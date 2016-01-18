from django.core.urlresolvers import reverse
from django.views.generic import View

from pulp.server import exceptions as pulp_exceptions
from pulp.server.auth import authorization
from pulp.server.controllers import user as user_controller
from pulp.server.managers import factory
from pulp.server.webservices.views.decorators import auth_required
from pulp.server.webservices.views.util import (generate_json_response,
                                                generate_json_response_with_pulp_encoder,
                                                generate_redirect_response,
                                                parse_json_body)


class RolesView(View):
    """
    Views for roles.
    """

    @auth_required(authorization.READ)
    def get(self, request):
        """
        List all roles.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest

        :return: Response containing a list of roles
        :rtype: django.http.HttpResponse
        """
        role_query_manager = factory.role_query_manager()
        permissions_manager = factory.permission_manager()
        roles = role_query_manager.find_all()
        for role in roles:
            users = [u.login for u in user_controller.find_users_belonging_to_role(role['id'])]
            role['users'] = users

            resource_permission = {}
            # isolate schema change
            if role['permissions']:
                for item in role['permissions']:
                    resource = item['resource']
                    operations = item.get('permission', [])
                    resource_permission[resource] = [permissions_manager.operation_value_to_name(o)
                                                     for o in operations]

            role['permissions'] = resource_permission

            link = {'_href': reverse('role_resource',
                    kwargs={'role_id': role['id']})}
            role.update(link)
        return generate_json_response_with_pulp_encoder(roles)

    @auth_required(authorization.CREATE)
    @parse_json_body(json_type=dict)
    def post(self, request):
        """
        Create a new role.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest

        :return: Response containing the role
        :rtype: django.http.HttpResponse
        """
        role_data = request.body_as_json
        role_id = role_data.get('role_id', None)
        display_name = role_data.get('display_name', None)
        description = role_data.get('description', None)
        manager = factory.role_manager()
        role = manager.create_role(role_id, display_name, description)
        link = {'_href': reverse('role_resource',
                kwargs={'role_id': role['id']})}
        role.update(link)
        response = generate_json_response_with_pulp_encoder(role)
        redirect_response = generate_redirect_response(response, link['_href'])
        return redirect_response


class RoleResourceView(View):
    """
    Views for a single role.
    """

    @auth_required(authorization.READ)
    def get(self, request, role_id):
        """
        Retrieve a specific role.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param role_id: id for the requested role
        :type role_id: str

        :return: Response containing the role
        :rtype: django.http.HttpResponse
        :raises: MissingResource if role ID does not exist
        """
        role = factory.role_query_manager().find_by_id(role_id)
        if role is None:
            raise pulp_exceptions.MissingResource(role_id)
        role['users'] = [u.login for u in user_controller.find_users_belonging_to_role(role['id'])]
        permissions_manager = factory.permission_manager()
        # isolate schema change
        resource_permission = {}
        for item in role['permissions']:
            resource = item['resource']
            operations = item.get('permission', [])
            resource_permission[resource] = [permissions_manager.operation_value_to_name(o)
                                             for o in operations]
        role['permissions'] = resource_permission

        link = {'_href': reverse('role_resource',
                kwargs={'role_id': role['id']})}
        role.update(link)
        return generate_json_response_with_pulp_encoder(role)

    @auth_required(authorization.DELETE)
    def delete(self, request, role_id):
        """
        Delete a  role.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param role_id: id for the requested role
        :type role_id: str

        :return: An empty response
        :rtype: django.http.HttpResponse
        """
        manager = factory.role_manager()
        result = manager.delete_role(role_id)
        return generate_json_response(result)

    @auth_required(authorization.UPDATE)
    @parse_json_body(json_type=dict)
    def put(self, request, role_id):
        """
        Update a specific role.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param role_id: id for the requested role
        :type role_id: str

        :return: Response containing the role
        :rtype: django.http.HttpResponse
        """
        role_data = request.body_as_json
        delta = role_data.get('delta', None)
        manager = factory.role_manager()
        role = manager.update_role(role_id, delta)
        link = {'_href': reverse('role_resource',
                kwargs={'role_id': role['id']})}
        role.update(link)
        return generate_json_response_with_pulp_encoder(role)


class RoleUsersView(View):
    """
    Views for user membership within a role
    """

    @auth_required(authorization.READ)
    def get(self, request, role_id):
        """
        List Users belonging to a role.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param role_id: id for the requested role
        :type role_id: str

        :return: Response containing the users
        :rtype: django.http.HttpResponse
        """
        role_users = user_controller.find_users_belonging_to_role(role_id)
        return generate_json_response_with_pulp_encoder(role_users)

    @auth_required(authorization.UPDATE)
    @parse_json_body(json_type=dict)
    def post(self, request, role_id):
        """
        Add user to a role.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param role_id: id for the requested role
        :type role_id: str

        :return: An empty response
        :rtype: django.http.HttpResponse
        :raises: InvalidValue some parameters are invalid
        """
        params = request.body_as_json
        login = params.get('login', None)
        if login is None:
            raise pulp_exceptions.InvalidValue(login)

        role_manager = factory.role_manager()
        add_user = role_manager.add_user_to_role(role_id, login)
        return generate_json_response(add_user)


class RoleUserView(View):
    """
    View for specific user membership within a role.
    """

    @auth_required(authorization.DELETE)
    def delete(self, request, role_id, login):
        """
        Remove user from a role.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param role_id: id for the requested role
        :type role_id: str
        :param login: id for the requested user
        :type login: str

        :return: An empty response
        :rtype: django.http.HttpResponse
        """
        role_manager = factory.role_manager()
        remove_user = role_manager.remove_user_from_role(role_id, login)
        return generate_json_response(remove_user)
