from django.core.urlresolvers import reverse
from django.http import HttpResponseBadRequest
from django.views.generic import View

from pulp.server import exceptions as pulp_exceptions
from pulp.server.auth import authorization
from pulp.server.db.model.consumer import ConsumerGroup
from pulp.server.db.model.criteria import Criteria
from pulp.server.managers import factory
from pulp.server.managers.consumer.group.cud import bind, unbind
from pulp.server.managers.consumer.group import query
from pulp.server.webservices.controllers.decorators import auth_required
from pulp.server.webservices.views import search
from pulp.server.webservices.views.util import (generate_json_response,
                                                generate_json_response_with_pulp_encoder,
                                                generate_redirect_response,
                                                json_body_allow_empty,
                                                json_body_required)


def serialize(group):
    """
    Creates an href to the consumer group and adds it to the consumer group.

    :param group: Cosumer group to serialize
    :type  group: dict
    """
    group['_href'] = reverse(
        'consumer_group_resource',
        kwargs={'consumer_group_id': group['id']}
    )
    return group


class ConsumerGroupView(View):
    """
    Views for consumer groups.
    """

    @auth_required(authorization.READ)
    def get(self, request):
        """
        List the available consumer groups.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :return: Response containing a list of consumer groups
        :rtype: django.http.HttpResponse
        """
        collection = ConsumerGroup.get_collection()
        cursor = collection.find({})
        groups = [serialize(group) for group in cursor]
        return generate_json_response_with_pulp_encoder(groups)

    @auth_required(authorization.CREATE)
    @json_body_required
    def post(self, request):
        """
        Create a consumer group and return a serialized object containing just created group.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :return: Response containing the consumer group
        :rtype: django.http.HttpResponse
        :raises: MissingValue if group ID is not provided
        :raises: InvalidValue if some parameters are invalid
        """
        params = request.body_as_json
        group_id = params.pop('id', None)
        if group_id is None:
            raise pulp_exceptions.MissingValue(['id'])
        display_name = params.pop('display_name', None)
        description = params.pop('description', None)
        consumer_ids = params.pop('consumer_ids', None)
        notes = params.pop('notes', None)
        if params:
            raise pulp_exceptions.InvalidValue(params.keys())
        manager = factory.consumer_group_manager()
        group = manager.create_consumer_group(group_id, display_name, description, consumer_ids,
                                              notes)
        link = {"_href": reverse('consumer_group_resource',
                kwargs={'consumer_group_id': group['id']})}
        group.update(link)
        response = generate_json_response_with_pulp_encoder(group)
        response_redirect = generate_redirect_response(response, link['_href'])
        return response_redirect


class ConsumerGroupResourceView(View):
    """
    Views for a specific consumer group.
    """

    @auth_required(authorization.READ)
    def get(self, request, consumer_group_id):
        """
        Return a serialized object representing the requested group.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param consumer_group_id: id for the requested group
        :type consumer_group_id: str
        :return: Response containing data for the requested group
        :rtype: django.http.HttpResponse
        :raises: MissingResource if group ID does not exist
        """
        collection = ConsumerGroup.get_collection()
        group = collection.find_one({'id': consumer_group_id})
        if group is None:
            raise pulp_exceptions.MissingResource(consumer_group=consumer_group_id)
        return generate_json_response_with_pulp_encoder(serialize(group))

    @auth_required(authorization.DELETE)
    def delete(self, request, consumer_group_id):
        """
        Delete a specified consumer group.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param consumer_group_id: id for the requested group
        :type consumer_group_id: str
        :return: An empty response
        :rtype: django.http.HttpResponse
        """
        manager = factory.consumer_group_manager()
        result = manager.delete_consumer_group(consumer_group_id)
        return generate_json_response(result)

    @auth_required(authorization.UPDATE)
    @json_body_allow_empty
    def put(self, request, consumer_group_id):
        """
        Update a specified consumer group.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param consumer_group_id: id for the requested group
        :type consumer_group_id: str
        :return: Response representing the updated group
        :rtype: django.http.HttpResponse
        """
        update_data = request.body_as_json
        manager = factory.consumer_group_manager()
        group = manager.update_consumer_group(consumer_group_id, **update_data)
        return generate_json_response_with_pulp_encoder(serialize(group))


class ConsumerGroupSearchView(search.SearchView):
    """
    This view provides GET and POST searching on Consumer Groups.
    """
    response_builder = staticmethod(generate_json_response_with_pulp_encoder)
    manager = query.ConsumerGroupQueryManager()
    serializer = staticmethod(serialize)


class ConsumerGroupAssociateActionView(View):
    """
    Views for consumer association to the group.
    """

    @auth_required(authorization.EXECUTE)
    @json_body_allow_empty
    def post(self, request, consumer_group_id):
        """
        Associate a consumer to the group.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param consumer_group_id: id for the requested group
        :type consumer_group_id: str
        :return: Response containing consumers bound to the group
        :rtype: django.http.HttpResponse
        """
        params = request.body_as_json
        criteria = Criteria.from_client_input(params.get('criteria', {}))
        manager = factory.consumer_group_manager()
        manager.associate(consumer_group_id, criteria)
        query_manager = factory.consumer_group_query_manager()
        group = query_manager.get_group(consumer_group_id)
        return generate_json_response_with_pulp_encoder(group['consumer_ids'])


class ConsumerGroupUnassociateActionView(View):
    """
    Views for consumer unassociation from the group.
    """

    @auth_required(authorization.EXECUTE)
    @json_body_allow_empty
    def post(self, request, consumer_group_id):
        """
        Unassociate a consumer from the group.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param consumer_group_id: id for the requested group
        :type consumer_group_id: str
        :return: Response containing consumers bound to the group
        :rtype: django.http.HttpResponse
        """
        params = request.body_as_json
        criteria = Criteria.from_client_input(params.get('criteria', {}))
        manager = factory.consumer_group_manager()
        manager.unassociate(consumer_group_id, criteria)
        query_manager = factory.consumer_group_query_manager()
        group = query_manager.get_group(consumer_group_id)
        return generate_json_response_with_pulp_encoder(group['consumer_ids'])


class ConsumerGroupContentActionView(View):
    """
    Views for content manipulation on consumer group.
    """

    @auth_required(authorization.CREATE)
    @json_body_allow_empty
    def post(self, request, consumer_group_id, action):
        """
        Install/update/uninstall content unit/s on each consumer in the group.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param consumer_group_id: A consumer group ID.
        :type consumer_group_id: str
        :param action: type of action to perform
        :type action: str
        """
        method = getattr(self, action, None)
        if method:
            return method(request, consumer_group_id)
        else:
            return HttpResponseBadRequest('bad request')

    def install(self, request, consumer_group_id):
        """
        Install content (units) on the consumers in a consumer group.

        Expected body: {units:[], options:<dict>}
        where unit is: {type_id:<str>, unit_key={}} and the
        options is a dict of install options.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param consumer_group_id: A consumer group ID.
        :type consumer_group_id: str
        :raises: OperationPostponed when an async operation is performed
        """
        body = request.body_as_json
        units = body.get('units')
        options = body.get('options')
        task = factory.consumer_group_manager().install_content(consumer_group_id,
                                                                units, options)
        raise pulp_exceptions.OperationPostponed(task)

    def update(self, request, consumer_group_id):
        """
        Update content (units) on the consumer in a consumer group.

        Expected body: {units:[], options:<dict>}
        where unit is: {type_id:<str>, unit_key={}} and the
        options is a dict of update options.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param consumer_group_id: A consumer group ID.
        :type consumer_group_id: str
        :raises: OperationPostponed when an async operation is performed
        """
        body = request.body_as_json
        units = body.get('units')
        options = body.get('options')
        task = factory.consumer_group_manager().update_content(consumer_group_id,
                                                               units, options)
        raise pulp_exceptions.OperationPostponed(task)

    def uninstall(self, request, consumer_group_id):
        """
        Uninstall content (units) from the consumers in a consumer group.

        Expected body: {units:[], options:<dict>}
        where unit is: {type_id:<str>, unit_key={}} and the
        options is a dict of uninstall options.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param consumer_group_id: A consumer group ID.
        :type consumer_group_id: str
        :raises: OperationPostponed when an async operation is performed
        """
        body = request.body_as_json
        units = body.get('units')
        options = body.get('options')
        task = factory.consumer_group_manager().uninstall_content(consumer_group_id,
                                                                  units, options)
        raise pulp_exceptions.OperationPostponed(task)


class ConsumerGroupBindingsView(View):
    """
    Views for repository binding to the group.
    """

    @auth_required(authorization.CREATE)
    @json_body_required
    def post(self, request, consumer_group_id):
        """
        Create a bind association between the consumers belonging to the given
        consumer group by id included in the URL path and a repo-distributor
        specified in the POST body: {repo_id:<str>, distributor_id:<str>}.
        Designed to be idempotent so only MissingResource is expected to
        be raised by manager.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param consumer_group_id: The consumer group ID to bind.
        :type consumer_group_id: str
        :raises: MissingResource if group id does not exist
        :raises: InvalidValue some parameters are invalid
        :raises: OperationPostponed when an async operation is performed
        """
        params = request.body_as_json
        repo_id = params.get('repo_id')
        distributor_id = params.get('distributor_id')
        binding_config = params.get('binding_config', None)
        options = params.get('options', {})
        notify_agent = params.get('notify_agent', True)
        missing_resources = verify_group_resources(consumer_group_id, repo_id, distributor_id)
        if missing_resources:
            if 'group_id' in missing_resources:
                raise pulp_exceptions.MissingResource(**missing_resources)
            else:
                raise pulp_exceptions.InvalidValue(list(missing_resources))
        bind_args_tuple = (consumer_group_id, repo_id, distributor_id, notify_agent,
                           binding_config, options)
        async_task = bind.apply_async(bind_args_tuple)
        raise pulp_exceptions.OperationPostponed(async_task)


class ConsumerGroupBindingView(View):
    """
    Represents a specific consumer group binding.
    """

    @auth_required(authorization.DELETE)
    def delete(self, request, consumer_group_id, repo_id, distributor_id):
        """
        Delete a bind association between the consumers belonging to the specified
        consumer group and repo-distributor. Designed to be idempotent.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param consumer_group_id: A consumer group ID.
        :type consumer_group_id: str
        :param repo_id: A repo ID.
        :type repo_id: str
        :param distributor_id: A distributor ID.
        :type distributor_id: str
        :raises: MissingResource if repo, distributor, group id is missing
        :raises: OperationPostponed when an async operation is performed
        """
        missing_resources = verify_group_resources(consumer_group_id, repo_id, distributor_id)
        if missing_resources:
            raise pulp_exceptions.MissingResource(**missing_resources)
        unbind_args_tuple = (consumer_group_id, repo_id, distributor_id, {})
        async_task = unbind.apply_async(unbind_args_tuple)
        raise pulp_exceptions.OperationPostponed(async_task)


def verify_group_resources(group_id, repo_id, distributor_id):
    """
    Confirm the group, repository, and distributor exist.

    :param group_id: The consumer group id to verify the existence of
    :type group_id: str
    :param repo_id: The repository id to confirm the existence of
    :type repo_id: str
    :param distributor_id: The distributor id to confirm the existence of on the repository
    :type distributor_id: str
    :return: A dictionary of the missing resources
    :rtype: dict
    """
    missing_resources = {}
    group_manager = factory.consumer_group_query_manager()
    repo_manager = factory.repo_query_manager()
    distributor_manager = factory.repo_distributor_manager()
    try:
        group_manager.get_group(group_id)
    except pulp_exceptions.MissingResource:
        missing_resources['group_id'] = group_id
    repo = repo_manager.find_by_id(repo_id)
    if repo is None:
        missing_resources['repo_id'] = repo_id
    try:
        distributor_manager.get_distributor(repo_id, distributor_id)
    except pulp_exceptions.MissingResource:
        missing_resources['distributor_id'] = distributor_id
    return missing_resources
