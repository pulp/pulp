from gettext import gettext as _
import logging
import sys

from mongoengine import NotUniqueError, OperationError, ValidationError
import celery

from pulp.common import dateutils, error_codes, tags
from pulp.common.tags import resource_tag, RESOURCE_REPOSITORY_TYPE, action_tag
from pulp.plugins.conduits.repo_sync import RepoSyncConduit
from pulp.plugins.conduits.repo_publish import RepoPublishConduit
from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.loader import api as plugin_api
from pulp.plugins.loader import exceptions as plugin_exceptions
from pulp.plugins.model import SyncReport
from pulp.plugins.util import misc
from pulp.server import exceptions as pulp_exceptions
from pulp.server.async.tasks import PulpTask, register_sigterm_handler, Task, TaskResult
from pulp.server.controllers import consumer as consumer_controller
from pulp.server.controllers import distributor as dist_controller
from pulp.server.controllers import importer as importer_controller
from pulp.server.db import connection, model
from pulp.server.db.model.repository import (
    RepoContentUnit, RepoSyncResult, RepoPublishResult)
from pulp.server.managers import factory as manager_factory
from pulp.server.managers.repo import _common as common_utils


_logger = logging.getLogger(__name__)


def get_associated_unit_ids(repo_id, unit_type, repo_content_unit_q=None):
    """
    Return a generator of unit IDs within the given repo that match the type and query

    :param repo_id:     ID of the repo whose units should be queried
    :type  repo_id:     str
    :param unit_type:   ID of the unit type which should be retrieved
    :type  unit_type:   str
    :param repo_content_unit_q: any additional filters that should be applied to the
                                RepositoryContentUnit search
    :type  repo_content_unit_q: mongoengine.Q
    :return:    generator of unit IDs
    :rtype:     generator
    """
    qs = model.RepositoryContentUnit.objects(q_obj=repo_content_unit_q,
                                             repo_id=repo_id,
                                             unit_type_id=unit_type)
    for assoc in qs.only('unit_id'):
        yield assoc.unit_id


def get_unit_model_querysets(repo_id, model_class, repo_content_unit_q=None):
    """
    Return a generator of mongoengine.queryset.QuerySet objects that collectively represent the
    units in the specified repo that are of the type corresponding to the model_class and that
    match the optional query.

    Results are broken up into multiple QuerySet objects, because units are requested by their ID,
    and we do not want to exceed the maximum size for a single query by stuffing too many IDs in one
    QuerySet object.

    You are welcome and encouraged to convert the return value into one generator of ContentUnit
    objects by using itertools.chain()

    :param repo_id:     ID of the repo whose units should be queried
    :type  repo_id:     str
    :param model_class: a subclass of ContentUnit that defines a unit model
    :type  model_class: pulp.server.db.model.ContentUnit
    :param repo_content_unit_q: any additional filters that should be applied to the
                                RepositoryContentUnit search
    :type  repo_content_unit_q: mongoengine.Q

    :return:    generator of mongoengine.queryset.QuerySet
    :rtype:     generator
    """
    for chunk in misc.paginate(get_associated_unit_ids(repo_id,
                                                       model_class._content_type_id.default,
                                                       repo_content_unit_q)):
        yield model_class.objects(id__in=chunk)


def find_repo_content_units(
        repository, repo_content_unit_q=None,
        units_q=None, unit_fields=None, limit=None, skip=None,
        yield_content_unit=False):
    """
    Search content units associated with a given repository.

    If yield_content_unit is not specified, or is set to false, then the RepositoryContentUnit
    representing the association will be returned with an attribute "unit" set to the actual
    ContentUnit. If yield_content_unit is set to true then the ContentUnit will be yielded instead
    of the RepoContentUnit.

    :param repository: The repository to search.
    :type repository: pulp.server.db.model.Repository
    :param repo_content_unit_q: Any query filters to apply to the RepoContentUnits.
    :type repo_content_unit_q: mongoengine.Q
    :param units_q: Any query filters to apply to the ContentUnits.
    :type units_q: mongoengine.Q
    :param unit_fields: List of fields to fetch for the unit objects, defaults to all fields.
    :type unit_fields: List of str
    :param limit: The maximum number of items to return for the given query.
    :type limit: int
    :param skip: The starting offset.
    :type skip: int
    :param yield_content_unit: Whether we should yield a ContentUnit or RepositoryContentUnit.
        If True then a ContentUnit will be yielded. Defaults to False
    :type yield_content_unit: bool

    :return: Content unit assoociations matching the query.
    :rtype: generator of pulp.server.db.model.ContentUnit or
        pulp.server.db.model.RepositoryContentUnit

    """

    qs = model.RepositoryContentUnit.objects(q_obj=repo_content_unit_q,
                                             repo_id=repository.repo_id)

    type_map = {}
    content_units = {}

    yield_count = 1
    skip_count = 0

    for repo_content_unit in qs:
        id_set = type_map.setdefault(repo_content_unit.unit_type_id, set())
        id_set.add(repo_content_unit.unit_id)
        content_unit_set = content_units.setdefault(repo_content_unit.unit_type_id, dict())
        content_unit_set[repo_content_unit.unit_id] = repo_content_unit

    for unit_type, unit_ids in type_map.iteritems():
        qs = plugin_api.get_unit_model_by_id(unit_type).objects(
            q_obj=units_q, __raw__={'_id': {'$in': list(unit_ids)}})
        if unit_fields:
            qs = qs.only(*unit_fields)

        for unit in qs:
            if skip and skip_count < skip:
                skip_count += 1
                continue

            if yield_content_unit:
                yield unit
            else:
                cu = content_units[unit_type][unit.id]
                cu.unit = unit
                yield cu

            if limit:
                if yield_count >= limit:
                    return

            yield_count += 1


def rebuild_content_unit_counts(repository):
    """
    Update the content_unit_counts field on a Repository.

    :param repository: The repository to update
    :type repository: pulp.server.db.model.Repository
    """
    db = connection.get_database()

    pipeline = [
        {'$match': {'repo_id': repository.repo_id}},
        {'$group': {'_id': '$unit_type_id', 'sum': {'$sum': 1}}}]
    q = db.command('aggregate', 'repo_content_units', pipeline=pipeline)

    # Flip this into the form that we need
    counts = {}
    for result in q['result']:
        counts[result['_id']] = result['sum']

    repository.content_unit_counts = counts
    repository.save()


def associate_single_unit(repository, unit):
    """
    Associate a single unit to a repository.

    :param repository: The repository to update.
    :type repository: pulp.server.db.model.Repository
    :param unit: The unit to associate to the repository.
    :type unit: pulp.server.db.model.ContentUnit
    """
    current_timestamp = dateutils.now_utc_timestamp()
    formatted_datetime = dateutils.format_iso8601_utc_timestamp(current_timestamp)
    qs = model.RepositoryContentUnit.objects(
        repo_id=repository.repo_id,
        unit_id=unit.id,
        unit_type_id=unit._content_type_id)
    qs.update_one(
        set_on_insert__created=formatted_datetime,
        set__updated=formatted_datetime,
        upsert=True)


def disassociate_units(repository, unit_iterable):
    """
    Disassociate all units in the iterable from the repository

    :param repository: The repository to update.
    :type repository: pulp.server.db.model.Repository
    :param unit_iterable: The units to disassociate from the repository.
    :type unit_iterable: iterable of pulp.server.db.model.ContentUnit
    """
    for unit_group in misc.paginate(unit_iterable):
        unit_id_list = [unit.id for unit in unit_group]
        qs = model.RepositoryContentUnit.objects(
            repo_id=repository.repo_id, unit_id__in=unit_id_list)
        qs.delete()


def create_repo(repo_id, display_name=None, description=None, notes=None, importer_type_id=None,
                importer_repo_plugin_config=None, distributor_list=None):
    """
    Create a repository and add importers and distributors if they are specified. If there are any
    issues adding any of the importers or distributors, the repo will be deleted and the exceptions
    will be reraised.

    Multiple distributors can be created in this call. Each distributor is specified as a dict with
    the following keys:

        distributor_type - ID of the type of distributor being added
        distributor_config - values sent to the distributor when used by this repository
        auto_publish - boolean indicating if the distributor should automatically publish with every
                       sync; defaults to False
        distributor_id - used to refer to the distributor later; if omitted, one will be generated

    :param repo_id: unique identifier for the repo
    :type  repo_id: str
    :param display_name: user-friendly name for the repo
    :type  display_name: str
    :param description: user-friendly text describing the repo's contents
    :type  description: str
    :param notes: key-value pairs to programmatically tag the repo
    :type  notes: dict
    :param importer_type_id: if specified, an importer with this type ID will be added to the repo
    :type  importer_type_id: str
    :param importer_repo_plugin_config: configuration values for the importer, may be None
    :type  importer_repo_plugin_config: dict
    :param distributor_list: iterable of distributor dicts to add; more details above
    :type  distributor_list: list or tuple

    :raises DuplicateResource: if there is already a repo with the requested ID
    :raises InvalidValue: if any of the fields are invalid

    :return: created repository object
    :rtype:  pulp.server.db.model.Repository
    """

    # Prevalidation.
    if not isinstance(distributor_list, (list, tuple, type(None))):
        raise pulp_exceptions.InvalidValue(['distributor_list'])
    if not all(isinstance(distributor, dict) for distributor in distributor_list or []):
        raise pulp_exceptions.InvalidValue(['distributor_list'])

    # Note: the repo must be saved before the importer and distributor controllers can be called
    #       because the first thing that they do is validate that the repo exists.
    repo = model.Repository(repo_id=repo_id, display_name=display_name, description=description,
                            notes=notes)
    try:
        repo.save()
    except NotUniqueError:
        raise pulp_exceptions.DuplicateResource(repo_id)
    except ValidationError, e:
        raise pulp_exceptions.InvalidValue(e.to_dict().keys())

    # Add the importer. Delete the repository if this fails.
    if importer_type_id is not None:
        try:
            importer_controller.set_importer(repo, importer_type_id, importer_repo_plugin_config)
        except Exception:
            _logger.exception(
                'Exception adding importer to repo [%s]; the repo will be deleted' % repo_id)
            repo.delete()
            raise

    # Add the distributors. Delete the repository if this fails.
    for distributor in distributor_list or []:
        type_id = distributor.get('distributor_type_id')
        plugin_config = distributor.get('distributor_config')
        auto_publish = distributor.get('auto_publish', False)
        dist_id = distributor.get('distributor_id')

        try:
            dist_controller.add_distributor(repo_id, type_id, plugin_config, auto_publish, dist_id)
        except Exception:
            _logger.exception('Exception adding distributor to repo [%s]; the repo will be '
                              'deleted' % repo_id)
            repo.delete()
            raise

    return repo


def queue_delete(repo_id):
    """
    Dispatch the task to delete the specified repository.

    :param repo_id: id of the repository to delete
    :type  repo_id: str

    :return: A TaskResult with the details of any errors or spawned tasks
    :rtype:  pulp.server.async.tasks.TaskResult
    """
    task_tags = [
        tags.resource_tag(tags.RESOURCE_REPOSITORY_TYPE, repo_id),
        tags.action_tag('delete')
    ]
    async_result = delete.apply_async_with_reservation(
        tags.RESOURCE_REPOSITORY_TYPE, repo_id,
        [repo_id], tags=task_tags)
    return async_result


@celery.task(base=Task, name='pulp.server.tasks.repository.delete')
def delete(repo_id):
    """
    Delete a repository and inform other affected collections.

    :param repo_id: id of the repository to delete.
    :type  repo_id: str

    :raise pulp_exceptions.PulpExecutionException: if any part of the process fails; the exception
                                                   will contain information on which sections failed

    :return: A TaskResult object with the details of any errors or spawned tasks
    :rtype:  pulp.server.async.tasks.TaskResult
    """

    # With so much going on during a delete, it's possible that a few things could go wrong while
    # others are successful. We track lesser errors that shouldn't abort the entire process until
    # the end and then raise an exception describing the incompleteness of the delete. The exception
    # arguments are captured as the second element in the tuple, but the user will have to look at
    # the server logs for more information.
    error_tuples = []  # tuple of failed step and exception arguments

    # Inform the importer
    repo_importer = model.Importer.objects(repo_id=repo_id).first()
    if repo_importer is not None:
        try:
            importer_controller.remove_importer(repo_id)
        except Exception, e:
            _logger.exception('Error received removing importer [%s] from repo [%s]' % (
                repo_importer.importer_type_id, repo_id))
            error_tuples.append(e)

    # Inform all distributors
    for distributor in model.Distributor.objects(repo_id=repo_id):
        try:
            dist_controller.delete(distributor)
        except Exception, e:
            _logger.exception('Error received removing distributor [%s] from repo [%s]' % (
                distributor.id, repo_id))
            error_tuples.append(e)

    # Database Updates
    repo = model.Repository.objects.get_repo_or_missing_resource(repo_id)
    repo.delete()

    try:
        # Remove all importers and distributors from the repo. This is likely already done by the
        # calls to other methods in this manager, but in case those failed we still want to attempt
        # to keep the database clean.
        model.Distributor.objects(repo_id=repo_id).delete()
        model.Importer.objects(repo_id=repo_id).delete()
        RepoSyncResult.get_collection().remove({'repo_id': repo_id}, safe=True)
        RepoPublishResult.get_collection().remove({'repo_id': repo_id}, safe=True)
        RepoContentUnit.get_collection().remove({'repo_id': repo_id}, safe=True)
    except Exception, e:
        msg = _('Error updating one or more database collections while removing repo [%(r)s]')
        msg = msg % {'r': repo_id}
        _logger.exception(msg)
        error_tuples.append(e)

    # remove the repo from any groups it was a member of
    group_manager = manager_factory.repo_group_manager()
    group_manager.remove_repo_from_groups(repo_id)

    if len(error_tuples) > 0:
        pe = pulp_exceptions.PulpExecutionException()
        pe.child_exceptions = error_tuples
        raise pe

    # append unbind itineraries foreach bound consumer
    options = {}
    consumer_bind_manager = manager_factory.consumer_bind_manager()

    additional_tasks = []
    errors = []
    for bind in consumer_bind_manager.find_by_repo(repo_id):
        try:
            report = consumer_controller.unbind(bind['consumer_id'], bind['repo_id'],
                                                bind['distributor_id'], options)
            if report:
                additional_tasks.extend(report.spawned_tasks)
        except Exception, e:
            errors.append(e)

    error = None
    if len(errors) > 0:
        error = pulp_exceptions.PulpCodedException(error_codes.PLP0007, repo_id=repo_id)
        error.child_exceptions = errors

    return TaskResult(error=error, spawned_tasks=additional_tasks)


def update_repo_and_plugins(repo, repo_delta, importer_config, distributor_configs):
    """
    Update a reposiory and its related collections.

    All details do not need to be specified; if a piece is omitted it's configuration is not
    touched, nor is it removed from the repository. The same holds true for the distributor_configs
    dict, not every distributor must be represented.

    This call will attempt to update the repository object, then the importer, then the
    distributors. If an exception occurs during any of these steps, the updates stop and the
    exception is immediately raised. Any updates that have already taken place are not rolled back.

    Distributor updates are asynchronous as there could be a very large number of consumers to
    update. Repository and importer updates are done synchronously.

    :param repo: repository object
    :type  repo: pulp.server.db.model.Repository
    :param repo_delta: list of attributes to change and their new values; if None, no attempt to
                       update the repository object will be made
    :type  repo_delta: dict, None
    :param importer_config: new configuration to use for the repo's importer; if None, no attempt
                            will be made to update the importer
    :type  importer_config: dict, None
    :param distributor_configs: mapping of distributor ID to the new configuration to set for it
    :type  distributor_configs: dict, None

    :return: Task result that contains the updated repository object and additional spawned tasks
    :rtype:  pulp.server.async.tasks.TaskResult

    :raises pulp_exceptions.InvalidValue: if repo_delta is not a dictionary
    """
    if repo_delta:
        if isinstance(repo_delta, dict):
            repo.update_from_delta(repo_delta)
            repo.save()
        else:
            raise pulp_exceptions.PulpCodedValidationException(
                error_code=error_codes.PLP1010, field='delta', field_type='dict', value=repo_delta)

    if importer_config is not None:
        importer_controller.update_importer_config(repo.repo_id, importer_config)

    additional_tasks = []
    if distributor_configs is not None:
        for dist_id, dist_config in distributor_configs.items():
            task_tags = [
                tags.resource_tag(tags.RESOURCE_REPOSITORY_TYPE, repo.repo_id),
                tags.resource_tag(tags.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE,
                                  dist_id),
                tags.action_tag(tags.ACTION_UPDATE_DISTRIBUTOR)
            ]
            async_result = dist_controller.update.apply_async_with_reservation(
                tags.RESOURCE_REPOSITORY_TYPE, repo.repo_id,
                [repo.repo_id, dist_id, dist_config, None], tags=task_tags)
            additional_tasks.append(async_result)
    return TaskResult(repo, None, additional_tasks)


def update_unit_count(repo_id, unit_type_id, delta):
    """
    Updates the total count of units associated with the repo. Each repo has an attribute
    'content_unit_counts' which is a dict where keys are content type IDs and values are the
    number of content units of that type in the repository.

    example: {'rpm': 12, 'srpm': 3}

    :param repo_id: identifies the repo
    :type  repo_id: str
    :param unit_type_id: identifies the unit type to update
    :type  unit_type_id: str
    :param delta: amount by which to increment the total count
    :type  delta: int

    :raises pulp_exceptions.PulpCodedException: if there is an error in the update
    """
    atomic_inc_key = 'inc__content_unit_counts__{unit_type_id}'.format(unit_type_id=unit_type_id)
    if delta:
        try:
            model.Repository.objects(repo_id=repo_id).update_one(**{atomic_inc_key: delta})
        except OperationError:
            message = 'There was a problem updating repository %s' % repo_id
            raise pulp_exceptions.PulpExecutionException(message), None, sys.exc_info()[2]


def update_last_unit_added(repo_id):
    """
    Updates the UTC date record on the repository for the time the last unit was added.

    :param repo_id: identifies the repo
    :type  repo_id: str
    """
    repo_obj = model.Repository.objects.get_repo_or_missing_resource(repo_id)
    repo_obj.last_unit_added = dateutils.now_utc_datetime_with_tzinfo()
    repo_obj.save()


def update_last_unit_removed(repo_id):
    """
    Updates the UTC date record on the repository for the time the last unit was removed.

    :param repo_id: identifies the repo
    :type  repo_id: str
    """
    repo_obj = model.Repository.objects.get_repo_or_missing_resource(repo_id)
    repo_obj.last_unit_removed = dateutils.now_utc_datetime_with_tzinfo()
    repo_obj.save()


@celery.task(base=PulpTask)
def queue_sync_with_auto_publish(repo_id, overrides=None, scheduled_call_id=None):
    """
    Sync a repository and upon successful completion, publish any distributors that are configured
    for auto publish.

    :param repo_id: id of the repository to create a sync call request list for
    :type repo_id:  str
    :param overrides: dictionary of configuration overrides for this sync
    :type overrides:  dict or None
    :param scheduled_call_id: id of scheduled call that dispatched this task
    :type  scheduled_call_id: str

    :return: result containing the details of the task executed and any spawned tasks
    :rtype:  pulp.server.async.tasks.TaskResult
    """
    kwargs = {'repo_id': repo_id, 'sync_config_override': overrides,
              'scheduled_call_id': scheduled_call_id}
    tags = [resource_tag(RESOURCE_REPOSITORY_TYPE, repo_id), action_tag('sync')]
    result = sync.apply_async_with_reservation(RESOURCE_REPOSITORY_TYPE, repo_id, tags=tags,
                                               kwargs=kwargs)
    return result


@celery.task(base=Task, name='pulp.server.managers.repo.sync.sync')
def sync(repo_id, sync_config_override=None, scheduled_call_id=None):
    """
    Performs a synchronize operation on the given repository and triggers publishs for distributors
    with autopublish enabled.

    The given repo must have an importer configured. This method is intentionally limited to
    synchronizing a single repo. Performing multiple repository syncs concurrently will require a
    more global view of the server and must be handled outside the scope of this class.

    :param repo_id: identifies the repo to sync
    :type  repo_id: str
    :param sync_config_override: optional config containing values to use for this sync only
    :type  sync_config_override: dict
    :param scheduled_call_id: id of scheduled call that dispatched this task
    :type  scheduled_call_id: str

    :return: TaskResult containing sync results and a list of spawned tasks
    :rtype:  pulp.server.async.tasks.TaskResult

    :raise pulp_exceptions.MissingResource: if specified repo does not exist, or it does not have
                                            an importer and associated plugin
    :raise pulp_exceptions.PulpExecutionException: if the task fails.
    """

    repo_obj = model.Repository.objects.get_repo_or_missing_resource(repo_id)
    transfer_repo = repo_obj.to_transfer_repo()

    repo_importer = model.Importer.objects.get_or_404(repo_id=repo_id)
    try:
        importer, imp_config = plugin_api.get_importer_by_id(repo_importer.importer_type_id)
    except plugin_exceptions.PluginNotFound:
        raise pulp_exceptions.MissingResource(repository=repo_id)

    call_config = PluginCallConfiguration(imp_config, repo_importer.config, sync_config_override)
    transfer_repo.working_dir = common_utils.get_working_directory()
    conduit = RepoSyncConduit(repo_id, repo_importer.importer_type_id)
    sync_result_collection = RepoSyncResult.get_collection()

    # Fire an events around the call
    fire_manager = manager_factory.event_fire_manager()
    fire_manager.fire_repo_sync_started(repo_id)

    # Perform the sync
    sync_start_timestamp = _now_timestamp()
    sync_result = None

    try:
        # Replace the Importer's sync_repo() method with our register_sigterm_handler decorator,
        # which will set up cancel_sync_repo() as the target for the signal handler
        sync_repo = register_sigterm_handler(importer.sync_repo, importer.cancel_sync_repo)
        sync_report = sync_repo(transfer_repo, conduit, call_config)

    except Exception, e:
        sync_end_timestamp = _now_timestamp()
        sync_result = RepoSyncResult.error_result(
            repo_obj.repo_id, repo_importer['id'], repo_importer['importer_type_id'],
            sync_start_timestamp, sync_end_timestamp, e, sys.exc_info()[2])
        raise

    else:
        sync_end_timestamp = _now_timestamp()
        # Need to be safe here in case the plugin is incorrect in its return
        if isinstance(sync_report, SyncReport):
            added_count = sync_report.added_count
            updated_count = sync_report.updated_count
            removed_count = sync_report.removed_count
            summary = sync_report.summary
            details = sync_report.details

            if sync_report.canceled_flag:
                result_code = RepoSyncResult.RESULT_CANCELED
            elif sync_report.success_flag:
                result_code = RepoSyncResult.RESULT_SUCCESS
            else:
                result_code = RepoSyncResult.RESULT_FAILED

        else:
            msg = _('Plugin type [%s] on repo [%s] did not return a valid sync report')
            _logger.warn(msg % (repo_importer['importer_type_id'], repo_obj.repo_id))
            added_count = updated_count = removed_count = -1  # None?
            summary = details = msg
            result_code = RepoSyncResult.RESULT_ERROR  # RESULT_UNKNOWN?

        sync_result = RepoSyncResult.expected_result(
            repo_obj.repo_id, repo_importer['id'], repo_importer['importer_type_id'],
            sync_start_timestamp, sync_end_timestamp, added_count, updated_count, removed_count,
            summary, details, result_code)

    finally:
        # Do an update instead of a save in case the importer has changed the scratchpad
        model.Importer.objects(repo_id=repo_obj.repo_id).update(set__last_sync=sync_end_timestamp)
        # Add a sync history entry for this run
        sync_result_collection.save(sync_result, safe=True)

    fire_manager.fire_repo_sync_finished(sync_result)
    if sync_result.result == RepoSyncResult.RESULT_FAILED:
        raise pulp_exceptions.PulpExecutionException(_('Importer indicated a failed response'))

    spawned_tasks = _queue_auto_publish_tasks(repo_obj.repo_id, scheduled_call_id=scheduled_call_id)
    return TaskResult(sync_result, spawned_tasks=spawned_tasks)


def _queue_auto_publish_tasks(repo_id, scheduled_call_id=None):
    """
    Queue publish tasks for all distributors of the specified repo that have auto publish enabled.

    :param repo_id: identifies a repository
    :type  repo_id: repo_id
    :param scheduled_call_id: id of scheduled call that dispatched this task
    :type  scheduled_call_id: str

    :return: list of task_ids for the queued publish tasks
    :rtype:  list
    """
    return [queue_publish(repo_id, dist.distributor_id, scheduled_call_id=scheduled_call_id).task_id
            for dist in model.Distributor.objects(repo_id=repo_id, auto_publish=True)]


def sync_history(start_date, end_date, repo_id):
    """
    Returns a cursor containing the sync history entries for the given repo.

    :param start_date: if specified, no events prior to this date will be returned. Expected to be
                       an iso8601 datetime string.
    :type  start_date: str
    :param end_date: if specified, no events after this date will be returned. Expected to be an
                     iso8601 datetime string.
    :type end_date: str
    :param repo_id: identifies the repo
    :type  repo_id: str

    :return: object containing sync history results
    :rtype:  pymongo.cursor.Cursor

    :raise MissingResource: if repo_id does not reference a valid repo
    """
    model.Repository.objects.get_repo_or_missing_resource(repo_id)
    search_params = {'repo_id': repo_id}
    date_range = {}
    if start_date:
        date_range['$gte'] = start_date
    if end_date:
        date_range['$lte'] = end_date
    if start_date or end_date:
        search_params['started'] = date_range
    return RepoSyncResult.get_collection().find(search_params)


@celery.task(base=PulpTask)
def queue_publish(repo_id, distributor_id, overrides=None, scheduled_call_id=None):
    """
    Queue a repo publish task.

    :param repo_id: id of the repo to publish
    :type  repo_id: str
    :param distributor_id: publish the repo with this distributor
    :type  distributor_id: str
    :param overrides: dictionary of options to pass to the publish task
    :type  overrides: dict or None
    :param scheduled_call_id: id of scheduled call that dispatched this task
    :type  scheduled_call_id: str

    :return: task result object
    :rtype: pulp.server.async.tasks.TaskResult
    """
    kwargs = {'repo_id': repo_id, 'dist_id': distributor_id, 'publish_config_override': overrides,
              'scheduled_call_id': scheduled_call_id}
    tags = [resource_tag(RESOURCE_REPOSITORY_TYPE, repo_id),
            action_tag('publish')]
    return publish.apply_async_with_reservation(RESOURCE_REPOSITORY_TYPE, repo_id, tags=tags,
                                                kwargs=kwargs)


@celery.task(base=Task, name='pulp.server.managers.repo.publish.publish')
def publish(repo_id, dist_id, publish_config_override=None, scheduled_call_id=None):
    """
    Uses the given distributor to publish the repository.

    The publish operation is executed synchronously in the caller's thread and will block until it
    is completed. The caller must take the necessary steps to address the fact that a publish call
    may be time intensive.

    :param repo_id: identifies the repo being published
    :type  repo_id: str
    :param dist_id: identifies the repo's distributor to publish
    :type  dist_id: str
    :param publish_config_override: optional config values to use for this publish call only
    :type  publish_config_override: dict, None
    :param scheduled_call_id: id of scheduled call that dispatched this task
    :type  scheduled_call_id: str

    :return: report of the details of the publish
    :rtype:  pulp.server.db.model.repository.RepoPublishResult

    :raises pulp_exceptions.MissingResource: if distributor/repo pair does not exist
    """
    repo_obj = model.Repository.objects.get_repo_or_missing_resource(repo_id)
    dist = model.Distributor.objects.get_or_404(repo_id=repo_id, distributor_id=dist_id)
    dist_inst, dist_conf = _get_distributor_instance_and_config(repo_id, dist_id)

    # Assemble the data needed for the publish
    conduit = RepoPublishConduit(repo_id, dist_id)
    call_config = PluginCallConfiguration(dist_conf, dist.config, publish_config_override)
    transfer_repo = repo_obj.to_transfer_repo()
    transfer_repo.working_dir = common_utils.get_working_directory()

    # Fire events describing the publish state
    fire_manager = manager_factory.event_fire_manager()
    fire_manager.fire_repo_publish_started(repo_id, dist_id)
    result = _do_publish(repo_obj, dist_id, dist_inst, transfer_repo, conduit, call_config)
    fire_manager.fire_repo_publish_finished(result)
    return result


def _get_distributor_instance_and_config(repo_id, distributor_id):
    """
    For a given repository and distributor, retrieve the instance of the distributor and its
    configuration from the plugin api.

    :param repo_id: identifies the repository
    :type  repo_id: str
    :param distributor_id: identifies the distributor
    :type  distributor_id: str

    :return: distributor instance and config
    :rtype:  tuple
    """
    dist = model.Distributor.objects.get_or_404(repo_id=repo_id, distributor_id=distributor_id)
    distributor, config = plugin_api.get_distributor_by_id(dist.distributor_type_id)
    return distributor, config


def _do_publish(repo_obj, dist_id, dist_inst, transfer_repo, conduit, call_config):
    """
    Publish the repository using the given distributor.

    :param repo_obj: repository object
    :type  repo_obj: pulp.server.db.model.Repository
    :param dist_id: identifies the distributor
    :type  dist_id: str
    :param dist_inst: instance of the distributor
    :type  dist_inst: dict
    :param transfer_repo: dict representation of a repo for the plugins to use
    :type  transfer_repo: pulp.plugins.model.Repository
    :param conduit: allows the plugin to interact with core pulp
    :type  conduit: pulp.plugins.conduits.repo_publish.RepoPublishConduit
    :param call_config: allows the plugin to retrieve values
    :type  call_config: pulp.plugins.config.PluginCallConfiguration

    :return: publish result containing information about the publish
    :rtype:  pulp.server.db.model.repository.RepoPublishResult

    :raises pulp_exceptions.PulpCodedException: if the publish report's success flag is falsey
    """
    publish_result_coll = RepoPublishResult.get_collection()
    publish_start_timestamp = _now_timestamp()
    try:
        # Add the register_sigterm_handler decorator to the publish_repo call, so that we can
        # respond to signals by calling the Distributor's cancel_publish_repo() method.
        publish_repo = register_sigterm_handler(dist_inst.publish_repo,
                                                dist_inst.cancel_publish_repo)
        publish_report = publish_repo(transfer_repo, conduit, call_config)
        if publish_report is not None and hasattr(publish_report, 'success_flag') \
                and not publish_report.success_flag:
            _logger.info(publish_report.summary)
            raise pulp_exceptions.PulpCodedException(
                error_code=error_codes.PLP0034, repository_id=repo_obj.repo_id,
                distributor_id=dist_id, summary=publish_report.summary
            )

    except Exception, e:
        exception_timestamp = _now_timestamp()

        # Reload the distributor in case the scratchpad is set by the plugin
        dist = model.Distributor.objects.get_or_404(repo_id=repo_obj.repo_id,
                                                    distributor_id=dist_id)
        # Add a publish history entry for the run
        result = RepoPublishResult.error_result(
            repo_obj.repo_id, dist.distributor_id, dist.distributor_type_id,
            publish_start_timestamp, exception_timestamp, e, sys.exc_info()[2])
        publish_result_coll.save(result, safe=True)

        _logger.exception(
            _('Exception caught from plugin during publish for repo [%(r)s]'
              % {'r': repo_obj.repo_id}))
        raise

    publish_end_timestamp = _now_timestamp()

    # Reload the distributor in case the scratchpad is set by the plugin
    dist = model.Distributor.objects.get_or_404(repo_id=repo_obj.repo_id, distributor_id=dist_id)
    dist.last_publish = publish_end_timestamp
    dist.save()

    # Add a publish entry
    summary = publish_report.summary
    details = publish_report.details
    _logger.debug('publish succeeded for repo [%s] with distributor ID [%s]' % (
                  repo_obj.repo_id, dist_id))
    result_code = RepoPublishResult.RESULT_SUCCESS
    result = RepoPublishResult.expected_result(
        repo_obj.repo_id, dist.distributor_id, dist.distributor_type_id,
        publish_start_timestamp, publish_end_timestamp, summary, details, result_code)
    publish_result_coll.save(result, safe=True)
    return result


def publish_history(start_date, end_date, repo_id, distributor_id):
    """
    Returns a cursor containing the publish history entries for the given repo and distributor.

    :param start_date: if specified, no events prior to this date will be returned.
    :type  start_date: iso8601 datetime string
    :param end_date: if specified, no events after this date will be returned.
    :type  end_date: iso8601 datetime string
    :param repo_id: identifies the repo
    :type  repo_id: str
    :param distributor_id: identifies the distributor to retrieve history for
    :type  distributor_id: str

    :return: object containing publish history results
    :rtype:  pymongo.cursor.Cursor

    :raise pulp_exceptions.MissingResource: if repo/distributor pair is invalid
    """
    model.Repository.objects.get_repo_or_missing_resource(repo_id)
    model.Distributor.objects.get_or_404(repo_id=repo_id, distributor_id=distributor_id)

    search_params = {'repo_id': repo_id, 'distributor_id': distributor_id}
    date_range = {}
    if start_date:
        date_range['$gte'] = start_date
    if end_date:
        date_range['$lte'] = end_date
    if len(date_range) > 0:
        search_params['started'] = date_range
    return RepoPublishResult.get_collection().find(search_params)


def _now_timestamp():
    """
    Return a current timestamp in iso8601 format.

    :return: iso8601 UTC timestamp with timezone specified.
    :rtype:  str
    """
    now = dateutils.now_utc_datetime_with_tzinfo()
    now_in_iso_format = dateutils.format_iso8601_datetime(now)
    return now_in_iso_format
