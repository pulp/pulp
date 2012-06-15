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

from pulp.server.compat import json, http_responses
from pulp.server.exceptions import PulpException
from pulp.server.webservices import serialization


_LOG = logging.getLogger(__name__)


class ExceptionHandlerMiddleware(object):
    """
    Catch otherwise unhandled exceptions and return appropriate 500 responses.
    @ivar app: WSGI application or middleware
    @ivar debug: boolean flag when true, puts the traceback into the response
    """

    def __init__(self, app, debug=False):
        self.app = app
        self.debug = debug
        self.headers = {'Content-Encoding': 'utf-8',
                        'Content-Type': 'application/json',
                        'Content-Length': '-1'}

    def __call__(self, environ, start_response):
        try:
            return self.app(environ, start_response)
        except:
            t, e, tb = sys.exc_info()
            status = None
            error_obj = None
            record_exception_and_traceback = self.debug
            if isinstance(e, PulpException):
                status = e.http_status_code
                if type(e) == PulpException:
                    # un-derived exceptions earn you a traceback
                    record_exception_and_traceback = True
                error_obj = serialization.error.http_error_obj(status, str(e))
                error_obj.update(e.data_dict())
                if record_exception_and_traceback:
                    error_obj['exception'] = traceback.format_exception_only(t, e)
                    error_obj['traceback'] = traceback.format_tb(tb)
            else:
                msg = _('Unhandled Exception')
                _LOG.exception(msg)
                status = httplib.INTERNAL_SERVER_ERROR
                error_obj = serialization.error.exception_obj(e, tb, msg)
            serialized_error = json.dumps(error_obj)
            self.headers['Content-Length'] = str(len(serialized_error))
            status_str = '%d %s' % (status, http_responses[status])
            start_response(status_str, [(k, v) for k, v in self.headers.items()])
            return [serialized_error]
