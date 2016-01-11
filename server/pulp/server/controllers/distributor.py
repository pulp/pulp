from gettext import gettext as _
import logging
import sys
import uuid

import celery

from pulp.common import tags
from pulp.common.error_codes import PLP0002, PLP0003
from pulp.plugins.conduits.repo_config import RepoConfigConduit
from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.loader import api as plugin_api
from pulp.server import exceptions
from pulp.server.async.tasks import Task, TaskResult
from pulp.server.db import model
from pulp.server.managers import factory as managers


_logger = logging.getLogger(__name__)


def add_distributor(repo_id, distributor_type_id, repo_plugin_config,
                    auto_publish, distributor_id=None):
    """
    Adds an association from the given repository to a distributor. The distributor_id is unique for
    a given repository. If distributor_id is not specified, one will be generated. If a distributor
    already exists on the repo for the given ID, the existing one will be removed and replaced with
    the newly configured one.

    :param repo_id: identifies the repo
    :type  repo_id: basestring
    :param distributor_type_id: must correspond to a distributor type loaded at server startup
    :type  distributor_type_id: basestring
    :param repo_plugin_config: configuration the repo will use with this distributor
    :type  repo_plugin_config: dict or None
    :param auto_publish: if True, this distributor will be invoked at the end of every sync
    :type  auto_publish: bool
    :param distributor_id: unique ID to refer to this distributor for this repo
    :type  distributor_id: basestring
    :return: distributor object
    :rtype:  pulp.server.db.model.Distributor

    :raise InvalidValue: if the distributor ID is provided and unacceptable
    :raise exceptions.PulpDataException: if the plugin returns that the config is invalid
    """

    repo_obj = model.Repository.objects.get_repo_or_missing_resource(repo_id)

    if not plugin_api.is_valid_distributor(distributor_type_id):
        raise exceptions.InvalidValue(['distributor_type_id'])

    if distributor_id is None:
        distributor_id = str(uuid.uuid4())

    distributor_instance, plugin_config = plugin_api.get_distributor_by_id(distributor_type_id)

    # Remove any keys whose values are explicitly set to None so the plugin will default them.
    if repo_plugin_config is not None:
        clean_config = dict([(k, v) for k, v in repo_plugin_config.items() if v is not None])
    else:
        clean_config = None

    # Let the distributor plugin verify the configuration
    call_config = PluginCallConfiguration(plugin_config, clean_config)
    config_conduit = RepoConfigConduit(distributor_type_id)
    transfer_repo = repo_obj.to_transfer_repo()
    result = distributor_instance.validate_config(transfer_repo, call_config, config_conduit)

    # For backward compatibility with plugins that don't yet return the tuple
    if isinstance(result, bool):
        valid_config = result
        message = None
    else:
        valid_config, message = result

    if not valid_config:
        raise exceptions.PulpDataException(message)

    try:
        model.Distributor.objects.get_or_404(repo_id=repo_id, distributor_id=distributor_id)
        delete(repo_id, distributor_id)
    except exceptions.MissingResource:
        pass  # if it didn't exist, no problem

    distributor_instance.distributor_added(transfer_repo, call_config)
    distributor = model.Distributor(repo_id, distributor_id, distributor_type_id, clean_config,
                                    auto_publish)
    distributor.save()
    return distributor


def queue_delete(distributor):
    """
    Dispatch a task to delete a distributor.

    :param distributor: distributor to be deleted
    :type  distributor: pulp.server.db.model.Distributor

    :return: An AsyncResult instance as returned by Celery's apply_async
    :rtype:  celery.result.AsyncResult
    """
    task_tags = [
        tags.resource_tag(tags.RESOURCE_REPOSITORY_TYPE, distributor.repo_id),
        tags.resource_tag(tags.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE, distributor.distributor_id),
        tags.action_tag('remove_distributor')
    ]
    async_result = delete.apply_async_with_reservation(
        tags.RESOURCE_REPOSITORY_TYPE, distributor.repo_id,
        [distributor.repo_id, distributor.distributor_id], tags=task_tags)
    return async_result


@celery.task(base=Task, name='pulp.server.tasks.repository.distributor_delete')
def delete(repo_id, dist_id):
    """
    Removes a distributor from a repository and unbinds any bound consumers.

    :param distributor: distributor to be deleted
    :type  distributor: pulp.server.db.model.Distributor

    :return: result containing any errors and tasks spawned
    :rtype pulp.server.async.tasks.TaskResult
    """

    distributor = model.Distributor.objects.get_or_404(repo_id=repo_id, distributor_id=dist_id)
    managers.repo_publish_schedule_manager().delete_by_distributor_id(repo_id, dist_id)

    # Call the distributor's cleanup method
    dist_instance, plugin_config = plugin_api.get_distributor_by_id(distributor.distributor_type_id)

    call_config = PluginCallConfiguration(plugin_config, distributor.config)
    repo = model.Repository.objects.get_repo_or_missing_resource(repo_id)
    dist_instance.distributor_removed(repo.to_transfer_repo(), call_config)
    distributor.delete()

    unbind_errors = []
    additional_tasks = []
    options = {}

    bind_manager = managers.consumer_bind_manager()
    for bind in bind_manager.find_by_distributor(repo_id, dist_id):
        try:
            report = bind_manager.unbind(bind['consumer_id'], bind['repo_id'],
                                         bind['distributor_id'], options)
            if report:
                additional_tasks.extend(report.spawned_tasks)
        except Exception, e:
            unbind_errors.append(e)

    bind_error = None
    if unbind_errors:
        bind_error = exceptions.PulpCodedException(PLP0003, repo_id=repo_id,
                                                   distributor_id=dist_id)
        bind_error.child_exceptions = unbind_errors

    return TaskResult(error=bind_error, spawned_tasks=additional_tasks)


def queue_update(distributor, config, delta):
    """
    Dispatch a task to update a distributor.

    :param distributor: distributor to be updated
    :type  distributor: pulp.server.db.model.Distributor
    :param config: A configuration dictionary for a distributor instance. The contents of this dict
                   depends on the type of distributor. Values of None will remove they key from the
                   config. Keys ommited from this dictionary will remain unchanged.
    :type  config: dict
    :param delta: A dictionary used to change conf values for a distributor instance. This currently
                  only supports the 'auto_publish' keyword, which should have a value of type bool
    :type  delta: dict or None

    :return: An AsyncResult instance as returned by Celery's apply_async
    :rtype:  celery.result.AsyncResult
    """
    task_tags = [
        tags.resource_tag(tags.RESOURCE_REPOSITORY_TYPE, distributor.repo_id),
        tags.resource_tag(tags.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE, distributor.distributor_id),
        tags.action_tag('update_distributor')
    ]
    async_result = update.apply_async_with_reservation(
        tags.RESOURCE_REPOSITORY_TYPE, distributor.repo_id,
        [distributor.repo_id, distributor.distributor_id, config, delta],
        tags=task_tags)
    return async_result


@celery.task(base=Task, name='pulp.server.tasks.repository.distributor_update')
def update(repo_id, dist_id, config=None, delta=None):
    """
    Update the distributor and (re)bind any bound consumers.

    :param distributor: distributor to be updated
    :type  distributor: pulp.server.db.model.Distributor
    :param config: A configuration dictionary for a distributor instance. The contents of this dict
                   depends on the type of distributor. Values of None will remove they key from the
                   config. Keys ommited from this dictionary will remain unchanged.
    :type  config: dict
    :param delta: A dictionary used to change conf values for a distributor instance. This currently
                  only supports the 'auto_publish' keyword, which should have a value of type bool
    :type  delta: dict or None

    :return: result containing any errors and tasks spawned
    :rtype pulp.server.async.tasks.TaskResult
    """
    repo = model.Repository.objects.get_repo_or_missing_resource(repo_id)
    distributor = model.Distributor.objects.get_or_404(repo_id=repo_id, distributor_id=dist_id)

    for k, v in config.iteritems():
        if v is None:
            distributor.config.pop(k)
        else:
            distributor.config[k] = v

    auto_publish = delta.get('auto_publish') if delta else None
    if isinstance(auto_publish, bool):
        distributor.auto_publish = auto_publish
    elif not isinstance(auto_publish, type(None)):
        raise exceptions.InvalidValue(['auto_publish'])

    # Let the distributor plugin verify the configuration
    distributor_instance, plugin_config = plugin_api.get_distributor_by_id(
        distributor.distributor_type_id)
    call_config = PluginCallConfiguration(plugin_config, distributor.config)
    transfer_repo = repo.to_transfer_repo()
    config_conduit = RepoConfigConduit(distributor.distributor_type_id)

    result = distributor_instance.validate_config(transfer_repo, call_config,
                                                  config_conduit)

    # For backward compatibility with plugins that don't yet return the tuple
    if isinstance(result, bool):
        valid_config = result
        message = None
    else:
        valid_config, message = result

    if not valid_config:
        raise exceptions.PulpDataException(message)
    distributor.save()

    unbind_errors = []
    additional_tasks = []
    options = {}
    bind_manager = managers.consumer_bind_manager()
    for bind in bind_manager.find_by_distributor(distributor.repo_id, distributor.distributor_id):
        try:
            report = bind_manager.bind(bind['consumer_id'], bind['repo_id'], bind['distributor_id'],
                                       bind['notify_agent'], bind['binding_config'], options)
            if report:
                additional_tasks.extend(report.spawned_tasks)
        except Exception, e:
            unbind_errors.append(e)

    bind_error = None
    if unbind_errors:
        bind_error = exceptions.PulpCodedException(PLP0002, repo_id=distributor.repo_id,
                                                   distributor_id=distributor.distributor_id)
        bind_error.child_exceptions = unbind_errors

    serialized_dist = model.Distributor.SERIALIZER(distributor).data
    return TaskResult(serialized_dist, error=bind_error, spawned_tasks=additional_tasks)


def create_bind_payload(repo_id, distributor_id, binding_config):
    """
    Requests the distributor plugin to generate the consumer bind payload.

    :param repo_id: identifies the repo being bound
    :type  repo_id: basestring
    :param distributor_id: identifies the distributor
    :type  distributor_id: basestring
    :param binding_config: config applicable only to the binding whose payload is being created
    :type  binding_config: object or None

    :return: payload to pass to the consumer
    :rtype:  dict

    :raise PulpExecutionException: if the distributor raises an error
    """
    dist = model.Distributor.objects.get_or_404(repo_id=repo_id, distributor_id=distributor_id)
    repo_obj = model.Repository.objects.get_repo_or_missing_resource(repo_id)

    distributor_instance, plugin_config = plugin_api.get_distributor_by_id(dist.distributor_type_id)

    # Let the distributor plugin verify the configuration
    call_config = PluginCallConfiguration(plugin_config, dist.config)
    transfer_repo = repo_obj.to_transfer_repo()

    try:
        return distributor_instance.create_consumer_payload(transfer_repo, call_config,
                                                            binding_config)
    except Exception:
        msg = _('Exception raised from distributor [%(d)s] generating consumer payload')
        msg = msg % {'d': distributor_id}
        _logger.exception(msg)
        raise exceptions.PulpExecutionException(), None, sys.exc_info()[2]
