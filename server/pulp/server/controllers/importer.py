import logging
import sys

import celery
from mongoengine import ValidationError

from pulp.common import error_codes, tags
from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.loader import api as plugin_api
from pulp.server import exceptions
from pulp.server.async.tasks import Task
from pulp.server.db import model
from pulp.server.managers import factory as manager_factory


_logger = logging.getLogger(__name__)


def build_resource_tag(repo_id, importer_type_id):
    """
    Returns an identfifier for the repo and importer.

    :param repo_id: unique ID for a repository
    :type  repo_id: basestring
    :param importer_type_id: unique ID for the importer
    :type  importer_type_id: basestring

    :return: a globally unique identifier for the repo and importer that
             can be used in cross-type comparisons.
    :rtype:  basestring
    """
    RESOURCE_TEMPLATE = 'pulp:importer:%s:%s'
    return RESOURCE_TEMPLATE % (repo_id, importer_type_id)


def clean_config_dict(config):
    """
    Remove keys from a dict that have a value None.

    :param config: configuration for plugin
    :type  config: dict

    :return: config without the keys whose values were None
    :rtype:  dict:
    """

    if config is not None:
        return dict([(k, v) for k, v in config.items() if v is not None])
    else:
        return None


@celery.task(base=Task, name='pulp.server.managers.repo.importer.set_importer')
def set_importer(repo_id, importer_type_id, repo_plugin_config):
    """
    Configures an importer to be used for the given repository.

    :param repo: repository object that the importer should be associated with
    :type  repo: pulp.server.db.model.Repository
    :param importer_type_id: type of importer, must correspond to a plugin loaded at server startup
    :type  importer_type_id: str
    :param repo_plugin_config: configuration values for the importer; may be None
    :type  repo_plugin_config: dict or None

    :return: created importer object
    :rtype:  pulp.server.model.Importer

    :raises PulpExecutionException: if something goes wrong in the plugin
    :raises exceptions.InvalidValue: if the values passed to create the importer are invalid
    """
    repo = model.Repository.objects.get_repo_or_missing_resource(repo_id)
    validate_importer_config(repo.repo_id, importer_type_id, repo_plugin_config)

    importer_instance, plugin_config = plugin_api.get_importer_by_id(importer_type_id)
    clean_config = clean_config_dict(repo_plugin_config)

    # Let the importer plugin verify the configuration
    call_config = PluginCallConfiguration(plugin_config, clean_config)
    transfer_repo = repo.to_transfer_repo()

    try:
        remove_importer(repo_id)
    except exceptions.MissingResource:
        pass  # it didn't exist, so no harm done

    # Let the importer plugin initialize the importer
    try:
        importer_instance.importer_added(transfer_repo, call_config)
    except Exception:
        _logger.exception(
            'Error initializing importer [%s] for repo [%s]' % (importer_type_id, repo.repo_id))
        raise exceptions.PulpExecutionException(), None, sys.exc_info()[2]

    importer = model.Importer(repo_id, importer_type_id, clean_config)
    try:
        importer.save()
    except ValidationError, e:
        raise exceptions.InvalidValue(e.to_dict().keys())

    return importer


def queue_set_importer(repo, importer_type_id, config):
    """
    Dispatch a task to set the importer on a repository.

    :param repo: repository object that the importer should be associated with
    :type  repo: pulp.server.db.model.Repository
    :param importer_type_id: type of importer, must correspond to a plugin loaded at server startup
    :type  importer_type_id: str
    :param config: configuration values for the importer
    :type  config: dict or None

    :return: asynchronous result
    :rtype:  pulp.server.async.tasks.TaskResult
    """
    task_tags = [tags.resource_tag(tags.RESOURCE_REPOSITORY_TYPE, repo.repo_id),
                 tags.action_tag('add_importer')]
    async_result = set_importer.apply_async_with_reservation(
        tags.RESOURCE_REPOSITORY_TYPE, repo.repo_id, [repo.repo_id, importer_type_id],
        {'repo_plugin_config': config}, tags=task_tags)
    return async_result


def validate_importer_config(repo_id, importer_type_id, importer_config):
    """
    This validates that the repository and importer type exist as these are both required to
    validate the configuration.

    :param repo_id: identifies the repo
    :type  repo_id: str
    :param importer_type_id: type of importer, must correspond to a plugin loaded at server startup
    :type  importer_type_id: str
    :param importer_config: configuration values for the importer; may be None
    :type  importer_config: dict

    :raises exceptions.PulpCodedValidationException: if config is invalid.
    """
    repo_obj = model.Repository.objects.get_repo_or_missing_resource(repo_id)

    if not plugin_api.is_valid_importer(importer_type_id):
        raise exceptions.PulpCodedValidationException(error_code=error_codes.PLP1008,
                                                      importer_type_id=importer_type_id)

    importer_instance, plugin_config = plugin_api.get_importer_by_id(importer_type_id)
    clean_config = clean_config_dict(importer_config)
    call_config = PluginCallConfiguration(plugin_config, clean_config)
    transfer_repo = repo_obj.to_transfer_repo()
    result = importer_instance.validate_config(transfer_repo, call_config)

    # For backward compatibility with plugins that don't yet return the tuple
    if isinstance(result, bool):
        valid_config = result
        message = None
    else:
        valid_config, message = result

    if not valid_config:
        raise exceptions.PulpCodedValidationException(validation_errors=message)


@celery.task(base=Task, name='pulp.server.managers.repo.importer.remove_importer')
def remove_importer(repo_id):
    """
    Removes an importer from a repository.

    :param repo_id: identifies the repo
    :type  repo_id: str
    """
    repo_obj = model.Repository.objects.get_repo_or_missing_resource(repo_id)
    repo_importer = model.Importer.objects.get_or_404(repo_id=repo_id)

    # remove schedules
    sync_manager = manager_factory.repo_sync_schedule_manager()
    sync_manager.delete_by_importer_id(repo_id, repo_importer.importer_type_id)

    # Call the importer's cleanup method
    importer_instance, plugin_config = plugin_api.get_importer_by_id(repo_importer.importer_type_id)

    call_config = PluginCallConfiguration(plugin_config, repo_importer.config)
    transfer_repo = repo_obj.to_transfer_repo()
    importer_instance.importer_removed(transfer_repo, call_config)
    repo_importer.delete()


def queue_remove_importer(repo_id, importer_type_id):
    """
    Dispatch a task to remove the importer from a repository.

    :param repo_id: identifies the repo
    :type  repo_id: str
    :param importer_type_id: type of importer
    :type  importer_type_id: str

    :return: asynchronous result
    :rtype:  pulp.server.async.tasks.TaskResult
    """
    get_valid_importer(repo_id, importer_type_id)
    task_tags = [tags.resource_tag(tags.RESOURCE_REPOSITORY_TYPE, repo_id),
                 tags.resource_tag(tags.RESOURCE_REPOSITORY_IMPORTER_TYPE, importer_type_id),
                 tags.action_tag('delete_importer')]
    async_result = remove_importer.apply_async_with_reservation(
        tags.RESOURCE_REPOSITORY_TYPE, repo_id, [repo_id], tags=task_tags)
    return async_result


def get_valid_importer(repo_id, importer_type_id):
    """
    Retrieves the importer for the specified repo and ensures that the provided importer type id
    matches the importer set on the repo.

    :param repo_id: id of the repo
    :type  repo_id: str
    :param importer_type_id: type of the importer
    :type  importer_type_id: str

    :return: key-value pairs describing the importer in use
    :rtype:  dict

    :raises pulp.server.exceptions.MissingResource: if repo/importer combination cannot be found
    """
    model.Repository.objects.get_repo_or_missing_resource(repo_id)
    try:
        importer = model.Importer.objects.get_or_404(repo_id=repo_id)
    except exceptions.MissingResource:
            raise exceptions.MissingResource(importer_id=importer_type_id)
    if importer.importer_type_id != importer_type_id:
        raise exceptions.MissingResource(importer_id=importer_type_id)
    return importer


@celery.task(base=Task, name='pulp.server.managers.repo.importer.update_importer_config')
def update_importer_config(repo_id, importer_config):
    """
    Attempts to update the saved configuration for the given repo's importer. The importer will be
    asked if the new configuration is valid. If not, this method will raise an error and the
    existing configuration will remain unchanged.

    :param repo_id: identifies the repo
    :type  repo_id: str
    :param importer_config: new configuration values to use for this repo
    :type  importer_config: dict
    """
    repo_importer = model.Importer.objects.get_or_404(repo_id=repo_id)
    importer_instance, plugin_config = plugin_api.get_importer_by_id(repo_importer.importer_type_id)
    validate_importer_config(repo_id, repo_importer.importer_type_id, plugin_config)

    # The convention is that None in an update removes the value and sets it to the default.
    unset_property_names = [k for k in importer_config if importer_config[k] is None]
    for key in unset_property_names:
        repo_importer.config.pop(key, None)
        importer_config.pop(key, None)

    # Whatever is left over are the changed/added values, so merge them in.
    repo_importer.config.update(importer_config)
    try:
        repo_importer.save()
    except ValidationError, e:
        raise exceptions.InvalidValue(e.to_dict().keys())

    serialized = model.Importer.serializer(repo_importer).data
    return serialized


def queue_update_importer_config(repo_id, importer_type_id, importer_config):
    """
    Dispatch a task to update the importer config.

    :param repo_id: id of the repo
    :type  repo_id: str
    :param importer_config: new configuration values to use for this repo
    :type  importer_config: dict
    """
    get_valid_importer(repo_id, importer_type_id)
    task_tags = [tags.resource_tag(tags.RESOURCE_REPOSITORY_TYPE, repo_id),
                 tags.resource_tag(tags.RESOURCE_REPOSITORY_IMPORTER_TYPE, importer_type_id),
                 tags.action_tag('update_importer')]
    async_result = update_importer_config.apply_async_with_reservation(
        tags.RESOURCE_REPOSITORY_TYPE,
        repo_id, [repo_id], {'importer_config': importer_config}, tags=task_tags)
    return async_result
