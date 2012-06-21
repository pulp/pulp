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
    check_username_password, check_user_cert, check_consumer_cert, check_consumer_cert_no_user,
    check_oauth)
from pulp.server.auth.authorization import is_authorized, is_superuser
from pulp.server.auth.principal import clear_principal, set_principal
from pulp.server.compat import wraps
from pulp.server.webservices import http

_log = logging.getLogger(__name__)

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
            # XXX jesus h christ: is this some god awful shit
            # please, please refactor this into ... something ... anything!
            user = None
            is_consumer = False
            permissions = {'/v2/consumers/' : [0, 1]}
            # first, try username:password authentication
            username, password = http.username_password()
            if username is not None:
                user = check_username_password(username, password)
                if user is None:
                    return self.unauthorized(user_pass_fail_msg)

            # second, try certificate authentication
            if user is None:
                cert_pem = http.ssl_client_cert()
                if cert_pem is not None:
                    # first, check user certificate
                    user = check_user_cert(cert_pem)
                    if user is None:
                        # second, check consumer certificate

                        # This is temporary solution to solve authorization failure for consumers
                        # because of no associated users. We would likely be going with a similar approach
                        # for v2 with static permissions for consumers instead of associates users. Once we
                        # have users and permissions flushed out for v2, this code will look much better.

                        # user = check_consumer_cert(cert_pem)
                        user = check_consumer_cert_no_user(cert_pem)
                        if user:
                            is_consumer = True
                            consumer_base_url = '/v2/consumers/%s' % user + '/'
                            permissions[consumer_base_url] = [0, 1, 2, 3, 4]

                # third, check oauth credentials
                if user is None:
                    auth = http.http_authorization()
                    username = http.request_info('HTTP_PULP_USER')
                    if None in (auth, username):
                        if cert_pem is not None:
                            return self.unauthorized(cert_fail_msg)
                    else:
                        meth = http.request_info('REQUEST_METHOD')
                        url = http.request_url()
                        query = http.request_info('QUERY_STRING')
                        user = check_oauth(username, meth, url, auth, query)
                        if user is None:
                            return self.unauthorized(oauth_fail_msg)

            # authentication has failed
            if user is None:
                return self.unauthorized(authen_fail_msg)

            # procedure to check consumer permissions - part of the temporary solution described above
            def is_consumer_authorized(resource, consumer, operation):
                if consumer_base_url in resource and operation in permissions[consumer_base_url]:
                    return True
                else:
                    return False

            # forth, check authorization
            if super_user_only and not is_superuser(user):
                return self.unauthorized(author_fail_msg)

            # if the operation is None, don't check authorization
            elif operation is not None:
                if is_consumer and is_consumer_authorized(http.resource_path(), user, operation):
                    value = method(self, *args, **kwargs)
                    clear_principal()
                    return value
                elif is_authorized(http.resource_path(), user, operation):
                    pass
                else:
                    return self.unauthorized(author_fail_msg)

            # everything ok, manage the principal and call the method
            set_principal(user)
            value = method(self, *args, **kwargs)
            clear_principal()
            return value

        return _auth_decorator
    return _auth_required
