from django.core.urlresolvers import reverse
from django.views.generic import View

from pulp.common import constants, dateutils, tags
from pulp.server import exceptions as pulp_exceptions
from pulp.server.auth import authorization
from pulp.server.db.model.criteria import Criteria, UnitAssociationCriteria
from pulp.server.db.model.repository import Repo as RepoModel
from pulp.server.managers import factory as manager_factory
from pulp.server.managers.consumer.applicability import regenerate_applicability_for_repos
from pulp.server.managers.content.upload import import_uploaded_unit
from pulp.server.managers.repo import query as repo_query
from pulp.server.managers.repo import importer as repo_importer_manager
from pulp.server.managers.repo.distributor import RepoDistributorManager
from pulp.server.managers.repo.unit_association import associate_from_repo, unassociate_by_criteria
from pulp.server.tasks import repository as repo_tasks
from pulp.server.webservices.views import search
from pulp.server.webservices.views.decorators import auth_required
from pulp.server.webservices.views.schedule import ScheduleResource
from pulp.server.webservices.views.util import (generate_json_response,
                                                generate_json_response_with_pulp_encoder,
                                                generate_redirect_response,
                                                json_body_allow_empty,
                                                json_body_required)


def _merge_related_objects(name, manager, repos):
    """
    Takes a list of Repo objects and adds their corresponding related objects
    in a list under the attribute given in 'name'. Uses the given manager to
    access the related objects by passing the list of IDs for the given repos.
    This is most commonly used for RepoImporter or RepoDistributor objects in
    lists under the 'importers' and 'distributors' attributes.

    :param name: name of the field, such as 'importers' or 'distributors'.
    :type  name: str
    :param manager: manager class for the object type. must implement a method 'find_by_repo_list'
                    that takes a list of repo ids.
    :type  manager: class
    :param repos: list of Repo instances that should have importers and distributors added.
    :type  repos: list of Repo instances
    :return: the same list that was passed in, just for convenience. The list itself is not
             modified- only its members are modified in-place.
    :rtype:  list of Repo instances
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

    :param repo: database representation of a repo
    :type  repo: dict
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


def _process_repos(repos, details, importers, distributors):
    """
    Apply standard processing to a collection of repositories being returned to a client. Adds
    the object link and optionally adds related importers and distributors.

    :param repos: collection of repositories
    :type  repos: list, tuple
    :param importers: if `true`, adds related importers under the attribute "importers".
    :type  importers: str
    :param distributors: if `true`, adds related distributors under the attribute "distributors"
    :type  distributors: str

    :return: the same list that was passed in, just for convenience. The list itself is not
             modified- only its members are modified in-place.
    :rtype:  list of Repo instances
    """
    if details.lower() == 'true':
        importers = distributors = 'true'
    if importers.lower() == 'true':
        _merge_related_objects(
            'importers', manager_factory.repo_importer_manager(), repos)
    if distributors.lower() == 'true':
        _merge_related_objects(
            'distributors', manager_factory.repo_distributor_manager(), repos)
    for repo in repos:
        repo['_href'] = reverse('repo_resource', kwargs={'repo_id': repo['id']})
        _convert_repo_dates_to_strings(repo)
        # Remove internally used scratchpad from repo details
        if 'scratchpad' in repo:
            del repo['scratchpad']
    return repos


class ReposView(View):
    """
    View for all repos.
    """

    @auth_required(authorization.READ)
    def get(self, request):
        """
        Return information about all repositories.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest

        :return: Response containing a list of dicts, one for each repo
        :rtype : django.http.HttpResponse
        """

        all_repos = list(RepoModel.get_collection().find(projection={'scratchpad': 0}))

        details = request.GET.get('details', 'false')
        include_importers = request.GET.get('importers', 'false')
        include_distributors = request.GET.get('distributors', 'false')

        _process_repos(
            all_repos,
            details,
            include_importers,
            include_distributors
        )

        return generate_json_response_with_pulp_encoder(all_repos)

    @auth_required(authorization.CREATE)
    @json_body_required
    def post(self, request):
        """
        Create a new repo. 'id' field in body is required.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest

        :return: Response containing a serialized dict for the created repo.
        :rtype : django.http.HttpResponse
        """

        # Pull the repo data out of the request body (validation will occur
        # in the manager)
        repo_data = request.body_as_json
        repo_id = repo_data.get('id', None)
        display_name = repo_data.get('display_name', None)
        description = repo_data.get('description', None)
        notes = repo_data.get('notes', None)

        importer_type_id = repo_data.get('importer_type_id', None)
        importer_repo_plugin_config = repo_data.get('importer_config', None)
        distributors = repo_data.get('distributors', None)

        # Creation
        repo_manager = manager_factory.repo_manager()
        args = [repo_id, display_name, description, notes]
        kwargs = {'importer_type_id': importer_type_id,
                  'importer_repo_plugin_config': importer_repo_plugin_config,
                  'distributor_list': distributors}
        repo = repo_manager.create_and_configure_repo(*args, **kwargs)
        repo['_href'] = reverse('repo_resource', kwargs={'repo_id': repo_id})
        response = generate_json_response_with_pulp_encoder(repo)
        return generate_redirect_response(response, repo['_href'])


class RepoResourceView(View):
    """
    View for a single repository.
    """

    @auth_required(authorization.READ)
    def get(self, request, repo_id):
        """
        Looks for query parameters 'importers' and 'distributors', and will add
        the corresponding fields to the repository returned. Query parameter
        'details' is equivalent to passing both 'importers' and 'distributors'.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param repo_id: id of requested repository
        :type  repo_id: str

        :return: Response containing a serialized dict for the requested repo.
        :rtype : django.http.HttpResponse
        :raises pulp_exceptions.MissingResource: if repo cannot be found
        """

        query_manager = manager_factory.repo_query_manager()
        repo = query_manager.find_by_id(repo_id)

        if repo is None:
            raise pulp_exceptions.MissingResource(repo=repo_id)

        repo['_href'] = reverse('repo_resource', kwargs={'repo_id': repo_id})
        _convert_repo_dates_to_strings(repo)

        details = request.GET.get('details', 'false').lower() == 'true'
        if request.GET.get('importers', 'false').lower() == 'true' or details:
            repo = _merge_related_objects(
                'importers', manager_factory.repo_importer_manager(), (repo,))[0]
        if request.GET.get('distributors', 'false').lower() == 'true' or details:
            repo = _merge_related_objects(
                'distributors', manager_factory.repo_distributor_manager(), (repo,))[0]

        return generate_json_response_with_pulp_encoder(repo)

    @auth_required(authorization.DELETE)
    def delete(self, request, repo_id):
        """
        Dispatch a task to delete a repository.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param repo_id: id of repository to be removed
        :type  repo_id: str

        :rtype : django.http.HttpResponse
        :raises pulp_exceptions.OperationPostponed: dispatch a task to delete the provided repo
        """

        # validate
        manager_factory.repo_query_manager().get_repository(repo_id)

        task_tags = [
            tags.resource_tag(tags.RESOURCE_REPOSITORY_TYPE, repo_id),
            tags.action_tag('delete')
        ]
        async_result = repo_tasks.delete.apply_async_with_reservation(
            tags.RESOURCE_REPOSITORY_TYPE, repo_id,
            [repo_id], tags=task_tags)

        raise pulp_exceptions.OperationPostponed(async_result)

    @auth_required(authorization.UPDATE)
    @json_body_allow_empty
    def put(self, request, repo_id):
        """
        Update a repository. This call will return synchronously unless a distributor is updated.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param repo_id: id of repository to be updated
        :type  repo_id: str

        :return: Response containing a serialized dict for the updated repo.
        :rtype : django.http.HttpResponse
        :raises pulp_exceptions.OperationPostponed: if a distributor is updated, dispatch a task
        """

        delta = request.body_as_json.get('delta', None)
        importer_config = request.body_as_json.get('importer_config', None)
        distributor_configs = request.body_as_json.get('distributor_configs', None)
        repo_manager = manager_factory.repo_manager()
        task_result = repo_manager.update_repo_and_plugins(repo_id, delta, importer_config,
                                                           distributor_configs)
        repo = task_result.return_value
        repo['_href'] = reverse('repo_resource', kwargs={'repo_id': repo_id})
        _convert_repo_dates_to_strings(repo)

        # Tasks are spawned if a distributor is updated, raise that as a result
        if task_result.spawned_tasks:
            raise pulp_exceptions.OperationPostponed(task_result)

        result = task_result.serialize()
        return generate_json_response_with_pulp_encoder(result)


class RepoSearch(search.SearchView):
    """
    Adds GET and POST searching for repositories.
    """
    manager = repo_query.RepoQueryManager()
    optional_fields = ['details', 'importers', 'distributors']
    response_builder = staticmethod(generate_json_response_with_pulp_encoder)

    @classmethod
    def get_results(cls, query, search_method, options, *args, **kwargs):
        """
        This overrides the base class's implementation so we can optionally include extra data.


        :param query: The criteria that should be used to search for objects
        :type  query: dict
        :param search_method: function that should be used to search
        :type  search_method: func
        :param options: additional options for including extra data
        :type  options: dict

        :return: processed results of the query
        :rtype:  list
        """
        results = list(search_method(query))
        details = options.get('details', 'false')
        importers = options.get('importers', 'false')
        distributors = options.get('distributors', 'false')
        return _process_repos(results, details, importers, distributors)


class RepoUnitSearch(search.SearchView):
    """
    Adds GET and POST searching for units within a repository.
    """

    @classmethod
    def _generate_response(cls, query, options, *args, **kwargs):
        """
        Perform the database query using the given search data, and return the resuls as a JSON
        serialized HttpReponse object.

        This overrides the base class so we can validate repo existance and to choose the search
        method depending on how many unit types we are dealing with.

        :param query: The criteria that should be used to search for objects
        :type  query: dict
        :param options: additional options for including extra data
        :type  options: dict

        :return:      The serialized search results in an HttpReponse
        :rtype:       django.http.HttpResponse
        """
        repo_id = kwargs.get('repo_id')
        repo_query_manager = manager_factory.repo_query_manager()
        repo = repo_query_manager.find_by_id(repo_id)
        if repo is None:
            raise pulp_exceptions.MissingResource(repo_id=repo_id)

        criteria = UnitAssociationCriteria.from_client_input(query)
        manager = manager_factory.repo_unit_association_query_manager()
        if criteria.type_ids is not None and len(criteria.type_ids) == 1:
            type_id = criteria.type_ids[0]
            units = manager.get_units_by_type(repo_id, type_id, criteria=criteria)
        else:
            units = manager.get_units_across_types(repo_id, criteria=criteria)
        return generate_json_response_with_pulp_encoder(units)


class RepoImportersView(View):
    """
    View for all importers of a repository.
    """

    @auth_required(authorization.READ)
    def get(self, request, repo_id):
        """
        Get all importers (only one) associated with a repository.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param repo_id: id of the requested repository
        :type  repo_id: str

        :return: Response containing a list of dicts, one for each importer of the repo
        :rtype : django.http.HttpResponse
        """

        importer_manager = manager_factory.repo_importer_manager()
        importers = importer_manager.get_importers(repo_id)
        return generate_json_response_with_pulp_encoder(importers)

    @auth_required(authorization.CREATE)
    @json_body_required
    def post(self, request, repo_id):
        """
        Associate an importer with a repository.

        This will validate that the repository exists and that there is an importer with the
        importer_type_id given. However, the importer configuration validation only checks the
        provided values against a standard set of importer configuration keys. The importer
        specific validation is called on association, so any type specific configuration will
        be validated later. This means the spawned task could fail with a validation error.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param repo_id: the repository to associate the importer with
        :type  repo_id: str

        :raises pulp_exceptions.OperationPostponed: dispatch a task
        """

        importer_type = request.body_as_json.get('importer_type_id', None)
        config = request.body_as_json.get('importer_config', None)

        # Validation occurs within the manager
        importer_manager = manager_factory.repo_importer_manager()
        importer_manager.validate_importer_config(repo_id, importer_type, config)

        task_tags = [tags.resource_tag(tags.RESOURCE_REPOSITORY_TYPE, repo_id),
                     tags.action_tag('add_importer')]
        async_result = repo_importer_manager.set_importer.apply_async_with_reservation(
            tags.RESOURCE_REPOSITORY_TYPE, repo_id, [repo_id, importer_type],
            {'repo_plugin_config': config}, tags=task_tags)
        raise pulp_exceptions.OperationPostponed(async_result)


class RepoImporterResourceView(View):
    """
    View for a single importer for a repository.
    """

    @auth_required(authorization.READ)
    def get(self, request, repo_id, importer_id):
        """
        Retrieve the importer for a repo.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param repo_id: request the importer of this repository
        :type  repo_id: str
        :param importer_id: (unused) id of the requested importer
        :type  importer_id: str

        :return: Response containing a dict reporesenting the importer of the repo
        :rtype : django.http.HttpResponse
        :raises pulp_exceptions.MissingResource: if importer_id does not match importer for repo
        """

        importer_manager = manager_factory.repo_importer_manager()
        importer = importer_manager.get_importer(repo_id)
        if importer['id'] != importer_id:
            raise pulp_exceptions.MissingResource(importer_id=importer_id)
        return generate_json_response_with_pulp_encoder(importer)

    @auth_required(authorization.DELETE)
    def delete(self, request, repo_id, importer_id):
        """
        Remove an importer from a repository.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param repo_id: The id of the repository to remove the importer from
        :type  repo_id: str
        :param importer_id: The id of the importer to remove from the given repository
        :type  importer_id: str

        :raises pulp_exceptions.MissingResource: if importer cannot be found for this repo
        :raises pulp_exceptions.OperationPostponed: to dispatch a task to delete the importer
        """

        importer_manager = manager_factory.repo_importer_manager()
        importer = importer_manager.get_importer(repo_id)
        if importer['id'] != importer_id:
            raise pulp_exceptions.MissingResource(importer_id=importer_id)

        task_tags = [tags.resource_tag(tags.RESOURCE_REPOSITORY_TYPE, repo_id),
                     tags.resource_tag(tags.RESOURCE_REPOSITORY_IMPORTER_TYPE, importer_id),
                     tags.action_tag('delete_importer')]
        async_result = repo_importer_manager.remove_importer.apply_async_with_reservation(
            tags.RESOURCE_REPOSITORY_TYPE, repo_id, [repo_id], tags=task_tags)
        raise pulp_exceptions.OperationPostponed(async_result)

    @auth_required(authorization.UPDATE)
    @json_body_required
    def put(self, request, repo_id, importer_id):
        """
        Associate an importer to a repository.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param repo_id: The id of the repository
        :type  repo_id: str
        :param importer_id: The id of the importer to associate
        :type  importer_id: str

        :raises pulp_exceptions.MissingValue: if required param importer_config is not in the body
        :raises pulp_exceptions.MissingResource: if importer does not match the repo's importer
        :raises pulp_exceptions.OperationPostponed: dispatch a task
        """

        importer_manager = manager_factory.repo_importer_manager()
        importer = importer_manager.get_importer(repo_id)
        if importer['id'] != importer_id:
            raise pulp_exceptions.MissingResource(importer_id=importer_id)

        importer_config = request.body_as_json.get('importer_config', None)

        if importer_config is None:
            raise pulp_exceptions.MissingValue(['importer_config'])

        task_tags = [tags.resource_tag(tags.RESOURCE_REPOSITORY_TYPE, repo_id),
                     tags.resource_tag(tags.RESOURCE_REPOSITORY_IMPORTER_TYPE, importer_id),
                     tags.action_tag('update_importer')]
        async_result = repo_importer_manager.update_importer_config.apply_async_with_reservation(
            tags.RESOURCE_REPOSITORY_TYPE,
            repo_id, [repo_id], {'importer_config': importer_config}, tags=task_tags)
        raise pulp_exceptions.OperationPostponed(async_result)


class RepoSyncSchedulesView(View):
    """
    View for scheduled repository syncs.
    """

    @auth_required(authorization.READ)
    def get(self, request, repo_id, importer_id):
        """
        Retrieve a list of all scheduled syncs for the given importer and repo.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param repo_id: id of the repository
        :type  repo_id: str
        :param importer_id: retrieve the scheduled syncs of this importer
        :type  importer_id: str

        :return: Response containing a list of dicts, one for each scheduled sync
        :rtype : django.http.HttpResponse
        """

        manager = manager_factory.repo_sync_schedule_manager()
        schedules = manager.list(repo_id, importer_id)
        for_display = [schedule.for_display() for schedule in schedules]
        for entry in for_display:
            entry['_href'] = reverse(
                'repo_sync_schedule_resource',
                kwargs={'repo_id': repo_id, 'importer_id': importer_id, 'schedule_id': entry['_id']}
            )

        return generate_json_response(for_display)

    @auth_required(authorization.CREATE)
    @json_body_required
    def post(self, request, repo_id, importer_id):
        """
        Create a new scheduled sync.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param repo_id: id of the repository
        :type  repo_id: str
        :param importer_id: create a new scheduled sync for this importer
        :type  importer_id: str

        :return: Response containing a serialized dict of the new  scheduled sync
        :rtype : django.http.HttpResponse
        :raises pulp_exceptions.UnsupportedValue: if there are unsupported request body params
        """

        manager = manager_factory.repo_sync_schedule_manager()
        sync_options = {'override_config': request.body_as_json.pop('override_config', {})}
        schedule = request.body_as_json.pop('schedule', None)
        failure_threshold = request.body_as_json.pop('failure_threshold', None)
        enabled = request.body_as_json.pop('enabled', True)
        if request.body_as_json:
            raise pulp_exceptions.UnsupportedValue(request.body_as_json.keys())

        scheduled_call = manager.create(repo_id, importer_id, sync_options,
                                        schedule, failure_threshold, enabled)
        display_call = scheduled_call.for_display()
        display_call['_href'] = reverse(
            'repo_sync_schedule_resource',
            kwargs={'repo_id': repo_id, 'importer_id': importer_id,
                    'schedule_id': scheduled_call['id']}
        )
        response = generate_json_response(display_call)
        return generate_redirect_response(response, display_call['_href'])


class RepoSyncScheduleResourceView(ScheduleResource):
    """
    View for a single scheduled repository sync.
    """

    def __init__(self):
        """
        Initialize RepoSyncScheduleResource.
        """

        super(RepoSyncScheduleResourceView, self).__init__()
        self.manager = manager_factory.repo_sync_schedule_manager()

    @auth_required(authorization.READ)
    def get(self, request, repo_id, importer_id, schedule_id):
        """
        Retrieve information about a scheduled sync.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param repo_id: id of the repository
        :type  repo_id: str
        :param importer_id: id of the importer
        :type  importer_id: str
        :param schedule_id: id of the requested scheduled repository sync
        :type  schedule)id: str

        :return: information about the requested scheduled sync
        :rtype: django.http.HttpResponse
        """

        self.manager.validate_importer(repo_id, importer_id)
        resource_href = reverse('repo_sync_schedule_resource',
                                kwargs={'repo_id': repo_id, 'importer_id': importer_id,
                                        'schedule_id': schedule_id})
        return self._get(schedule_id, resource_href)

    @auth_required(authorization.DELETE)
    def delete(self, request, repo_id, importer_id, schedule_id):
        """
        Remove a scheduled repository sync from the importer.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param repo_id: id of the repository
        :type  repo_id: str
        :param importer_id: remove the scheduled sync from this importer
        :type  importer_id: str
        :param schedule_id: id of the scheduled repository sync to delete
        :type  schedule)id: str

        :return: An empty response
        :rtype: django.http.HttpResponse
        :raises pulp_exceptions.MissingResource: if schedule_id/importer_id/repo_id does not exist
        """

        try:
            self.manager.delete(repo_id, importer_id, schedule_id)
        except pulp_exceptions.InvalidValue:
            raise pulp_exceptions.MissingResource(schedule_id=schedule_id)
        return generate_json_response(None)

    @auth_required(authorization.UPDATE)
    @json_body_allow_empty
    def put(self, request, repo_id, importer_id, schedule_id):
        """
        Update a scheduled repository sync.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param repo_id: id of the repository
        :type  repo_id: str
        :param importer_id: id of the importer
        :type  importer_id: str
        :param schedule_id: id of the scheduled repository sync to update
        :type  schedule)id: str

        :return: information about the updated scheduled sync
        :rtype: django.http.HttpResponse
        """

        if 'schedule' in request.body_as_json:
            request.body_as_json['iso_schedule'] = request.body_as_json.pop('schedule')
        schedule = self.manager.update(repo_id, importer_id, schedule_id, request.body_as_json)
        ret = schedule.for_display()
        ret['_href'] = reverse(
            'repo_sync_schedule_resource',
            kwargs={'repo_id': repo_id, 'importer_id': importer_id, 'schedule_id': schedule_id}
        )
        return generate_json_response(ret)


class RepoDistributorsView(View):
    """
    View for all distributors associated with a repo.
    """

    @auth_required(authorization.READ)
    def get(self, request, repo_id):
        """
        Get a list of all distributors associated with a given repository.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param repo_id: The id of the requested repository
        :type  repo_id: str

        :return: Response containing a list of dicts, one for each associated distributor
        :rtype : django.http.HttpResponse
        """

        distributor_manager = manager_factory.repo_distributor_manager()

        distributor_list = distributor_manager.get_distributors(repo_id)
        return generate_json_response_with_pulp_encoder(distributor_list)

    @auth_required(authorization.CREATE)
    @json_body_required
    def post(self, request, repo_id):
        """
        Associate a distributor with a repository.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param repo_id: The id of the repository to associate with
        :type  repo_id: str

        :return: Response containing a dict of the associated distributor
        :rtype : django.http.HttpResponse
        """

        # Validation will occur in the manager
        distributor_type = request.body_as_json.get('distributor_type_id', None)
        distributor_config = request.body_as_json.get('distributor_config', None)
        distributor_id = request.body_as_json.get('distributor_id', None)
        auto_publish = request.body_as_json.get('auto_publish', False)

        distributor_manager = manager_factory.repo_distributor_manager()
        distributor = distributor_manager.add_distributor(
            repo_id, distributor_type, distributor_config, auto_publish, distributor_id
        )
        distributor['_href'] = reverse(
            'repo_distributor_resource',
            kwargs={'repo_id': repo_id, 'distributor_id': distributor['id']}
        )
        response = generate_json_response_with_pulp_encoder(distributor)
        return generate_redirect_response(response, distributor['_href'])


class RepoDistributorsSearchView(search.SearchView):
    """
    Distributor search view.
    """

    manager = RepoDistributorManager()
    response_builder = staticmethod(generate_json_response_with_pulp_encoder)


class RepoDistributorResourceView(View):
    """
    View for a single distributor associated with a repository.
    """

    @auth_required(authorization.READ)
    def get(self, request, repo_id, distributor_id):
        """
        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param repo_id: The id of the repository the distributor is associated with
        :type  repo_id: str
        :param repo_id: The id of the requested distributor
        :type  repo_id: str

        :return: Response containing a dict of the requested distributor
        :rtype : django.http.HttpResponse
        """

        distributor_manager = manager_factory.repo_distributor_manager()
        distributor = distributor_manager.get_distributor(repo_id, distributor_id)
        return generate_json_response_with_pulp_encoder(distributor)

    @auth_required(authorization.DELETE)
    def delete(self, request, repo_id, distributor_id):
        """
        Disassociate the requested distributor.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param repo_id: The id of the repository the to disassociate from
        :type  repo_id: str
        :param repo_id: The id of the distributor to disassociate
        :type  repo_id: str

        :raises pulp_exceptions.OperationPostponed: dispatch a task
        """

        # validate resources
        manager = manager_factory.repo_distributor_manager()
        manager.get_distributor(repo_id, distributor_id)

        task_tags = [
            tags.resource_tag(tags.RESOURCE_REPOSITORY_TYPE, repo_id),
            tags.resource_tag(tags.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE, distributor_id),
            tags.action_tag('remove_distributor')
        ]
        async_result = repo_tasks.distributor_delete.apply_async_with_reservation(
            tags.RESOURCE_REPOSITORY_TYPE, repo_id, [repo_id, distributor_id],
            tags=task_tags)
        raise pulp_exceptions.OperationPostponed(async_result)

    @auth_required(authorization.UPDATE)
    @json_body_required
    def put(self, request, repo_id, distributor_id):
        """
        Used to update a repo distributor instance.

        The expected parameters are 'distributor_config', which is a dictionary containing
        configuration values accepted by the distributor type, and 'delta', which is a dictionary
        containing other configuration values for the distributor (like the auto_publish flag,
        for example). Currently, the only supported key in the delta is 'auto_publish', which
        should have a boolean value.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param repo_id: id of the repository the distributor is associated with
        :type  repo_id: str
        :param distributor_id: id of the distributor instance to update.
        :type  distributor_id: str

        :raises pulp_exceptions.MissingValue: if distributor_config is not passed
        :raises pulp_exceptions.OperationPostponed: dispatch a task
        """

        # validate
        manager = manager_factory.repo_distributor_manager()
        manager.get_distributor(repo_id, distributor_id)

        delta = request.body_as_json.get('delta', None)
        config = request.body_as_json.get('distributor_config')
        if config is None:
            raise pulp_exceptions.MissingValue(['distributor_config'])
        task_tags = [
            tags.resource_tag(tags.RESOURCE_REPOSITORY_TYPE, repo_id),
            tags.resource_tag(tags.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE, distributor_id),
            tags.action_tag('update_distributor')
        ]
        async_result = repo_tasks.distributor_update.apply_async_with_reservation(
            tags.RESOURCE_REPOSITORY_TYPE, repo_id,
            [repo_id, distributor_id, config, delta], tags=task_tags)
        raise pulp_exceptions.OperationPostponed(async_result)


class RepoPublishSchedulesView(View):
    """
    View for scheduled publishes.
    """

    @auth_required(authorization.READ)
    def get(self, request, repo_id, distributor_id):
        """
        Retrieve information about all scheduled publishes.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param repo_id: id of the repository
        :type  repo_id: str
        :param distributor_id: id of the distributor
        :type  distributor_id: str

        :return: Response containing serialized list of dicts, one for each scheduled publish
        :rtype : django.http.HttpResponse
        """

        manager = manager_factory.repo_publish_schedule_manager()
        schedules = manager.list(repo_id, distributor_id)
        for_display = [schedule.for_display() for schedule in schedules]
        for entry in for_display:
            entry['_href'] = reverse('repo_publish_schedule_resource', kwargs={
                'repo_id': repo_id, 'distributor_id': distributor_id, 'schedule_id': entry['_id']
            })
        return generate_json_response(for_display)

    @auth_required(authorization.CREATE)
    @json_body_required
    def post(self, request, repo_id, distributor_id):
        """
        Create a new scheduled publish.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param repo_id: id of the repository
        :type  repo_id: str
        :param distributor_id: id of the distributor
        :type  distributor_id: str

        :return: Response containing a dict for the new scheduled publish
        :rtype : django.http.HttpResponse
        :raises pulp_exceptions.UnsupportedValue: if unsupported fields are included in body
        """

        manager = manager_factory.repo_publish_schedule_manager()
        publish_options = {'override_config': request.body_as_json.pop('override_config', {})}
        schedule = request.body_as_json.pop('schedule', None)
        failure_threshold = request.body_as_json.pop('failure_threshold', None)
        enabled = request.body_as_json.pop('enabled', True)
        if request.body_as_json:
            raise pulp_exceptions.UnsupportedValue(request.body_as_json.keys())

        schedule = manager.create(repo_id, distributor_id, publish_options,
                                  schedule, failure_threshold, enabled)
        ret = schedule.for_display()
        ret['_href'] = reverse('repo_publish_schedule_resource', kwargs={
            'repo_id': repo_id, 'distributor_id': distributor_id, 'schedule_id': schedule.id
        })
        response = generate_json_response_with_pulp_encoder(ret)
        return generate_redirect_response(response, ret['_href'])


class RepoPublishScheduleResourceView(ScheduleResource):
    """
    View for a single scheduled publish.
    """

    def __init__(self):
        """
        Initialize RepoPublishScheduleResourceView.
        """

        super(RepoPublishScheduleResourceView, self).__init__()
        self.manager = manager_factory.repo_publish_schedule_manager()

    @auth_required(authorization.READ)
    def get(self, request, repo_id, distributor_id, schedule_id):
        """
        Retrieve information about a scheduled publish.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param repo_id: id of the repository
        :type  repo_id: str
        :param distributor_id: id of the distributor
        :type  distributor_id: str
        :param schedule_id: id of the scheduled publish to be retrieved
        :type  schedule_id: str

        :return: Response containing serialized dict for the scheduled publish
        :rtype : django.http.HttpResponse
        """

        self.manager.validate_distributor(repo_id, distributor_id)
        resource_href = reverse('repo_publish_schedule_resource', kwargs={
            'repo_id': repo_id, 'distributor_id': distributor_id, 'schedule_id': schedule_id
        })
        return self._get(schedule_id, resource_href)

    @auth_required(authorization.UPDATE)
    @json_body_allow_empty
    def put(self, request, repo_id, distributor_id, schedule_id):
        """
        Update a scheduled publish.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param repo_id: id of the repository
        :type  repo_id: str
        :param distributor_id: id of the distributor
        :type  distributor_id: str
        :param schedule_id: id of the scheduled publish to be updated
        :type  schedule_id: str

        :return: Response containing serialized dict for the scheduled publish
        :rtype : django.http.HttpResponse
        """

        updates = request.body_as_json
        if 'schedule' in updates:
            updates['iso_schedule'] = updates.pop('schedule')
        schedule = self.manager.update(repo_id, distributor_id, schedule_id, updates)
        ret = schedule.for_display()
        ret['_href'] = reverse('repo_publish_schedule_resource', kwargs={
            'repo_id': repo_id, 'distributor_id': distributor_id, 'schedule_id': schedule_id
        })
        return generate_json_response(ret)

    @auth_required(authorization.DELETE)
    def delete(self, request, repo_id, distributor_id, schedule_id):
        """
        Remove a scheduled publish.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param repo_id: id of the repository
        :type  repo_id: str
        :param distributor_id: id of the distributor
        :type  distributor_id: str
        :param schedule_id: id of the scheduled publish to be removed
        :type  schedule_id: str

        :return: An empty response
        :rtype : django.http.HttpResponse
        """

        try:
            self.manager.delete(repo_id, distributor_id, schedule_id)
        except pulp_exceptions.InvalidValue:
            raise pulp_exceptions.MissingResource(schedule_id=schedule_id)

        return generate_json_response(None)


class ContentApplicabilityRegenerationView(View):
    """
    Content applicability regeneration for updated repositories.
    """

    @auth_required(authorization.CREATE)
    @json_body_required
    def post(self, request):
        """
        Dispatch a task to regenerate content applicability data for repositories that match
        the criteria passed in the body.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest

        :raises pulp_exceptions.MissingValue: if repo_critera is not a body parameter
        :raises pulp_exceptions.InvalidValue: if repo_critera (dict) has unsupported keys,
                                              the manager will raise an InvalidValue for the
                                              specific keys. Here, we create a parent exception
                                              for repo_criteria and include the specific keys as
                                              child exceptions.
        :raises pulp_exceptions.OperationPostponed: dispatch a task
        """

        repo_criteria_body = request.body_as_json.get('repo_criteria', None)
        if repo_criteria_body is None:
            raise pulp_exceptions.MissingValue('repo_criteria')
        try:
            repo_criteria = Criteria.from_client_input(repo_criteria_body)
        except pulp_exceptions.InvalidValue, e:
            invalid_criteria = pulp_exceptions.InvalidValue('repo_criteria')
            invalid_criteria.add_child_exception(e)
            raise invalid_criteria

        regeneration_tag = tags.action_tag('content_applicability_regeneration')
        async_result = regenerate_applicability_for_repos.apply_async_with_reservation(
            tags.RESOURCE_REPOSITORY_PROFILE_APPLICABILITY_TYPE, tags.RESOURCE_ANY_ID,
            (repo_criteria.as_dict(),), tags=[regeneration_tag])
        raise pulp_exceptions.OperationPostponed(async_result)


class RepoSyncHistory(View):
    """
    View for sync history of a specified repository.
    """

    @auth_required(authorization.READ)
    def get(self, request, repo_id):
        """
        Retrieve sync history for a specified repository.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param repo_id: id of the repository
        :type  repo_id: str

        :return: Response containing a list of dicts, one for each sync event
        :rtype : django.http.HttpResponse
        :raises pulp_exceptions.InvalidValue: if limit is not an integer
        """

        sort = request.GET.get(constants.REPO_HISTORY_FILTER_SORT)
        start_date = request.GET.get(constants.REPO_HISTORY_FILTER_START_DATE)
        end_date = request.GET.get(constants.REPO_HISTORY_FILTER_END_DATE)
        limit = request.GET.get(constants.REPO_HISTORY_FILTER_LIMIT)
        if limit:
            try:
                limit = int(limit)
            except ValueError:
                raise pulp_exceptions.InvalidValue([constants.REPO_HISTORY_FILTER_LIMIT])
        if not sort:
            sort = constants.SORT_DESCENDING

        sync_manager = manager_factory.repo_sync_manager()
        # Error checking is done on these options in the sync manager before the database is queried
        entries = sync_manager.sync_history(repo_id, limit=limit, sort=sort, start_date=start_date,
                                            end_date=end_date)
        return generate_json_response_with_pulp_encoder(entries)


class RepoPublishHistory(View):
    """
    View for publish history of a specified repository.
    """

    @auth_required(authorization.READ)
    def get(self, request, repo_id, distributor_id):
        """
        Retrieve publish history for a specified distributor.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param repo_id: id of the repository
        :type  repo_id: str
        :param repo_id: retrieve the publish history of this distributor
        :type  repo_id: str

        :return: Response containing a list of dicts, one for each publish event
        :rtype : django.http.HttpResponse
        """

        sort = request.GET.get(constants.REPO_HISTORY_FILTER_SORT)
        start_date = request.GET.get(constants.REPO_HISTORY_FILTER_START_DATE)
        end_date = request.GET.get(constants.REPO_HISTORY_FILTER_END_DATE)
        limit = request.GET.get(constants.REPO_HISTORY_FILTER_LIMIT)
        if limit:
            try:
                limit = int(limit)
            except ValueError:
                raise pulp_exceptions.InvalidValue([constants.REPO_HISTORY_FILTER_LIMIT])
        if not sort:
            sort = constants.SORT_DESCENDING

        publish_manager = manager_factory.repo_publish_manager()
        entries = publish_manager.publish_history(repo_id, distributor_id, limit=limit, sort=sort,
                                                  start_date=start_date, end_date=end_date)
        return generate_json_response_with_pulp_encoder(entries)


class RepoSync(View):
    """
    View for syncing a repository.
    """

    @auth_required(authorization.EXECUTE)
    @json_body_allow_empty
    def post(self, request, repo_id):
        """
        Dispatch a task to sync a repository.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param repo_id: id of the repository to sync
        :type  repo_id: str

        :raises pulp_exceptions.OperationPostponed: dispatch a sync repo task
        """

        overrides = request.body_as_json.get('override_config', None)

        # Check for repo existence and let the missing resource bubble up
        manager_factory.repo_query_manager().get_repository(repo_id)
        async_result = repo_tasks.sync_with_auto_publish(repo_id, overrides)
        raise pulp_exceptions.OperationPostponed(async_result)


class RepoPublish(View):
    """
    View for publishing a repository.
    """

    @auth_required(authorization.EXECUTE)
    @json_body_required
    def post(self, request, repo_id):
        """
        Dispatch a task to publish a repository.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param repo_id: id of the repository to publish
        :type  repo_id: str

        :raises pulp_exceptions.MissingValue: if required param id is not passed
        :raises pulp_exceptions.OperationPostponed: dispatch a publish repo task
        """

        # validation
        manager = manager_factory.repo_query_manager()
        manager.get_repository(repo_id)

        distributor_id = request.body_as_json.get('id', None)
        if distributor_id is None:
            raise pulp_exceptions.MissingValue('id')
        overrides = request.body_as_json.get('override_config', None)
        async_result = repo_tasks.publish(repo_id, distributor_id, overrides)
        raise pulp_exceptions.OperationPostponed(async_result)


class RepoAssociate(View):
    """
    View to copy units between repositories.
    """

    @auth_required(authorization.UPDATE)
    @json_body_required
    def post(self, request, dest_repo_id):
        """
        Associate units matching the criteria into the given repository

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param dest_repo_id: id of the repository content will be copied to
        :type  dest_repo_id: str

        :raises pulp_exceptions.MissingValue: if required param source_repo_id is not passed
        :raises pulp_exceptions.InvalidValue: if source_repo_id is not found or if criteria
                                              params cannot be parsed
        :raises pulp_exceptions.OperationPostponed: dispatch a publish repo task
        """

        # Validate existence of dest_repo_id, can raise a MissingResource
        repo_query_manager = manager_factory.repo_query_manager()
        repo_query_manager.get_repository(dest_repo_id)

        criteria_body = request.body_as_json.get('criteria', None)
        overrides = request.body_as_json.get('override_config', None)
        source_repo_id = request.body_as_json.get('source_repo_id', None)
        if source_repo_id is None:
            raise pulp_exceptions.MissingValue(['source_repo_id'])

        # Catch MissingResource because this is body data, raise 400 rather than 404
        try:
            repo_query_manager.get_repository(source_repo_id)
        except pulp_exceptions.MissingResource:
            raise pulp_exceptions.InvalidValue(['source_repo_id'])

        if criteria_body:
            try:
                criteria = UnitAssociationCriteria.from_client_input(criteria_body)
            except pulp_exceptions.InvalidValue, e:
                invalid_criteria = pulp_exceptions.InvalidValue('criteria')
                invalid_criteria.add_child_exception(e)
                raise invalid_criteria
        else:
            criteria = None

        task_tags = [tags.resource_tag(tags.RESOURCE_REPOSITORY_TYPE, dest_repo_id),
                     tags.resource_tag(tags.RESOURCE_REPOSITORY_TYPE, source_repo_id),
                     tags.action_tag('associate')]
        async_result = associate_from_repo.apply_async_with_reservation(
            tags.RESOURCE_REPOSITORY_TYPE, dest_repo_id, [source_repo_id, dest_repo_id],
            {'criteria': criteria, 'import_config_override': overrides}, tags=task_tags)
        raise pulp_exceptions.OperationPostponed(async_result)


class RepoUnassociate(View):
    """
    View to unassociate a unit from a repository.
    """

    @auth_required(authorization.UPDATE)
    @json_body_allow_empty
    def post(self, request, repo_id):
        """
        Unassociate units that match the criteria from the given repository.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param repo_id: id of the repository to unassociate content from
        :type  repo_id: str

        :raises pulp_exceptions.InvalidValue: if criteria params cannot be parsed
        :raises pulp_exceptions.OperationPostponed: dispatch a unassociate_by_criteria task
        """

        criteria_body = request.body_as_json.get('criteria')
        if criteria_body:
            try:
                criteria = UnitAssociationCriteria.from_client_input(criteria_body)
            except pulp_exceptions.InvalidValue, e:
                invalid_criteria = pulp_exceptions.InvalidValue('criteria')
                invalid_criteria.add_child_exception(e)
                raise invalid_criteria
        else:
            criteria = None

        task_tags = [tags.resource_tag(tags.RESOURCE_REPOSITORY_TYPE, repo_id),
                     tags.action_tag('unassociate')]
        async_result = unassociate_by_criteria.apply_async_with_reservation(
            tags.RESOURCE_REPOSITORY_TYPE, repo_id,
            [repo_id, criteria], tags=task_tags)
        raise pulp_exceptions.OperationPostponed(async_result)


class RepoImportUpload(View):
    """
    View to import units into a repository.
    """

    @auth_required(authorization.UPDATE)
    @json_body_required
    def post(self, request, repo_id):
        """
        Import an uploaded unit into the given repository.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param repo_id: The id of the repository the upload should be imported into
        :type  repo_id: str

        :raises pulp_exceptions.OperationPostponed: dispatch a importy_uploaded_unit task
        """

        try:
            upload_id = request.body_as_json['upload_id']
            unit_type_id = request.body_as_json['unit_type_id']
            unit_key = request.body_as_json['unit_key']
        except KeyError, e:
            raise pulp_exceptions.MissingValue(e.args[0])

        unit_metadata = request.body_as_json.pop('unit_metadata', None)
        override_config = request.body_as_json.pop('override_config', None)
        task_tags = [tags.resource_tag(tags.RESOURCE_REPOSITORY_TYPE, repo_id),
                     tags.action_tag('import_upload')]
        async_result = import_uploaded_unit.apply_async_with_reservation(
            tags.RESOURCE_REPOSITORY_TYPE, repo_id,
            [repo_id, unit_type_id, unit_key, unit_metadata, upload_id, override_config],
            tags=task_tags)
        raise pulp_exceptions.OperationPostponed(async_result)
