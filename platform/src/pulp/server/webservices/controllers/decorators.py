# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""
This module contains decorators for web.py class methods.

It is important that these decorators only be used on methods of
pulp.server.webservices.controllers.base.JSONController classes, it is assumed
that certain other methods will exist.
"""

import logging
from gettext import gettext as _

from pulp.server.auth.authentication import (
    check_username_password, check_user_cert, check_consumer_cert,
    check_oauth, is_oauth_enabled)
from pulp.server.managers import factory
from pulp.server.compat import wraps
from pulp.server.webservices import http

# -- constants ----------------------------------------------------------------

_LOG = logging.getLogger(__name__)


class AuthenticationFailed(Exception):
    def __str__(self):
        class_name = self.__class__.__name__
        msg = _('Pulp auth exception occurred: %(c)s') % {'c': class_name}
        return msg.encode('utf-8')


def auth_required(operation=None, super_user_only=False):
    """
    Controller method wrapper that authenticates users based on various
    credentials and then checks their authorization before allowing the
    controller to be accessed.

    A None for the operation means not to check authorization, only check
    authentication.

    The super_user_only flag set to True means that only members of the
    built in SuperUsers role are authorized.

    @type operation: int or None
    @param operation: the operation a user needs permission for

    @type super_user_only: bool
    @param super_user_only: only authorize a user if they are a super user
    """
    def _auth_required(method):
        """
        Closure method for decorator.
        """
        user_pass_fail_msg = _('Invalid username or password')
        cert_fail_msg = _('Invalid SSL Certificate')
        oauth_fail_msg = _('Invalid OAuth Credentials')
        authen_fail_msg = _('Authentication Required')
        author_fail_msg = _('Permission Denied')

        @wraps(method)
        def _auth_decorator(self, *args, **kwargs):

            is_consumer = False
            principal_manager = factory.principal_manager()

            def check_preauthenticated():
                # Support web server level authentication of users
                username = http.request_info("REMOTE_USER")
                if username is not None:
                    # Omitting the password = assume preauthenticated
                    user = check_username_password(username)
                    if user is None:
                        # User is not in the local database, nor in LDAP
                        raise AuthenticationFailed('Given pre-authenticated user does not exist')
                    else:
                        _LOG.debug("User preauthenticated: %s" % username)
                        return user
                return None
            
            def password_authentication():
                username, password = http.username_password()
                if username is not None:
                    user = check_username_password(username, password)
                    if user is None:
                        raise AuthenticationFailed(user_pass_fail_msg)
                    else:
                        _LOG.debug("User password authentication: %s" % username)
                        return user
                return None
                
            def user_cert_authentication():
                cert_pem = http.ssl_client_cert()
                if cert_pem is not None:
                    user = check_user_cert(cert_pem)
                    if user:
                        _LOG.debug("User cert authentication: %s" % user)
                        return user
                return None

            def consumer_cert_authentication():
                cert_pem = http.ssl_client_cert()
                if cert_pem is not None:
                    consumerid = check_consumer_cert(cert_pem)
                    if consumerid is not None:
                        _LOG.debug("Consumer cert authentication: %s" % consumerid)
                        return consumerid
                return None

            # Only install this one if oauth is configured
            def oauth_authentication():
                if not is_oauth_enabled():
                    return None
                username = http.request_info('HTTP_PULP_USER')
                auth = http.http_authorization()
                cert_pem = http.ssl_client_cert()
                if username is None or auth is None:
                    if cert_pem is not None:
                        raise AuthenticationFailed(cert_fail_msg)
                    return None
                meth = http.request_info('REQUEST_METHOD')
                url = http.request_url()
                query = http.request_info('QUERY_STRING')
                user = check_oauth(username, meth, url, auth, query)

                if user is None:
                    raise AuthenticationFailed(oauth_fail_msg)
                _LOG.debug("Oauth authentication: %s" % user)
                return user

            registered_auth_functions = [check_preauthenticated, 
                                         password_authentication, 
                                         user_cert_authentication, 
                                         consumer_cert_authentication, 
                                         oauth_authentication]

            user_authenticated = False
            for authenticate_user in registered_auth_functions:
                try:
                    user = authenticate_user()
                except AuthenticationFailed, ex:
                    return self.unauthorized(ex)
                
                if user is not None:
                    user_authenticated = True
                    if authenticate_user == consumer_cert_authentication:
                        is_consumer = True
                    break

            if not user_authenticated:
                return self.unauthorized(oauth_fail_msg)
                
            # procedure to check consumer permissions - part of the temporary solution described above
            def is_consumer_authorized(resource, consumer, operation):
                pm = factory.permission_manager()
                permissions = {'/v2/consumers/' : [pm.CREATE, pm.READ]}
                consumer_base_url = '/v2/consumers/%s/' % consumer
                permissions[consumer_base_url] = [pm.CREATE, pm.READ, pm.UPDATE, pm.DELETE, pm.EXECUTE]
                if consumer_base_url in resource and operation in permissions[consumer_base_url]:
                    return True
                else:
                    return False

            # check authorization
            user_query_manager = factory.user_query_manager()
            if super_user_only and not user_query_manager.is_superuser(user['login']):
                return self.unauthorized(author_fail_msg)

            # if the operation is None, don't check authorization
            elif operation is not None:
                if is_consumer and is_consumer_authorized(http.resource_path(), user, operation):
                    value = method(self, *args, **kwargs)
                    principal_manager.clear_principal()
                    return value
                elif user_query_manager.is_authorized(http.resource_path(), user['login'], operation):
                    pass
                else:
                    return self.unauthorized(author_fail_msg)

            # everything ok, manage the principal and call the method
            principal_manager.set_principal(user)
            value = method(self, *args, **kwargs)
            principal_manager.clear_principal()
            return value

        return _auth_decorator
    return _auth_required
