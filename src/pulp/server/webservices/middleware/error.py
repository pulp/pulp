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

import httplib
import logging
import sys
import traceback
from gettext import gettext as _

try:
    import json
except ImportError:
    import simplejson as json

from pulp.server.webservices.http import http_responses


_LOG = logging.getLogger(__name__)


def serialize_error(e, tb=None):
    """
    Serialize a server-side error into a JSON object
    """
    assert isinstance(e, Exception)
    msg = None
    args = e.args[:]
    tb = tb or _('traceback available in server log')
    if isinstance(e.args[0], basestring):
        msg = args[0]
        args = args[1:]
    err = {
        'http_status': httplib.INTERNAL_SERVER_ERROR,
        'error_message': msg,
        'error_args': args,
        'traceback': tb,
    }
    serial_err = json.dumps(err)
    return serial_err


class ErrorHandlerMiddleware(object):
    """
    Catch otherwise unhandled exceptions and return appropriate 500 responses.
    @ivar app: WSGI application or middleware
    @ivar debug: boolean flag when true, puts the traceback into the response
    """

    def __init__(self, app, debug=False):
        self.app = app
        self.debug = debug

    def __call__(self, enviorn, start_response):
        try:
            return self.app(enviorn, start_response)
        except Exception, e:
            exc_info = sys.exc_info()
            tb = ''.join(traceback.format_exception(*exc_info))
            _LOG.error(tb)
            if not self.debug:
                tb = None
            serial_err = serialize_error(e, tb)
            status = httplib.INTERNAL_SERVER_ERROR
            status_str = '%d %s' % (status, http_responses[status])
            start_response(status_str, [('Content-Type', 'application/json'),
                                        ('Content-Length', str(len(serial_err)))])
            return serial_err
