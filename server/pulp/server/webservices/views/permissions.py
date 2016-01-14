from django.views.generic import View

from pulp.server import exceptions as pulp_exceptions
from pulp.server.auth import authorization
from pulp.server.managers import factory
from pulp.server.webservices.views.decorators import auth_required
from pulp.server.webservices.views.util import (generate_json_response,
                                                generate_json_response_with_pulp_encoder,
                                                parse_json_body)


class PermissionView(View):
    """
    Views for permissions retrieval.
    """

    @auth_required(authorization.READ)
    def get(self, request):
        """
        Retrieve permissions for all resources or for a particular resource.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest

        :return: Response containing a list of permissions for resource/s
        :rtype: django.http.HttpResponse
        """
        query_params = request.GET
        resource = query_params.get('resource', None)

        permissions = []
        if resource is None:
            permissions = factory.permission_query_manager().find_all()
        else:
            permission = factory.permission_query_manager().find_by_resource(resource)
            if permission is not None:
                permissions = [permission]

        for permission in permissions:
            # Isolate the database schema change to behind the api.  This should be transparent
            users = {}
            for item in permission['users']:
                users[item['username']] = item['permissions']
            permission['users'] = users
            permission_manager = factory.permission_manager()
            for user, ops in users.items():
                users[user] = [permission_manager.operation_value_to_name(o) for o in ops]

        return generate_json_response_with_pulp_encoder(permissions)


class GrantToUserView(View):
    """
    Grant permissions to a user.
    """

    @auth_required(authorization.EXECUTE)
    @parse_json_body(json_type=dict)
    def post(self, request):
        """
        Grant permissions to a user.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest

        :return: An empty response
        :rtype: django.http.HttpResponse
        """
        params = request.body_as_json
        login = params.get('login', None)
        resource = params.get('resource', None)
        operation_names = params.get('operations', None)

        _validate_params({'login': login,
                          'resource': resource,
                          'operation_names': operation_names})

        # Grant permission synchronously
        permission_manager = factory.permission_manager()
        operations = permission_manager.operation_names_to_values(operation_names)
        grant_perm = permission_manager.grant(resource, login, operations)
        return generate_json_response(grant_perm)


class RevokeFromUserView(View):
    """
    Revoke permission from user.
    """

    @auth_required(authorization.EXECUTE)
    @parse_json_body(json_type=dict)
    def post(self, request):
        """
        Revoke permissions from a user.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest

        :return: An empty response
        :rtype: django.http.HttpResponse
        """
        params = request.body_as_json
        login = params.get('login', None)
        resource = params.get('resource', None)
        operation_names = params.get('operations', None)

        _validate_params({'login': login,
                          'resource': resource,
                          'operation_names': operation_names})

        permission_manager = factory.permission_manager()
        operations = permission_manager.operation_names_to_values(operation_names)
        revoke_perm = permission_manager.revoke(resource, login, operations)
        return generate_json_response(revoke_perm)


class GrantToRoleView(View):
    """
    Grant permission to a role
    """

    @auth_required(authorization.EXECUTE)
    @parse_json_body(json_type=dict)
    def post(self, request):
        """
        Grant permissions to a role.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest

        :return: An empty response
        :rtype: django.http.HttpResponse
        """
        params = request.body_as_json
        role_id = params.get('role_id', None)
        resource = params.get('resource', None)
        operation_names = params.get('operations', None)

        _validate_params({'role_id': role_id,
                          'resource': resource,
                          'operation_names': operation_names})

        # Grant permission synchronously
        role_manager = factory.role_manager()
        permission_manager = factory.permission_manager()
        operations = permission_manager.operation_names_to_values(operation_names)
        add_perm = role_manager.add_permissions_to_role(role_id, resource, operations)
        return generate_json_response(add_perm)


class RevokeFromRoleView(View):
    """
    Revoke permission from a role.
    """

    @auth_required(authorization.EXECUTE)
    @parse_json_body(json_type=dict)
    def post(self, request):
        """
        Revoke permissions from a role.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest

        :return: An empty response
        :rtype: django.http.HttpResponse
        """

        params = request.body_as_json
        role_id = params.get('role_id', None)
        resource = params.get('resource', None)
        operation_names = params.get('operations', None)

        _validate_params({'role_id': role_id,
                          'resource': resource,
                          'operation_names': operation_names})

        role_manager = factory.role_manager()
        permission_manager = factory.permission_manager()
        operations = permission_manager.operation_names_to_values(operation_names)
        remove_perm = role_manager.remove_permissions_from_role(role_id, resource, operations)
        return generate_json_response(remove_perm)


def _validate_params(params):
    """
    Raise MissingValue if any of the required params are None.

    :param params: parameters to be checked
    :type: dict
    :raises: MissingValue if some params are None
    """
    missing_values = []
    for key, value in params.items():
        if value is None:
            missing_values.append(key)

    if missing_values:
        raise pulp_exceptions.MissingValue(missing_values)
