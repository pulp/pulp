"""
This module contains views that deal with User objects.
"""
from django.views.generic import View
from django.core.urlresolvers import reverse

from pulp.server import exceptions as pulp_exceptions
from pulp.server.auth import authorization
from pulp.server.controllers import user as user_controller
from pulp.server.db import model
from pulp.server.db.model.auth import Permission
from pulp.server.managers import factory
from pulp.server.webservices.views import search
from pulp.server.webservices.views.decorators import auth_required
from pulp.server.webservices.views.util import (generate_json_response,
                                                generate_json_response_with_pulp_encoder,
                                                generate_redirect_response,
                                                parse_json_body)


class UserSearchView(search.SearchView):
    """
    This view provides GET and POST searching on User objects.
    """
    response_builder = staticmethod(generate_json_response_with_pulp_encoder)
    model = model.User


class UsersView(View):
    """
    Views for users.
    """

    @auth_required(authorization.READ)
    def get(self, request):
        """
        List all users.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest

        :return: Response containing a list of users
        :rtype: django.http.HttpResponse
        """
        users = model.User.SERIALIZER(model.User.objects(), multiple=True).data
        return generate_json_response_with_pulp_encoder(users)

    @auth_required(authorization.CREATE)
    @parse_json_body(json_type=dict)
    def post(self, request):
        """
        Create a new user.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest

        :return: Response containing the user
        :rtype: django.http.HttpResponse

        :raises: MissingValue if login field is missing
        :raises: InvalidValue if some parameters are invalid
        """
        user_data = request.body_as_json
        login = user_data.pop('login', None)
        if login is None:
            raise pulp_exceptions.MissingValue(['login'])
        password = user_data.pop('password', None)

        # name defaults to login
        name = user_data.pop('name', login)

        # Raise if extra data is passed
        if user_data:
            raise pulp_exceptions.InvalidValue(user_data.keys())

        new_user = user_controller.create_user(login, password=password, name=name)
        serialized_user = model.User.SERIALIZER(new_user).data

        # For backwards compatability. See https://pulp.plan.io/issues/1125
        serialized_user['id'] = str(serialized_user['_id'])

        # Grant permissions
        permission_manager = factory.permission_manager()
        permission_manager.grant_automatic_permissions_for_resource(serialized_user['_href'])

        response = generate_json_response_with_pulp_encoder(serialized_user)
        return generate_redirect_response(response, serialized_user['_href'])


class UserResourceView(View):
    """
    View for a specific user.
    """

    @auth_required(authorization.READ)
    def get(self, request, login):
        """
        Retrieve a specific user.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param login: login for the requested user
        :type login: str

        :return: Response containing the user
        :rtype: django.http.HttpResponse
        """
        user = model.User.objects.get_or_404(login=login)
        serialized_user = model.User.SERIALIZER(user).data
        return generate_json_response_with_pulp_encoder(serialized_user)

    @auth_required(authorization.DELETE)
    def delete(self, request, login):
        """
        Delete a user.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param login: login for the requested user
        :type login: str

        :return: An empty response
        :rtype: django.http.HttpResponse
        """
        user_controller.delete_user(login)

        # Delete any existing user permissions given to the creator of the user
        link = reverse('user_resource', kwargs={'login': login})
        if Permission.get_collection().find_one({'resource': link}):
            Permission.get_collection().remove({'resource': link})
        return generate_json_response()

    @auth_required(authorization.UPDATE)
    @parse_json_body(json_type=dict)
    def put(self, request, login):
        """
        Update a user.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param login: login for the requested user
        :type login: str

        :return: Response containing the user
        :rtype: django.http.HttpResponse
        """
        delta = request.body_as_json.get('delta')
        updated_user = user_controller.update_user(login, delta)
        serialized_user = model.User.SERIALIZER(updated_user).data
        return generate_json_response_with_pulp_encoder(serialized_user)
