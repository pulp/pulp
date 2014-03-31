# -*- coding: utf-8 -*-
#
# Copyright © 2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import celery
import logging

from pulp.common.error_codes import PLP0004, PLP0005, PLP0020, PLP0021, PLP0022
from pulp.server.async.tasks import Task, TaskResult
from pulp.server.exceptions import PulpCodedException, PulpException
from pulp.server.managers import factory as managers
from pulp.server.tasks.consumer import bind as bind_task, unbind as unbind_task

logger = logging.getLogger(__name__)


@celery.task(base=Task)
def bind(group_id, repo_id, distributor_id, notify_agent, binding_config, agent_options):
    """
    Bind the members of the specified consumer group.
    :param group_id: A consumer group ID.
    :type group_id: str
    :param repo_id: A repository ID.
    :type repo_id: str
    :param distributor_id: A distributor ID.
    :type distributor_id: str
    :param agent_options: Bind options passed to the agent handler.
    :type agent_options: dict
    :param notify_agent: indicates if the agent should be sent a message about the new binding
    :type  notify_agent: bool
    :param binding_config: configuration options to use when generating the payload for this binding
    :type binding_config: dict
    :return: Details of the subtasks that were executed
    :rtype: TaskResult
    """
    manager = managers.consumer_group_query_manager()
    group = manager.get_group(group_id)

    bind_errors = []
    additional_tasks = []

    for consumer_id in group['consumer_ids']:
        try:
            report = bind_task(consumer_id, repo_id, distributor_id, notify_agent, binding_config,
                               agent_options)
            if report.spawned_tasks:
                additional_tasks.extend(report.spawned_tasks)
        except PulpException, e:
            # Log a message so that we can debug but don't throw
            logger.debug(e.message)
            bind_errors.append(e)
        except Exception, e:
            logger.exception(e.message)
            # Don't do anything else since we still want to process all the other consumers
            bind_errors.append(e)

    bind_error = None
    if len(bind_errors) > 0:
        bind_error = PulpCodedException(PLP0004,
                                        repo_id=repo_id,
                                        distributor_id=distributor_id,
                                        group_id=group_id)
        bind_error.child_exceptions = bind_errors

    return TaskResult(error=bind_error, spawned_tasks=additional_tasks)


@celery.task(base=Task)
def unbind(group_id, repo_id, distributor_id, options):
    """
    Unbind the members of the specified consumer group.
    :param group_id: A consumer group ID.
    :type group_id: str
    :param repo_id: A repository ID.
    :type repo_id: str
    :param distributor_id: A distributor ID.
    :type distributor_id: str
    :param options: Bind options passed to the agent handler.
    :type options: dict
    :return: TaskResult containing the ids of all the spawned tasks & bind errors
    :rtype: TaskResult
    """
    manager = managers.consumer_group_query_manager()
    group = manager.get_group(group_id)

    bind_errors = []
    additional_tasks = []

    for consumer_id in group['consumer_ids']:
        try:
            report = unbind_task(consumer_id, repo_id, distributor_id, options)
            if report:
                additional_tasks.extend(report.spawned_tasks)
        except PulpException, e:
            #Log a message so that we can debug but don't throw
            logger.warn(e.message)
            bind_errors.append(e)
        except Exception, e:
            logger.exception(e.message)
            bind_errors.append(e)
            #Don't do anything else since we still want to process all the other consumers

    bind_error = None
    if len(bind_errors) > 0:
        bind_error = PulpCodedException(PLP0005,
                                        repo_id=repo_id,
                                        distributor_id=distributor_id,
                                        group_id=group_id)
        bind_error.child_exceptions = bind_errors
    return TaskResult(error=bind_error, spawned_tasks=additional_tasks)


def install_content(consumer_group_id, units, options):
    """
    Create an itinerary for consumer group content installation.
    :param consumer_group_id: unique id of the consumer group
    :type consumer_group_id: str
    :param units: units to install
    :type units: list or tuple
    :param options: options to pass to the install manager
    :type options: dict or None
    :return: Details of the subtasks that were executed
    :rtype: TaskResult
    """
    consumer_group = managers.consumer_group_query_manager().get_group(consumer_group_id)
    agent_manager = managers.consumer_agent_manager()

    return _process_group(consumer_group, PLP0020, {'group_id': consumer_group_id},
                          agent_manager.install_content, units, options)


def update_content(consumer_group_id, units, options):
    """
    Create an itinerary for consumer group content update.
    :param consumer_group_id: unique id of the consumer group
    :type consumer_group_id: str
    :param units: units to update
    :type units: list or tuple
    :param options: options to pass to the update manager
    :type options: dict or None
    :return: Details of the subtasks that were executed
    :rtype: TaskResult
    """
    consumer_group = managers.consumer_group_query_manager().get_group(consumer_group_id)
    agent_manager = managers.consumer_agent_manager()

    return _process_group(consumer_group, PLP0021, {'group_id': consumer_group_id},
                          agent_manager.update_content, units, options)


def uninstall_content(consumer_group_id, units, options):
    """
    Create an itinerary for consumer group content uninstallation.
    :param consumer_group_id: unique id of the consumer group
    :type consumer_group_id: str
    :param units: units to uninstall
    :type units: list or tuple
    :param options: options to pass to the uninstall manager
    :type options: dict or None
    :return: Details of the subtasks that were executed
    :rtype: TaskResult
    """
    consumer_group = managers.consumer_group_query_manager().get_group(consumer_group_id)
    agent_manager = managers.consumer_agent_manager()

    return _process_group(consumer_group, PLP0022, {'group_id': consumer_group_id},
                          agent_manager.uninstall_content, units, options)


def _process_group(consumer_group, error_code, error_kwargs, process_method, *args):
    """
    Process an action over a group of consumers

    :param consumer_group: A consumer group dictionary
    :type consumer_group: dict
    :param error_code: The error code to wrap any consumer failures in
    :type error_code: pulp.common.error_codes.Error
    :param error_kwargs: The keyword arguments to pass to the error code when it is instantiated
    :type error_kwargs: dict
    :param process_method: The method to call on each consumer in the group
    :type process_method: function
    :param args: any additional arguments passed to this method will be passed to the
                 process method function
    :type args: list of arguments
    :returns: A TaskResult with the overall results of the group
    :rtype: TaskResult
    """
    errors = []
    spawned_tasks = []
    for consumer_id in consumer_group['consumer_ids']:
        try:
            task = process_method(consumer_id, *args)
            spawned_tasks.append(task)
        except PulpException, e:
            #Log a message so that we can debug but don't throw
            logger.warn(e.message)
            errors.append(e)
        except Exception, e:
            logger.exception(e.message)
            errors.append(e)
            #Don't do anything else since we still want to process all the other consumers

    error = None
    if len(errors) > 0:
        error = PulpCodedException(error_code, **error_kwargs)
        error.child_exceptions = errors
    return TaskResult({}, error, spawned_tasks)
