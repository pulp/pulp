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


logger = logging.getLogger(__name__)


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
        except Exception, e:
            if isinstance(e, PulpException):
                status = e.http_status_code
                response = serialization.error.http_error_obj(status, str(e))
                response.update(e.data_dict())
                response['error'] = e.to_dict()
            else:
                # If it's not a Pulp exception, return a 500
                msg = _('Unhandled Exception')
                logger.error(msg)
                status = httplib.INTERNAL_SERVER_ERROR
                response = serialization.error.http_error_obj(status, str(e))

            if status == httplib.INTERNAL_SERVER_ERROR or self.debug:
                logger.exception(str(e))
                e_type, e_value, trace = sys.exc_info()
                response['exception'] = traceback.format_exception_only(e_type, e_value)
                response['traceback'] = traceback.format_tb(trace)
            else:
                logger.info(str(e))

            serialized_response = json.dumps(response)
            self.headers['Content-Length'] = str(len(serialized_response))
            status_str = '%d %s' % (status, http_responses[status])
            start_response(status_str, [(k, v) for k, v in self.headers.items()])
            return [serialized_response]
