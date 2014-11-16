"""
This module contains the web controllers for Repositories.
"""
import logging
import sys

import web

from pulp.common import constants, dateutils, tags
from pulp.server.auth.authorization import CREATE, DELETE, EXECUTE, READ, UPDATE
from pulp.server.db.model.criteria import Criteria, UnitAssociationCriteria
from pulp.server.db.model.repository import Repo, RepoContentUnit
from pulp.server.managers.consumer.applicability import regenerate_applicability_for_repos
from pulp.server.managers.content.upload import import_uploaded_unit
from pulp.server.managers.repo.importer import remove_importer, set_importer, update_importer_config
from pulp.server.managers.repo.unit_association import associate_from_repo, unassociate_by_criteria
from pulp.server.tasks import repository
from pulp.server.webservices import serialization
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import auth_required
from pulp.server.webservices.controllers.schedule import ScheduleResource
from pulp.server.webservices.controllers.search import SearchController
import pulp.server.exceptions as exceptions
import pulp.server.managers.factory as manager_factory


_logger = logging.getLogger(__name__)


def _merge_related_objects(name, manager, repos):
    """
    Takes a list of Repo objects and adds their corresponding related objects
    in a list under the attribute given in 'name'. Uses the given manager to
    access the related objects by passing the list of IDs for the given repos.
    This is most commonly used for RepoImporter or RepoDistributor objects in
    lists under the 'importers' and 'distributors' attributes.

    @param name: name of the field, such as 'importers' or 'distributors'.
    @type  name: str

    @param manager: manager class for the object type. must implement a method
                    'find_by_repo_list' that takes a list of repo ids.

    @param repos: list of Repo instances that should have importers and
                  distributors added.
    @type  repos  list of Repo instances

    @return the same list that was passed in, just for convenience. The list
            itself is not modified- only its members are modified in-place.
    @rtype  list of Repo instances
    """
    repo_ids = tuple(repo['id'] for repo in repos)

    # make it cheap to access each repo by id
    repo_dict = dict((repo['id'], repo) for repo in repos)

    # guarantee that at least an empty list will be present
    for repo in repos:
        repo[name] = []

    for item in manager.find_by_repo_list(repo_ids):
        repo_dict[item['repo_id']][name].append(item)

    return repos


def _convert_repo_dates_to_strings(repo):
    """
    Convert the last_unit_added & last_unit_removed fields of a repository
    This modifies the repository in place

    :param repo:  diatabase representation of a repo
    :type repo: dict
    """
    # convert the native datetime object to a string with timezone specified
    last_unit_added = repo.get('last_unit_added')
    if last_unit_added:
        new_date = dateutils.to_utc_datetime(last_unit_added,
                                             no_tz_equals_local_tz=False)
        repo['last_unit_added'] = dateutils.format_iso8601_datetime(new_date)
    last_unit_removed = repo.get('last_unit_removed')
    if last_unit_removed:
        new_date = dateutils.to_utc_datetime(last_unit_removed,
                                             no_tz_equals_local_tz=False)
        repo['last_unit_removed'] = dateutils.format_iso8601_datetime(new_date)


class RepoCollection(JSONController):

    # Scope: Collection
    # GET:   Retrieve all repositories in the system
    # POST:  Repository Create

    @staticmethod
    def _process_repos(repos, importers=False, distributors=False):
        """
        Apply standard processing to a collection of repositories being returned
        to a client. Adds the object link and optionally adds related importers
        and distributors.

        @param repos: collection of repositories
        @type  repos: list, tuple

        @param importers:   iff True, adds related importers under the
                            attribute "importers".
        @type  importers:   bool

        @param distributors:    iff True, adds related distributors under the
                                attribute "distributors".
        @type  distributors:    bool

        @return the same list that was passed in, just for convenience. The list
                itself is not modified- only its members are modified in-place.
        @rtype  list of Repo instances
        """
        if importers:
            _merge_related_objects(
                'importers', manager_factory.repo_importer_manager(), repos)
        if distributors:
            _merge_related_objects(
                'distributors', manager_factory.repo_distributor_manager(), repos)

        for repo in repos:
            repo.update(serialization.link.search_safe_link_obj(repo['id']))
            _convert_repo_dates_to_strings(repo)

            # Remove internally used scratchpad from repo details
            if 'scratchpad' in repo:
                del repo['scratchpad']

        return repos

    @auth_required(READ)
    def GET(self):
        """
        Looks for query parameters 'importers' and 'distributors', and will add
        the corresponding fields to the each repository returned. Query
        parameter 'details' is equivalent to passing both 'importers' and
        'distributors'.
        """
        query_params = web.input()
        all_repos = list(Repo.get_collection().find(projection={'scratchpad': 0}))

        if query_params.get('details', False):
            query_params['importers'] = True
            query_params['distributors'] = True

        self._process_repos(
            all_repos,
            query_params.get('importers', False),
            query_params.get('distributors', False)
        )

        # Return the repos or an empty list; either way it's a 200
        return self.ok(all_repos)

    @auth_required(CREATE)
    def POST(self):

        # Pull the repo data out of the request body (validation will occur
        # in the manager)
        repo_data = self.params()
        id = repo_data.get('id', None)
        display_name = repo_data.get('display_name', None)
        description = repo_data.get('description', None)
        notes = repo_data.get('notes', None)

        importer_type_id = repo_data.get('importer_type_id', None)
        importer_repo_plugin_config = repo_data.get('importer_config', None)

        distributors = repo_data.get('distributors', None)

        # Creation
        repo_manager = manager_factory.repo_manager()
        args = [id, display_name, description, notes]
        kwargs = {'importer_type_id': importer_type_id,
                  'importer_repo_plugin_config': importer_repo_plugin_config,
                  'distributor_list': distributors}
        repo = repo_manager.create_and_configure_repo(*args, **kwargs)
        repo.update(serialization.link.child_link_obj(id))
        return self.created(id, repo)


class RepoSearch(SearchController):
    def __init__(self):
        super(RepoSearch, self).__init__(
            manager_factory.repo_query_manager().find_by_criteria)

    @auth_required(READ)
    def GET(self):
        query_params = web.input()
        if query_params.pop('details', False):
            query_params['importers'] = True
            query_params['distributors'] = True
        items = self._get_query_results_from_get(
            ('details', 'importers', 'distributors'))

        RepoCollection._process_repos(
            items,
            query_params.pop('importers', False),
            query_params.pop('distributors', False)
        )
        return self.ok(items)

    @auth_required(READ)
    def POST(self):
        """
        Searches based on a Criteria object. Requires a posted parameter
        'criteria' which has a data structure that can be turned into a
        Criteria instance.
        """
        items = self._get_query_results_from_post()

        RepoCollection._process_repos(
            items,
            self.params().get('importers', False),
            self.params().get('distributors', False)
        )
        return self.ok(items)


class RepoResource(JSONController):

    # Scope:   Resource
    # GET:     Repository Retrieval
    # DELETE:  Repository Delete
    # PUT:     Repository Update

    @auth_required(READ)
    def GET(self, id):
        """
        Looks for query parameters 'importers' and 'distributors', and will add
        the corresponding fields to the repository returned. Query parameter
        'details' is equivalent to passing both 'importers' and 'distributors'.
        """
        query_params = web.input()
        query_manager = manager_factory.repo_query_manager()
        repo = query_manager.find_by_id(id)

        if repo is None:
            raise exceptions.MissingResource(repo=id)

        repo.update(serialization.link.current_link_obj())
        _convert_repo_dates_to_strings(repo)

        if query_params.get('details', False):
            query_params['importers'] = True
            query_params['distributors'] = True

        if query_params.get('importers', False):
            repo = _merge_related_objects(
                'importers', manager_factory.repo_importer_manager(), (repo,))[0]
        if query_params.get('distributors', False):
            repo = _merge_related_objects(
                'distributors', manager_factory.repo_distributor_manager(), (repo,))[0]

        return self.ok(repo)

    @auth_required(DELETE)
    def DELETE(self, repo_id):
        # validate
        manager_factory.repo_query_manager().get_repository(repo_id)

        # delete
        task_tags = [
            tags.resource_tag(tags.RESOURCE_REPOSITORY_TYPE, repo_id),
            tags.action_tag('delete')
        ]
        async_result = repository.delete.apply_async_with_reservation(
            tags.RESOURCE_REPOSITORY_TYPE, repo_id,
            [repo_id], tags=task_tags)

        raise exceptions.OperationPostponed(async_result)

    @auth_required(UPDATE)
    def PUT(self, repo_id):
        parameters = self.params()
        delta = parameters.get('delta', None)
        importer_config = parameters.get('importer_config', None)
        distributor_configs = parameters.get('distributor_configs', None)

        repo_manager = manager_factory.repo_manager()

        task_result = repo_manager.update_repo_and_plugins(repo_id, delta, importer_config,
                                                           distributor_configs)
        # TODO Old CallRequest used to kwarg_blacklist the importer_config and distributor_config
        # TODO Do we need to filter those out here?
        repo = task_result.return_value
        repo.update(serialization.link.current_link_obj())
        _convert_repo_dates_to_strings(repo)

        # If tasks were spawned, raise that as a result
        if task_result.spawned_tasks:
            raise exceptions.OperationPostponed(task_result)

        result = task_result.serialize()
        return self.ok(result)


class RepoImporters(JSONController):

    # Scope:  Sub-collection
    # GET:    List Importers
    # POST:   Set Importer

    @auth_required(READ)
    def GET(self, repo_id):
        importer_manager = manager_factory.repo_importer_manager()

        importers = importer_manager.get_importers(repo_id)
        return self.ok(importers)

    @auth_required(CREATE)
    def POST(self, repo_id):

        # Params (validation will occur in the manager)
        params = self.params()
        importer_type = params.get('importer_type_id', None)
        importer_config = params.get('importer_config', None)

        if importer_type is None:
            _logger.error('Missing importer type adding importer to repository [%s]' % repo_id)
            raise exceptions.MissingValue(['importer_type'])

        # Note: If an importer exists, it's removed, so no need to handle 409s.
        # Note: If the plugin raises an exception during initialization, let it
        #  bubble up and be handled like any other 500.

        task_tags = [tags.resource_tag(tags.RESOURCE_REPOSITORY_TYPE, repo_id),
                     tags.action_tag('add_importer')]
        async_result = set_importer.apply_async_with_reservation(
            tags.RESOURCE_REPOSITORY_TYPE, repo_id, [repo_id, importer_type],
            {'repo_plugin_config': importer_config}, tags=task_tags)
        raise exceptions.OperationPostponed(async_result)


class RepoImporter(JSONController):

    # Scope:  Exclusive Sub-resource
    # GET:    Get Importer
    # DELETE: Remove Importer
    # PUT:    Update Importer Config

    @auth_required(READ)
    def GET(self, repo_id, importer_id):

        # importer_id is there to meet the REST requirement, so leave it there
        # despite it not being used in this method.

        importer_manager = manager_factory.repo_importer_manager()

        importer = importer_manager.get_importer(repo_id)
        return self.ok(importer)

    @auth_required(UPDATE)
    def DELETE(self, repo_id, importer_id):

        task_tags = [tags.resource_tag(tags.RESOURCE_REPOSITORY_TYPE, repo_id),
                     tags.resource_tag(tags.RESOURCE_REPOSITORY_IMPORTER_TYPE, importer_id),
                     tags.action_tag('delete_importer')]
        async_result = remove_importer.apply_async_with_reservation(
            tags.RESOURCE_REPOSITORY_TYPE, repo_id, [repo_id], tags=task_tags)
        raise exceptions.OperationPostponed(async_result)

    @auth_required(UPDATE)
    def PUT(self, repo_id, importer_id):

        # Params (validation will occur in the manager)
        params = self.params()
        importer_config = params.get('importer_config', None)

        if importer_config is None:
            _logger.error('Missing configuration updating importer for repository [%s]' % repo_id)
            raise exceptions.MissingValue(['importer_config'])

        task_tags = [tags.resource_tag(tags.RESOURCE_REPOSITORY_TYPE, repo_id),
                     tags.resource_tag(tags.RESOURCE_REPOSITORY_IMPORTER_TYPE, importer_id),
                     tags.action_tag('update_importer')]
        async_result = update_importer_config.apply_async_with_reservation(
            tags.RESOURCE_REPOSITORY_TYPE,
            repo_id, [repo_id], {'importer_config': importer_config}, tags=task_tags)
        raise exceptions.OperationPostponed(async_result)


class SyncScheduleCollection(JSONController):

    # Scope: sub-sub-collection
    # GET:   list all scheduled syncs
    # POST:  create new scheduled sync

    @auth_required(READ)
    def GET(self, repo_id, importer_id):
        manager = manager_factory.repo_sync_schedule_manager()
        schedules = manager.list(repo_id, importer_id)
        for_display = [schedule.for_display() for schedule in schedules]
        for entry in for_display:
            entry.update(serialization.link.child_link_obj(entry['_id']))

        return self.ok(for_display)

    @auth_required(CREATE)
    def POST(self, repo_id, importer_id):
        manager = manager_factory.repo_sync_schedule_manager()

        params = self.params()
        sync_options = {'override_config': params.pop('override_config', {})}
        schedule = params.pop('schedule', None)
        failure_threshold = params.pop('failure_threshold', None)
        enabled = params.pop('enabled', True)
        if params:
            raise exceptions.UnsupportedValue(params.keys())

        scheduled_call = manager.create(repo_id, importer_id, sync_options,
                                        schedule, failure_threshold, enabled)

        ret = scheduled_call.for_display()
        ret.update(serialization.link.child_link_obj(scheduled_call.id))
        return self.created(ret['_href'], ret)


class SyncScheduleResource(ScheduleResource):
    def __init__(self):
        super(SyncScheduleResource, self).__init__()
        self.manager = manager_factory.repo_sync_schedule_manager()

    # Scope:  exclusive sub-sub-resource
    # DELETE: remove a scheduled sync
    # GET:    get a representation of the scheduled sync
    # PUT:    change a scheduled sync

    @auth_required(DELETE)
    def DELETE(self, repo_id, importer_id, schedule_id):
        result = self.manager.delete(repo_id, importer_id, schedule_id)
        return self.ok(result)

    @auth_required(READ)
    def GET(self, repo_id, importer_id, schedule_id):
        self.manager.validate_importer(repo_id, importer_id)
        return self._get(schedule_id)

    @auth_required(UPDATE)
    def PUT(self, repo_id, importer_id, schedule_id):
        updates = self.params()
        if 'schedule' in updates:
            updates['iso_schedule'] = updates.pop('schedule')
        schedule = self.manager.update(repo_id, importer_id, schedule_id, updates)
        ret = schedule.for_display()
        ret.update(serialization.link.current_link_obj())
        return self.ok(ret)


class RepoDistributors(JSONController):

    # Scope:  Sub-collection
    # GET:    List Distributors
    # POST:   Add Distributor

    @auth_required(READ)
    def GET(self, repo_id):
        distributor_manager = manager_factory.repo_distributor_manager()

        distributor_list = distributor_manager.get_distributors(repo_id)
        return self.ok(distributor_list)

    @auth_required(CREATE)
    def POST(self, repo_id):

        # Params (validation will occur in the manager)
        params = self.params()
        distributor_type = params.get('distributor_type_id', None)
        distributor_config = params.get('distributor_config', None)
        distributor_id = params.get('distributor_id', None)
        auto_publish = params.get('auto_publish', False)

        distributor_manager = manager_factory.repo_distributor_manager()
        distributor = distributor_manager.add_distributor(repo_id,
                                                          distributor_type,
                                                          distributor_config,
                                                          auto_publish,
                                                          distributor_id)
        distributor.update(serialization.link.child_link_obj(distributor['id']))
        return self.created(distributor['_href'], distributor)


class RepoDistributor(JSONController):

    # Scope:  Exclusive Sub-resource
    # GET:    Get Distributor
    # DELETE: Remove Distributor
    # PUT:    Update Distributor Config

    @auth_required(READ)
    def GET(self, repo_id, distributor_id):
        distributor_manager = manager_factory.repo_distributor_manager()

        distributor = distributor_manager.get_distributor(repo_id, distributor_id)
        return self.ok(distributor)

    @auth_required(UPDATE)
    def DELETE(self, repo_id, distributor_id):
        # validate resources
        manager = manager_factory.repo_distributor_manager()
        manager.get_distributor(repo_id, distributor_id)
        # delete
        task_tags = [
            tags.resource_tag(tags.RESOURCE_REPOSITORY_TYPE, repo_id),
            tags.resource_tag(tags.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE, distributor_id),
            tags.action_tag('remove_distributor')
        ]

        async_result = repository.distributor_delete.apply_async_with_reservation(
            tags.RESOURCE_REPOSITORY_TYPE, repo_id, [repo_id, distributor_id],
            tags=task_tags)

        raise exceptions.OperationPostponed(async_result)

    @auth_required(UPDATE)
    def PUT(self, repo_id, distributor_id):
        """
        Used to update a repo distributor instance. This requires update permissions.
        The expected parameters are 'distributor_config', which is a dictionary containing
        configuration values accepted by the distributor type, and 'delta', which is a dictionary
        containing other configuration values for the distributor (like the auto_publish flag,
        for example). Currently, the only supported key in the delta is 'auto_publish', which
        should have a boolean value.

        :param repo_id:         The repository ID
        :type  repo_id:         str
        :param distributor_id:  The unique distributor ID of the distributor instance to update.
        :type  distributor_id:  str
        """
        params = self.params()
        delta = params.get('delta', None)
        # validate
        manager = manager_factory.repo_distributor_manager()
        manager.get_distributor(repo_id, distributor_id)
        config = params.get('distributor_config')
        if config is None:
            _logger.error(
                'Missing configuration when updating distributor [%s] on repository [%s]',
                distributor_id,
                repo_id)
            raise exceptions.MissingValue(['distributor_config'])
        # update
        task_tags = [
            tags.resource_tag(tags.RESOURCE_REPOSITORY_TYPE, repo_id),
            tags.resource_tag(tags.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE, distributor_id),
            tags.action_tag('update_distributor')
        ]
        async_result = repository.distributor_update.apply_async_with_reservation(
            tags.RESOURCE_REPOSITORY_TYPE, repo_id,
            [repo_id, distributor_id, config, delta], tags=task_tags)
        raise exceptions.OperationPostponed(async_result)


class PublishScheduleCollection(JSONController):

    # Scope: sub-sub-collection
    # GET:   list all scheduled publishes
    # POST:  create new scheduled publish

    @auth_required(READ)
    def GET(self, repo_id, distributor_id):
        manager = manager_factory.repo_publish_schedule_manager()
        schedules = manager.list(repo_id, distributor_id)
        for_display = [schedule.for_display() for schedule in schedules]
        for entry in for_display:
            entry.update(serialization.link.child_link_obj(entry['_id']))

        return self.ok(for_display)

    @auth_required(CREATE)
    def POST(self, repo_id, distributor_id):
        manager = manager_factory.repo_publish_schedule_manager()

        params = self.params()
        publish_options = {'override_config': params.pop('override_config', {})}
        schedule = params.pop('schedule', None)
        failure_threshold = params.pop('failure_threshold', None)
        enabled = params.pop('enabled', True)
        if params:
            raise exceptions.UnsupportedValue(params.keys())

        schedule = manager.create(repo_id, distributor_id, publish_options,
                                  schedule, failure_threshold, enabled)

        ret = schedule.for_display()
        ret.update(serialization.link.child_link_obj(schedule.id))
        return self.created(ret['_href'], ret)


class PublishScheduleResource(ScheduleResource):
    def __init__(self):
        super(PublishScheduleResource, self).__init__()
        self.manager = manager_factory.repo_publish_schedule_manager()

    # Scope:  exclusive sub-sub-resource
    # DELETE: remove a scheduled publish
    # GET:    get a representation of the scheduled publish
    # PUT:    change a scheduled publish

    @auth_required(DELETE)
    def DELETE(self, repo_id, distributor_id, schedule_id):
        result = self.manager.delete(repo_id, distributor_id, schedule_id)
        return self.ok(result)

    @auth_required(READ)
    def GET(self, repo_id, distributor_id, schedule_id):
        self.manager.validate_distributor(repo_id, distributor_id)
        return self._get(schedule_id)

    @auth_required(UPDATE)
    def PUT(self, repo_id, distributor_id, schedule_id):
        updates = self.params()
        if 'schedule' in updates:
            updates['iso_schedule'] = updates.pop('schedule')
        schedule = self.manager.update(repo_id, distributor_id, schedule_id, updates)
        ret = schedule.for_display()
        ret.update(serialization.link.current_link_obj())
        return self.ok(ret)


class RepoSyncHistory(JSONController):

    # Scope: Resource
    # GET:   Get history entries for the given repo

    @auth_required(READ)
    def GET(self, repo_id):
        # Params
        filters = self.filters(
            [constants.REPO_HISTORY_FILTER_LIMIT, constants.REPO_HISTORY_FILTER_SORT,
             constants.REPO_HISTORY_FILTER_START_DATE,
             constants.REPO_HISTORY_FILTER_END_DATE])
        limit = filters.get(constants.REPO_HISTORY_FILTER_LIMIT, None)
        sort = filters.get(constants.REPO_HISTORY_FILTER_SORT, None)
        start_date = filters.get(constants.REPO_HISTORY_FILTER_START_DATE, None)
        end_date = filters.get(constants.REPO_HISTORY_FILTER_END_DATE, None)

        if limit is not None:
            try:
                limit = int(limit[0])
            except ValueError:
                _logger.error('Invalid limit specified [%s]' % limit)
                raise exceptions.InvalidValue([constants.REPO_HISTORY_FILTER_LIMIT])
        # Error checking is done on these options in the sync manager before the database is queried
        if sort is None:
            sort = constants.SORT_DESCENDING
        else:
            sort = sort[0]
        if start_date:
            start_date = start_date[0]
        if end_date:
            end_date = end_date[0]

        sync_manager = manager_factory.repo_sync_manager()
        entries = sync_manager.sync_history(repo_id, limit=limit, sort=sort, start_date=start_date,
                                            end_date=end_date)
        return self.ok(entries)


class RepoPublishHistory(JSONController):

    # Scope: Resource
    # GET:   Get history entries for the given repo

    @auth_required(READ)
    def GET(self, repo_id, distributor_id):
        # Params
        filters = self.filters([constants.REPO_HISTORY_FILTER_LIMIT,
                                constants.REPO_HISTORY_FILTER_SORT,
                                constants.REPO_HISTORY_FILTER_START_DATE,
                                constants.REPO_HISTORY_FILTER_END_DATE])
        limit = filters.get(constants.REPO_HISTORY_FILTER_LIMIT, None)
        sort = filters.get(constants.REPO_HISTORY_FILTER_SORT, None)
        start_date = filters.get(constants.REPO_HISTORY_FILTER_START_DATE, None)
        end_date = filters.get(constants.REPO_HISTORY_FILTER_END_DATE, None)

        if limit is not None:
            try:
                limit = int(limit[0])
            except ValueError:
                _logger.error('Invalid limit specified [%s]' % limit)
                raise exceptions.InvalidValue([constants.REPO_HISTORY_FILTER_LIMIT])
        if sort is None:
            sort = constants.SORT_DESCENDING
        else:
            sort = sort[0]
        if start_date:
            start_date = start_date[0]
        if end_date:
            end_date = end_date[0]

        publish_manager = manager_factory.repo_publish_manager()
        entries = publish_manager.publish_history(repo_id, distributor_id, limit=limit, sort=sort,
                                                  start_date=start_date, end_date=end_date)
        return self.ok(entries)


class RepoSync(JSONController):

    # Scope: Action
    # POST:  Trigger a repo sync

    @auth_required(EXECUTE)
    def POST(self, repo_id):

        # Params
        params = self.params()
        overrides = params.get('override_config', None)

        # Check for repo existence and let the missing resource bubble up
        manager_factory.repo_query_manager().get_repository(repo_id)

        # Execute the sync asynchronously
        task_tags = [tags.resource_tag(tags.RESOURCE_REPOSITORY_TYPE, repo_id),
                     tags.action_tag('sync')]
        async_result = repository.sync_with_auto_publish.apply_async_with_reservation(
            tags.RESOURCE_REPOSITORY_TYPE, repo_id, [repo_id, overrides], {}, tags=task_tags)

        # this raises an exception that is handled by the middleware,
        # so no return is needed
        raise exceptions.OperationPostponed(async_result)


class RepoPublish(JSONController):

    # Scope: Action
    # POST:  Trigger a repo publish

    @auth_required(EXECUTE)
    def POST(self, repo_id):
        # validation
        manager = manager_factory.repo_query_manager()
        manager.get_repository(repo_id)

        # Params
        params = self.params()
        distributor_id = params.get('id', None)
        overrides = params.get('override_config', None)
        async_result = repository.publish(repo_id, distributor_id, overrides)
        raise exceptions.OperationPostponed(async_result)


class RepoAssociate(JSONController):

    # Scope: Action
    # POST:  Associate units from a repository into the given repository

    @auth_required(UPDATE)
    def POST(self, dest_repo_id):

        # Params
        params = self.params()
        source_repo_id = params.get('source_repo_id', None)
        overrides = params.get('override_config', None)

        if source_repo_id is None:
            raise exceptions.MissingValue(['source_repo_id'])

        # A 404 only applies to things in the URL, so the destination repo
        # check allows the MissingResource to bubble up, but if the source
        # repo doesn't exist, it's considered bad data.
        repo_query_manager = manager_factory.repo_query_manager()
        repo_query_manager.get_repository(dest_repo_id)

        try:
            repo_query_manager.get_repository(source_repo_id)
        except exceptions.MissingResource:
            raise exceptions.InvalidValue(['source_repo_id'])

        criteria = params.get('criteria', None)
        if criteria is not None:
            try:
                criteria = UnitAssociationCriteria.from_client_input(criteria)
            except:
                _logger.error('Error parsing association criteria [%s]' % criteria)
                raise exceptions.PulpDataException(), None, sys.exc_info()[2]

        task_tags = [tags.resource_tag(tags.RESOURCE_REPOSITORY_TYPE, dest_repo_id),
                     tags.resource_tag(tags.RESOURCE_REPOSITORY_TYPE, source_repo_id),
                     tags.action_tag('associate')]
        async_result = associate_from_repo.apply_async_with_reservation(
            tags.RESOURCE_REPOSITORY_TYPE, dest_repo_id, [source_repo_id, dest_repo_id],
            {'criteria': criteria, 'import_config_override': overrides}, tags=task_tags)
        raise exceptions.OperationPostponed(async_result)


class RepoUnassociate(JSONController):

    # Scope: Action
    # POST: Unassociate units from a repository

    @auth_required(UPDATE)
    def POST(self, repo_id):

        params = self.params()
        criteria = params.get('criteria', None)

        if criteria is not None:
            try:
                criteria = UnitAssociationCriteria.from_client_input(criteria)
            except:
                _logger.error('Error parsing unassociation criteria [%s]' % criteria)
                raise exceptions.PulpDataException(), None, sys.exc_info()[2]

        task_tags = [tags.resource_tag(tags.RESOURCE_REPOSITORY_TYPE, repo_id),
                     tags.action_tag('unassociate')]
        async_result = unassociate_by_criteria.apply_async_with_reservation(
            tags.RESOURCE_REPOSITORY_TYPE, repo_id,
            [repo_id, criteria, RepoContentUnit.OWNER_TYPE_USER,
             manager_factory.principal_manager().get_principal()['login']], tags=task_tags)
        raise exceptions.OperationPostponed(async_result)


class RepoImportUpload(JSONController):

    @auth_required(UPDATE)
    def POST(self, repo_id):
        """
        Import an uploaded unit into the given repository.

        :param repo_id: The id of the repository the upload should be imported into
        :type  repo_id: basestring
        :return:        A json serialized dictionary with two keys. 'success_flag' indexes a boolean
                        value that indicates whether the import was successful, and 'summary' will
                        contain the summary as reported by the Importer.
        :rtype:         basestring
        """
        # Collect user input
        params = self.params()
        upload_id = params['upload_id']
        unit_type_id = params['unit_type_id']
        unit_key = params['unit_key']
        unit_metadata = params.pop('unit_metadata', None)
        override_config = params.pop('override_config', None)

        task_tags = [tags.resource_tag(tags.RESOURCE_REPOSITORY_TYPE, repo_id),
                     tags.action_tag('import_upload')]
        async_result = import_uploaded_unit.apply_async_with_reservation(
            tags.RESOURCE_REPOSITORY_TYPE, repo_id,
            [repo_id, unit_type_id, unit_key, unit_metadata, upload_id, override_config],
            tags=task_tags)
        raise exceptions.OperationPostponed(async_result)


class RepoResolveDependencies(JSONController):

    # Scope: Actions
    # POST:  Resolve and return dependencies for one or more units

    @auth_required(READ)
    def POST(self, repo_id):
        # Params
        params = self.params()
        query = params.get('criteria', {})
        options = params.get('options', {})
        timeout = params.get('timeout', 60)

        try:
            criteria = UnitAssociationCriteria.from_client_input(query)
        except:
            _logger.error('Error parsing association criteria [%s]' % query)
            raise exceptions.PulpDataException(), None, sys.exc_info()[2]

        try:
            timeout = int(timeout)
        except ValueError:
            raise exceptions.InvalidValue(['timeout']), None, sys.exc_info()[2]

        dependency_manager = manager_factory.dependency_manager()
        result = dependency_manager.resolve_dependencies_by_criteria(repo_id, criteria, options)
        return self.ok(result)


class RepoUnitAdvancedSearch(JSONController):

    # Scope: Search
    # POST:  Advanced search for repo unit associations

    @auth_required(READ)
    def POST(self, repo_id):
        # Params
        params = self.params()
        query = params.get('criteria', None)

        repo_query_manager = manager_factory.repo_query_manager()
        repo = repo_query_manager.find_by_id(repo_id)
        if repo is None:
            raise exceptions.MissingResource(repo_id=repo_id)

        if query is None:
            raise exceptions.MissingValue(['criteria'])

        try:
            criteria = UnitAssociationCriteria.from_client_input(query)
        except:
            _logger.error('Error parsing association criteria [%s]' % query)
            raise exceptions.PulpDataException(), None, sys.exc_info()[2]

        # Data lookup
        manager = manager_factory.repo_unit_association_query_manager()
        if criteria.type_ids is not None and len(criteria.type_ids) == 1:
            type_id = criteria.type_ids[0]
            units = manager.get_units_by_type(repo_id, type_id, criteria=criteria)
        else:
            units = manager.get_units_across_types(repo_id, criteria=criteria)

        return self.ok(units)


class ContentApplicabilityRegeneration(JSONController):
    """
    Content applicability regeneration for updated repositories.
    """
    @auth_required(CREATE)
    def POST(self):
        """
        Creates an async task to regenerate content applicability data for given updated
        repositories.

        body {repo_criteria:<dict>}
        """
        body = self.params()
        repo_criteria = body.get('repo_criteria', None)
        if repo_criteria is None:
            raise exceptions.MissingValue('repo_criteria')
        try:
            repo_criteria = Criteria.from_client_input(repo_criteria)
        except:
            raise exceptions.InvalidValue('repo_criteria')

        regeneration_tag = tags.action_tag('content_applicability_regeneration')
        async_result = regenerate_applicability_for_repos.apply_async_with_reservation(
            tags.RESOURCE_REPOSITORY_PROFILE_APPLICABILITY_TYPE, tags.RESOURCE_ANY_ID,
            (repo_criteria.as_dict(),), tags=[regeneration_tag])
        raise exceptions.OperationPostponed(async_result)


# These are defined under /v2/repositories/ (see application.py to double-check)
urls = (
    '/', 'RepoCollection',  # collection
    '/search/$', 'RepoSearch',  # resource search
    '/actions/content/regenerate_applicability/$', ContentApplicabilityRegeneration,
    '/([^/]+)/$', 'RepoResource',  # resource

    '/([^/]+)/importers/$', 'RepoImporters',  # sub-collection
    '/([^/]+)/importers/([^/]+)/$', 'RepoImporter',  # exclusive sub-resource
    '/([^/]+)/importers/([^/]+)/schedules/sync/$', 'SyncScheduleCollection',
    '/([^/]+)/importers/([^/]+)/schedules/sync/([^/]+)/$', 'SyncScheduleResource',

    '/([^/]+)/distributors/$', 'RepoDistributors',  # sub-collection
    '/([^/]+)/distributors/([^/]+)/$', 'RepoDistributor',  # exclusive sub-resource
    '/([^/]+)/distributors/([^/]+)/schedules/publish/$', 'PublishScheduleCollection',
    '/([^/]+)/distributors/([^/]+)/schedules/publish/([^/]+)/$', 'PublishScheduleResource',

    '/([^/]+)/history/sync/$', 'RepoSyncHistory',  # sub-collection
    '/([^/]+)/history/publish/([^/]+)/$', 'RepoPublishHistory',  # sub-collection

    '/([^/]+)/actions/sync/$', 'RepoSync',  # resource action
    '/([^/]+)/actions/publish/$', 'RepoPublish',  # resource action
    '/([^/]+)/actions/associate/$', 'RepoAssociate',  # resource action
    '/([^/]+)/actions/unassociate/$', 'RepoUnassociate',  # resource action
    '/([^/]+)/actions/import_upload/$', 'RepoImportUpload',  # resource action
    '/([^/]+)/actions/resolve_dependencies/$', 'RepoResolveDependencies',  # resource action

    '/([^/]+)/search/units/$', 'RepoUnitAdvancedSearch',  # resource search
)

application = web.application(urls, globals())
