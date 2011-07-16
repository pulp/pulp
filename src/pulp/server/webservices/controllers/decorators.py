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

import itertools
import logging
import sys
import traceback
from gettext import gettext as _
from pprint import pformat

from pulp.server.auth.authentication import (
    check_username_password, check_user_cert, check_consumer_cert, check_oauth)
from pulp.server.auth.authorization import is_authorized, is_superuser
from pulp.server.auth.principal import clear_principal, set_principal
from pulp.server.compat import wraps
from pulp.server.webservices import http, mongo


_log = logging.getLogger(__name__)


def error_handler(method):
    """
    Controller method wrapper that catches internal errors and reports them as
    JSON serialized trace back strings
    """
    @wraps(method)
    def report_error(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except Exception:
            exc_info = sys.exc_info()
            tb_msg = ''.join(traceback.format_exception(*exc_info))
            _log.error("%s" % (traceback.format_exc()))
            return self.internal_server_error(tb_msg)
    return report_error


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
                        user = check_consumer_cert(cert_pem)
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
            # forth, check authorization
            if super_user_only and not is_superuser(user):
                return self.unauthorized(author_fail_msg)
            # if the operation is None, don't check authorization
            elif operation is not None and \
                 not is_authorized(http.resource_path(), user, operation):
                return self.unauthorized(author_fail_msg)
            # everything ok, manage the principal and call the method
            set_principal(user)
            value = method(self, *args, **kwargs)
            clear_principal()
            return value

        return _auth_decorator
    return _auth_required


def collection_query(*valid_filters):
    """
    Parse out common query parameters as filters in addition to any custom
    filters needed by the controller and build a mongo db spec document.
    NOTE: this decorator requires the decorated method to accept a keyword
    argument, spec, that is a mongo db spec document for passing to the find
    collection method.
    @type valid_filters: str's
    @param valid_filters: additional valid query parameters
    """
    def _collection_query(method):
        common_filters = ('_intersect', '_union')

        @wraps(method)
        def _query_decortator(self, *args, **kwargs):
            filters = self.filters(tuple(itertools.chain(common_filters, valid_filters)))
            intersect = filters.pop('_intersect', ())
            union = filters.pop('_union', ())
            spec = mongo.filters_to_set_spec(filters, intersect, union)
            kwargs.update({'spec': spec})
            return method(self, *args, **kwargs)

        return _query_decortator
    return _collection_query

