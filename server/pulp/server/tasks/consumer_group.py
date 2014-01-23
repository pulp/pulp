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

from pulp.common.error_codes import PLP0004, PLP0005
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
            #Log a message so that we can debug but don't throw
            logger.debug(e.message)
            bind_errors.append(e)
        except Exception, e:
            logger.exception(e)
            #Don't do anything else since we still want to process all the other consumers
            bind_errors.append(e)

    bind_error = None
    if len(bind_errors) > 0:
        bind_error = PulpCodedException(PLP0004,
                                        repo_id=repo_id,
                                        distributor_id=distributor_id,
                                        group_id=group_id)
        bind_error.child_exceptions = bind_errors

    return TaskResult({}, bind_error, additional_tasks)


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
            logger.exception(e)
            bind_errors.append(e)
            #Don't do anything else since we still want to process all the other consumers

    bind_error = None
    if len(bind_errors) > 0:
        bind_error = PulpCodedException(PLP0005,
                                        repo_id=repo_id,
                                        distributor_id=distributor_id,
                                        group_id=group_id)
        bind_error.child_exceptions = bind_errors
    return TaskResult({}, bind_error, additional_tasks)


@celery.task(base=Task)
def install_content(consumer_id, units, options):
    pass


@celery.task(base=Task)
def update_content(consumer_id, units, options):
    pass


@celery.task(base=Task)
def uninstall_content(consumer_id, units, options):
    pass
