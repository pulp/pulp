"""
This module contains decorators for web.py class methods.

It is important that these decorators only be used on methods of
pulp.server.webservices.controllers.base.JSONController classes, it is assumed
that certain other methods will exist.
"""

import logging

from pulp.common import error_codes
from pulp.server.auth.authorization import CREATE, READ, UPDATE, DELETE, EXECUTE, OPERATION_NAMES
from pulp.server.config import config
from pulp.server.compat import wraps
from pulp.server.exceptions import PulpCodedAuthenticationException
from pulp.server.managers import factory
from pulp.server.webservices import http


_logger = logging.getLogger(__name__)

DEFAULT_CONSUMER_PERMISSIONS = {'/v2/repositories/': [READ]}


# Each authentication method reads request header to get appropriate credentials information,
# runs authentication check and returns corresponding user login or consumer id.
def check_preauthenticated():
    # Support web server level authentication of users
    username = http.request_info("REMOTE_USER")
    if username is not None:
        # Omitting the password = assume preauthenticated
        userid = factory.authentication_manager().check_username_password(username)
        if userid is None:
            # User is not in the local database, nor in LDAP
            raise PulpCodedAuthenticationException(error_code=error_codes.PLP0029, user=username)
        else:
            _logger.debug("User preauthenticated: %s" % username)
            return userid


def password_authentication():
    username, password = http.username_password()
    if username is not None:
        userid = factory.authentication_manager().check_username_password(username, password)
        if userid is None:
            raise PulpCodedAuthenticationException(error_code=error_codes.PLP0030, user=username)
        else:
            _logger.debug("User [%s] authenticated with password" % username)
            return userid


def user_cert_authentication():
    cert_pem = http.ssl_client_cert()
    if cert_pem is not None:
        userid = factory.authentication_manager().check_user_cert(cert_pem)
        if userid:
            _logger.debug("User authenticated with ssl cert: %s" % userid)
            return userid
    return None


def consumer_cert_authentication():
    cert_pem = http.ssl_client_cert()
    if cert_pem is not None:
        consumerid = factory.authentication_manager().check_consumer_cert(cert_pem)
        if consumerid is not None:
            _logger.debug("Consumer authenticated with ssl cert: %s" % consumerid)
            return consumerid


def oauth_authentication():
    if not config.getboolean('oauth', 'enabled'):
        return None, False

    username = http.request_info('HTTP_PULP_USER')
    auth = http.http_authorization()
    cert_pem = http.ssl_client_cert()
    if username is None or auth is None:
        if cert_pem is not None:
            raise PulpCodedAuthenticationException(error_code=error_codes.PLP0027, user=username)
        return None, False
    meth = http.request_info('REQUEST_METHOD')
    url = http.request_url()
    query = http.request_info('QUERY_STRING')
    userid, is_consumer = factory.authentication_manager().check_oauth(username, meth, url, auth,
                                                                       query)
    if userid is None:
        raise PulpCodedAuthenticationException(error_code=error_codes.PLP0028, user=username)
    _logger.debug("User authenticated with Oauth: %s" % userid)
    return userid, is_consumer


def is_consumer_authorized(resource, consumerid, operation):
    """
    Checks consumer authorization for given resource uri.
    Return True if authorized, False otherwise.

    :type resource: str
    :param resource: resource uri to check permissions for.

    :type consumerid: str
    :param consumerid: uniquely identifies consumer

    :rtype: bool
    :return:  True if authorized, False otherwise.
    """
    permissions = DEFAULT_CONSUMER_PERMISSIONS
    consumer_base_url = '/v2/consumers/%s/' % consumerid
    # Add all permissions to base url for this consumer.
    permissions[consumer_base_url] = [CREATE, READ, UPDATE, DELETE, EXECUTE]

    parts = [p for p in resource.split('/') if p]
    while parts:
        current_resource = '/%s/' % '/'.join(parts)
        if current_resource in permissions and permissions[current_resource] is not None:
            if operation in permissions[current_resource]:
                return True
        parts = parts[:-1]
    return False


def _verify_auth(self, operation, super_user_only, method, *args, **kwargs):
    """
    Internal method for checking authentication and authorization. This code
    is kept outside of the decorator which calls it so that it can be mocked.
    This allows for the decorator itself which calls here to have assertions
    made about the operation and super_user values set in the view code.

    An operation of None means not to check authorization; only check
    authentication.

    The super_user_only flag set to True means that only members of the
    built in SuperUsers role are authorized.

    :type operation: int or None
    :param operation: The operation a user needs permission for, or None to
                      skip authorization.

    :type super_user_only: bool
    :param super_user_only: Only authorize a user if they are a super user.
    """
    # Check Authentication

    # Run through each registered and enabled auth function
    is_consumer = False
    registered_auth_functions = [check_preauthenticated,
                                 password_authentication,
                                 user_cert_authentication,
                                 consumer_cert_authentication,
                                 oauth_authentication]

    user_authenticated = False
    for authenticate_user in registered_auth_functions:
        if authenticate_user == oauth_authentication:
            userid, is_consumer = authenticate_user()
        else:
            userid = authenticate_user()

        if userid is not None:
            user_authenticated = True
            if authenticate_user == consumer_cert_authentication:
                is_consumer = True
            break

    if not user_authenticated:
        raise PulpCodedAuthenticationException(error_code=error_codes.PLP0025)

    # Check Authorization

    principal_manager = factory.principal_manager()
    user_query_manager = factory.user_query_manager()

    if super_user_only and not user_query_manager.is_superuser(userid):
        raise PulpCodedAuthenticationException(error_code=error_codes.PLP0026, user=userid,
                                                       operation=OPERATION_NAMES[operation])
    # if the operation is None, don't check authorization
    elif operation is not None:
        if is_consumer:
            if is_consumer_authorized(http.resource_path(), userid, operation):
                # set default principal = SYSTEM
                principal_manager.set_principal()
            else:
                raise PulpCodedAuthenticationException(error_code=error_codes.PLP0026,
                                                               user=userid,
                                                               operation=OPERATION_NAMES[operation])
        elif user_query_manager.is_authorized(http.resource_path(), userid, operation):
            user = user_query_manager.find_by_login(userid)
            principal_manager.set_principal(user)
        else:
            raise PulpCodedAuthenticationException(error_code=error_codes.PLP0026,
                                                           user=userid,
                                                           operation=OPERATION_NAMES[operation])

    # Authentication and authorization succeeded. Call method and then clear principal.
    value = method(self, *args, **kwargs)
    principal_manager.clear_principal()
    return value


def auth_required(operation=None, super_user_only=False):
    """
    View method wrapper that authenticates users based on various credentials
    and then checks their authorization before allowing the view to be
    accessed.

    An operation of None means not to check authorization; only check
    authentication.

    The super_user_only flag set to True means that only members of the
    built in SuperUsers role are authorized.

    :type operation: int or None
    :param operation: The operation a user needs permission for or None to
                      skip authorization.

    :type super_user_only: bool
    :param super_user_only: Only authorize a user if they are a super user.
    """
    def _auth_required(method):
        """
        Closure method for decorator.
        """
        @wraps(method)
        def _auth_decorator(self, *args, **kwargs):
            """
            Calls the internal method which provides the authorization and
            authentication.

            :param args: The positional arguments to be passed to the wrapped
                         view.
            :type args: tuple

            :param kwargs: The keyword arguments to be passed to the wrapped
                           view.
            :type kwargs: dict

            :raises: An Authorization or Authentication exception if either
                     is invalid.
            :returns: The result of the wrapped view method.
            """
            return _verify_auth(self, operation, super_user_only, method, *args, **kwargs)

        return _auth_decorator
    return _auth_required
