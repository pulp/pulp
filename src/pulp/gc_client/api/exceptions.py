# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
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
Defines exception classes to handle server connection and request exceptions
"""

from gettext import gettext as _

# Base class for server request exceptions

class RequestException(Exception):
    """
    Base exception class
    """
    def __init__(self, response_body):
        Exception.__init__(self)
        self._href = response_body['_href']
        self.http_request_method = response_body['http_request_method']
        self.http_status = response_body['http_status']
        self.error_message = response_body['error_message']
        self.exception = response_body['exception']
        self.traceback = response_body['traceback']
        
    def __str__(self):
        return _('RequestException: %s request on %s failed with %s - %s\n' % (self.http_request_method, 
                                                                               self._href, 
                                                                               self.http_status, 
                                                                               self.error_message))
            

# Response code = 400
class BadRequestException(RequestException): pass

# Response code = 401. Commented out for now until we fix server side exception handling to follow same hierarchy.
# class PermissionsException(RequestException): pass

# Response code = 404
class NotFoundException(RequestException): pass

# Response code = 409
class DuplicateResourceException(RequestException): pass

# Response code >= 500
class PulpServerException(RequestException): pass


class ConnectionException(Exception):
    """
    Exception to indicate a less than favorable response from the server.
    The arguments are [0] the response status as an integer and
    [1] the response message as a dict, if we managed to decode from json,
    or a str if we didn't [2] potentially a traceback, if the server response
    was a python error, otherwise it will be None
    """
    pass

class PermissionsException(Exception):
    """
    Indicates an attempt was made to do a server call without providing
    authentication credentials, either through a certificate or as command
    line flags.
    """
    pass
