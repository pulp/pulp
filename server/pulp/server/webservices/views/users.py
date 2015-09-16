"""
This module contains views that deal with User objects.
"""
from django.views.generic import View
from django.core.urlresolvers import reverse

from pulp.server import exceptions as pulp_exceptions
from pulp.server.auth import authorization
from pulp.server.db.model.auth import Permission
from pulp.server.managers import factory
from pulp.server.managers.auth.user import query
from pulp.server.webservices.views import search
from pulp.server.webservices.views.decorators import auth_required
from pulp.server.webservices.views.util import (generate_json_response,
                                                generate_json_response_with_pulp_encoder,
                                                generate_redirect_response,
                                                json_body_required)


USER_WHITELIST = [u'login', u'name', u'roles']


def serialize(user):
    """
    This function accepts a user object, adds a link to it, removes sensitive information from it,
    and returns the modified object.

    :param user: A user document
    :type  user: bson.BSON
    :return:     A modified version of the User, suitable for returning via the REST interface.
    :rtype:      bson.BSON
    """
    _add_link(user)
    _process_dictionary_against_whitelist(user, USER_WHITELIST)
    return user


class UserSearchView(search.SearchView):
    """
    This view provides GET and POST searching on User objects.
    """
    response_builder = staticmethod(generate_json_response_with_pulp_encoder)
    manager = query.UserQueryManager()
    serializer = staticmethod(serialize)


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
        query_manager = factory.user_query_manager()
        users = query_manager.find_all()

        for user in users:
            serialize(user)

        return generate_json_response_with_pulp_encoder(users)

    @auth_required(authorization.CREATE)
    @json_body_required
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
        # Pull all the user data
        user_data = request.body_as_json
        login = user_data.pop('login', None)
        if login is None:
            raise pulp_exceptions.MissingValue(['login'])
        password = user_data.pop('password', None)
        name = user_data.pop('name', None)
        if user_data:
            raise pulp_exceptions.InvalidValue(user_data.keys())
        # Creation
        manager = factory.user_manager()
        args = [login]
        kwargs = {'password': password,
                  'name': name}

        user = manager.create_user(*args, **kwargs)

        # Add the link to the user
        link = _add_link(user)

        # Grant permissions
        permission_manager = factory.permission_manager()
        permission_manager.grant_automatic_permissions_for_resource(link['_href'])

        response = generate_json_response_with_pulp_encoder(user)
        return generate_redirect_response(response, link['_href'])


class UserResourceView(View):
    """
    View for a specific user.
    """

    @auth_required(authorization.READ)
    def get(self, resuest, login):
        """
        Retrieve a specific user.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param login: login for the requested user
        :type login: str

        :return: Response containing the user
        :rtype: django.http.HttpResponse
        :raises: MissingResource if login does not exist
        """
        user = factory.user_query_manager().find_by_login(login)
        if user is None:
            raise pulp_exceptions.MissingResource(login)

        user = serialize(user)
        return generate_json_response_with_pulp_encoder(user)

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
        manager = factory.user_manager()
        result = manager.delete_user(login)

        # Delete any existing user permissions given to the creator of the user
        link = {'_href': reverse('user_resource',
                kwargs={'login': login})}
        if Permission.get_collection().find_one({'resource': link['_href']}):
            Permission.get_collection().remove({'resource': link})

        return generate_json_response(result)

    @auth_required(authorization.UPDATE)
    @json_body_required
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
        # Pull all the user update data
        user_data = request.body_as_json
        delta = user_data.get('delta', None)

        # Perform update
        manager = factory.user_manager()
        result = manager.update_user(login, delta)
        _process_dictionary_against_whitelist(result, USER_WHITELIST)
        return generate_json_response_with_pulp_encoder(result)


def _add_link(user):
    link = {'_href': reverse('user_resource',
            kwargs={'login': user['login']})}
    user.update(link)
    return link


def _process_dictionary_against_whitelist(source_dict, valid_keys):
    """
    Process a dictionary and remove all keys that are not in a known white list

    This method assumes that the _href, _id, and _ns keys are always valid

    :param source_dict: The dictionary to filter out values from
    :type source_dict: dict
    :param valid_keys: list of keys that are valid in the resulting object
    :type valid_keys: list of unicode
    """
    global_whitelist = [u'_href', u'_id', u'_ns']
    merged_whitelist = global_whitelist + valid_keys
    keys_list = source_dict.keys()
    for key in keys_list:
        if key not in merged_whitelist:
            source_dict.pop(key, None)
