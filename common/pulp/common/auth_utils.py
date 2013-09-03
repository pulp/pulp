# -*- coding: utf-8 -*-
# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

# The following error codes will be returned when a user fails an authentication check
# to better describe why. See

# Key in the JSON response that contains the error code
CODE_KEY = 'auth_error_code'

CODE_FAILED = 'authentication_failed'
CODE_PERMISSION = 'permission_denied'
CODE_INVALID_SSL_CERT = 'invalid_ssl_certificate'
CODE_OAUTH = 'invalid_oauth_credentials'
CODE_PREAUTH = 'pre_auth_remote_user_missing'
CODE_USER_PASS = 'invalid_username_or_password'


def generate_failure_response(code):
    """
    Generates a JSON document describing an authentication failure using the programmatic error
    codes.

    :param code: error code to describe the reason for the failure
    :type  code: str

    :return: JSON document suitable for returning through the REST API layer
    :rtype:  dict
    """
    return {CODE_KEY : code}


def get_error_code(response_doc):
    """
    Returns the CODE_* error code from the given response. The response is the result
    of the generate_failure_response method above.

    :param response_doc: response describing the error
    :type  response_doc: dict

    :return: code describing the error
    :rtype:  str
    """
    return response_doc[CODE_KEY]
