from django.core.urlresolvers import reverse
from django.views.generic import View

from pulp.common import tags
from pulp.common.plugins import distributor_constants
from pulp.server import exceptions as pulp_exceptions
from pulp.server.auth import authorization
from pulp.server.db.model.criteria import Criteria
from pulp.server.db.model.repo_group import RepoGroup as RepoGroupModel
from pulp.server.managers import factory as managers_factory
from pulp.server.managers.repo.group import query as repo_group_query
from pulp.server.managers.repo.group.publish import publish as repo_group_publish
from pulp.server.webservices.controllers.decorators import auth_required
from pulp.server.webservices.views import search
from pulp.server.webservices.views.util import (
    generate_json_response, generate_json_response_with_pulp_encoder, generate_redirect_response,
    json_body_allow_empty, json_body_required
)


def _add_group_link(repo_group):
    repo_group['_href'] = reverse('repo_group_resource', kwargs={'repo_group_id': repo_group['id']})
    return repo_group


class RepoGroupsView(View):
    """
    Views for all repo groups.
    """

    @auth_required(authorization.READ)
    def get(self, request):
        """
        Return a serialized response containing a list of repo groups.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest

        :return: Response containing a serialized list of dicts, one for each repo group
        :rtype: django.http.HttpResponse
        """

        collection = RepoGroupModel.get_collection()
        cursor = collection.find({})
        groups = [_add_group_link(group) for group in cursor]
        return generate_json_response_with_pulp_encoder(groups)

    @auth_required(authorization.CREATE)
    @json_body_required
    def post(self, request):
        """
        Create a repo group from the data passed in the body.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest

        :return: Response containing a serialized dict of the new repo group
        :rtype: django.http.HttpResponse
        :raises pulp_exceptions.MissingValue: if required values are not passed into the body
        :raises pulp_exceptions.InvalidValue: if invalid values are passed into the body
        """
        group_data = request.body_as_json
        group_id = group_data.pop('id', None)
        if group_id is None:
            raise pulp_exceptions.MissingValue(['id'])
        display_name = group_data.pop('display_name', None)
        description = group_data.pop('description', None)
        repo_ids = group_data.pop('repo_ids', None)
        notes = group_data.pop('notes', None)
        distributors = group_data.pop('distributors', None)
        if group_data:
            raise pulp_exceptions.InvalidValue(group_data.keys())
        # Create the repo group
        manager = managers_factory.repo_group_manager()
        args = [group_id, display_name, description, repo_ids, notes]
        kwargs = {'distributor_list': distributors}
        group = manager.create_and_configure_repo_group(*args, **kwargs)
        group = _add_group_link(group)
        group['distributors'] = distributors or []
        response = generate_json_response_with_pulp_encoder(group)
        return generate_redirect_response(response, group['_href'])


class RepoGroupResourceView(View):
    """
    View for a single repo group.
    """

    @auth_required(authorization.READ)
    def get(self, request, repo_group_id):
        """
        Retrieve the specified repo group.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param repo_group_id: id of repo group to return
        :type  repo_group_id: str

        :return: Response containing serialized dict of the specified group
        :rtype: django.http.HttpResponse
        :raises pulp_exceptions.MissingResource: if repo_group_id is not found
        """
        collection = RepoGroupModel.get_collection()
        group = collection.find_one({'id': repo_group_id})
        if group is None:
            raise pulp_exceptions.MissingResource(repo_group=repo_group_id)
        group = _add_group_link(group)
        return generate_json_response_with_pulp_encoder(group)

    @auth_required(authorization.DELETE)
    def delete(self, request, repo_group_id):
        """
        Delete the specified repo group.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param repo_group_id: id of repo group to delete
        :type  repo_group_id: str

        :return: An empty response
        :rtype: django.http.HttpResponse
        """
        manager = managers_factory.repo_group_manager()
        manager.delete_repo_group(repo_group_id)
        return generate_json_response(None)

    @auth_required(authorization.UPDATE)
    @json_body_allow_empty
    def put(self, request, repo_group_id):
        """
        Update the specified repo group with body data.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param repo_group_id: id of repo group to update
        :type  repo_group_id: str

        :return: Response containing a serialized dict of the modified repo group
        :rtype: django.http.HttpResponse
        """
        update_data = request.body_as_json
        manager = managers_factory.repo_group_manager()
        group = manager.update_repo_group(repo_group_id, **update_data)
        group = _add_group_link(group)
        return generate_json_response_with_pulp_encoder(group)


class RepoGroupSearch(search.SearchView):
    serializer = staticmethod(_add_group_link)
    manager = repo_group_query.RepoGroupQueryManager()
    response_builder = staticmethod(generate_json_response_with_pulp_encoder)


class RepoGroupAssociateView(View):
    """
    View to associate repositories with repo groups.
    """

    @auth_required(authorization.EXECUTE)
    @json_body_allow_empty
    def post(self, request, repo_group_id):
        """
        Associate repos that match criteria specified in the body to the specified repo group.
        Call is idempotent.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param repo_group_id: matching repos are associated with this repo group
        :type  repo_group_id: str

        :return: Response containing a serialized list of associated repository names
        :rtype: django.http.HttpResponse
        """
        criteria = Criteria.from_client_input(request.body_as_json.get('criteria', {}))
        manager = managers_factory.repo_group_manager()
        manager.associate(repo_group_id, criteria)
        collection = RepoGroupModel.get_collection()
        group = collection.find_one({'id': repo_group_id})
        return generate_json_response(group['repo_ids'])


class RepoGroupUnassociateView(View):
    """
    View to unassociate repositories with repo groups.
    """

    @auth_required(authorization.EXECUTE)
    @json_body_allow_empty
    def post(self, request, repo_group_id):
        """
        Unassociate repos that match criteria specified in the body to the specified repo group.
        Call is idempotent.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param repo_group_id: matching repos are unassociated with this repo group
        :type  repo_group_id: str

        :return: Response containing a serialized list of unassociated repository names
        :rtype: django.http.HttpResponse
        """
        criteria = Criteria.from_client_input(request.body_as_json.get('criteria', {}))
        manager = managers_factory.repo_group_manager()
        manager.unassociate(repo_group_id, criteria)
        collection = RepoGroupModel.get_collection()
        group = collection.find_one({'id': repo_group_id})
        return generate_json_response(group['repo_ids'])


class RepoGroupDistributorsView(View):
    """
    Views for all distributors of the given repo group.
    """

    @auth_required(authorization.READ)
    def get(self, request, repo_group_id):
        """
        Get a list of all distributors associated with the given repo_group.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param repo_group_id: return distributors associated with this repo group
        :type  repo_group_id: str

        :return: response containing a serialized list of dicts, one for each associated distributor
        :rtype: django.http.HttpResponse
        """
        distributor_manager = managers_factory.repo_group_distributor_manager()
        distributor_list = distributor_manager.find_distributors(repo_group_id)
        for distributor in distributor_list:
            distributor['_href'] = reverse('repo_group_distributor_resource',
                                           kwargs={'repo_group_id': repo_group_id,
                                                   'distributor_id': distributor['id']})
        return generate_json_response_with_pulp_encoder(distributor_list)

    @auth_required(authorization.CREATE)
    @json_body_required
    def post(self, request, repo_group_id):
        """
        Asssociate a distributor with a repo group.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param repo_group_id: matching distributors will be associated with this repo group
        :type  repo_group_id: str

        :return: response containing a serialized dict of the distributor association
        :rtype: django.http.HttpResponse
        """
        # Params (validation will occur in the manager)
        params = request.body_as_json
        distributor_type_id = params.get(distributor_constants.DISTRIBUTOR_TYPE_ID_KEY, None)
        distributor_config = params.get(distributor_constants.DISTRIBUTOR_CONFIG_KEY, None)
        distributor_id = params.get(distributor_constants.DISTRIBUTOR_ID_KEY, None)
        distributor_manager = managers_factory.repo_group_distributor_manager()
        created = distributor_manager.add_distributor(repo_group_id, distributor_type_id,
                                                      distributor_config, distributor_id)
        created['_href'] = reverse('repo_group_distributor_resource',
                                   kwargs={'repo_group_id': repo_group_id,
                                           'distributor_id': created['id']})
        response = generate_json_response_with_pulp_encoder(created)
        return generate_redirect_response(response, created['_href'])


class RepoGroupDistributorResourceView(View):
    """
    View for a single repo group distributor association.
    """

    @auth_required(authorization.READ)
    def get(self, request, repo_group_id, distributor_id):
        """
        Get information about a single repo group distributor association.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param repo_group_id: repo group the distributor is associated with
        :type  repo_group_id: str
        :param distributor_id: distributor to get
        :type  distributor_id: str

        :return: response containing a serialized dict of the requested distributor
        :rtype: django.http.HttpResponse
        """
        distributor_manager = managers_factory.repo_group_distributor_manager()
        dist = distributor_manager.get_distributor(repo_group_id, distributor_id)
        dist['_href'] = reverse(
            'repo_group_distributor_resource',
            kwargs={'repo_group_id': repo_group_id, 'distributor_id': distributor_id}
        )
        return generate_json_response_with_pulp_encoder(dist)

    @auth_required(authorization.DELETE)
    @json_body_allow_empty
    def delete(self, request, repo_group_id, distributor_id):
        """
        Disassociate a distributor from a repository group.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param repo_group_id: repo group the distributor is associated with
        :type  repo_group_id: str
        :param distributor_id: distributor to disassociate
        :type  distributor_id: str

        :return: An empty response
        :rtype: django.http.HttpResponse
        """
        params = request.body_as_json
        force = params.get('force', False)
        distributor_manager = managers_factory.repo_group_distributor_manager()
        distributor_manager.remove_distributor(repo_group_id, distributor_id, force=force)
        return generate_json_response(None)

    @auth_required(authorization.UPDATE)
    @json_body_required
    def put(self, request, repo_group_id, distributor_id):
        """
        Change information about a single repo group distributor association.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param repo_group_id: repo group the distributor is associated with
        :type  repo_group_id: str
        :param distributor_id: distributor to update
        :type  distributor_id: str

        :return: response containing a serialized dict of the modified distributor association
        :rtype: django.http.HttpResponse
        :raises pulp_exceptions.MissingValue: if param 'distributor_config' is not in the body
        """
        params = request.body_as_json
        distributor_config = params.get('distributor_config', None)
        if distributor_config is None:
            raise pulp_exceptions.MissingValue(['distributor_config'])
        distributor_manager = managers_factory.repo_group_distributor_manager()
        result = distributor_manager.update_distributor_config(repo_group_id, distributor_id,
                                                               distributor_config)
        result['_href'] = reverse(
            'repo_group_distributor_resource',
            kwargs={'repo_group_id': repo_group_id, 'distributor_id': distributor_id}
        )
        return generate_json_response_with_pulp_encoder(result)


class RepoGroupPublishView(View):
    """
    View to trigger the publish of a repo group.
    """

    @auth_required(authorization.EXECUTE)
    @json_body_required
    def post(self, request, repo_group_id):
        """
        Dispatch a task to publish content from the repo group using the distributor specified by
        the params.

        :param request: WSGI request object
        :type  request: django.core.handlers.wsgi.WSGIRequest
        :param repo_group_id: repo group to publish
        :type  repo_group_id: str

        :raises pulp_exceptions.MissingValue if 'id' is not passed in the body
        :raises pulp_exceptions.OperationPosponed: dispatch a task
        """
        params = request.body_as_json
        distributor_id = params.get('id', None)
        overrides = params.get('override_config', None)
        if distributor_id is None:
            raise pulp_exceptions.MissingValue(['id'])
        # If a repo group does not exist, get_group raises a MissingResource exception
        manager = managers_factory.repo_group_query_manager()
        manager.get_group(repo_group_id)
        task_tags = [
            tags.resource_tag(tags.RESOURCE_REPOSITORY_GROUP_TYPE, repo_group_id),
            tags.resource_tag(tags.RESOURCE_REPOSITORY_GROUP_DISTRIBUTOR_TYPE, distributor_id),
            tags.action_tag('publish')
        ]
        async_result = repo_group_publish.apply_async_with_reservation(
            tags.RESOURCE_REPOSITORY_GROUP_TYPE,
            repo_group_id,
            args=[repo_group_id, distributor_id],
            kwargs={'publish_config_override': overrides},
            tags=task_tags
        )
        raise pulp_exceptions.OperationPostponed(async_result)
