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
from gettext import gettext as _

try:
    import json
except ImportError:
    import simplejson as json

from pulp.server.webservices.http import http_responses
from pulp.server.webservices import serialization


_LOG = logging.getLogger(__name__)


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
            _LOG.exception(_('Unhandled exception'))
            tb = None
            if self.debug:
                tb = sys.exc_info()[2]
            err_obj = serialization.error.serialize_exception(e, tb)
            serial_err = json.dumps(err_obj)
            status = httplib.INTERNAL_SERVER_ERROR
            status_str = '%d %s' % (status, http_responses[status])
            start_response(status_str, [('Content-Type', 'application/json'),
                                        ('Content-Length', str(len(serial_err)))])
            return serial_err
