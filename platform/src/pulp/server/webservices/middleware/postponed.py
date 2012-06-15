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

import logging

from pulp.server.compat import json, http_responses
from pulp.server.exceptions import OperationPostponed
from pulp.server.webservices import serialization


_LOG = logging.getLogger(__name__)


class PostponedOperationMiddleware(object):
    """
    Catch OperationPostponed exceptions and return an HTTP Accepted response
    along with the proper serialization of the asynchronous call information.
    """

    def __init__(self, app):
        self.app = app
        self.headers = {'Content-Encoding': 'utf-8',
                        'Content-Type': 'application/json',
                        'Content-Length': '-1'}

    def __call__(self, environ, start_response):
        try:
            return self.app(environ, start_response)
        except OperationPostponed, e:
            # TODO add some debugging logging
            serialized_call_report = e.call_report.serialize()
            href_obj = serialization.dispatch.task_href(e.call_report)
            serialized_call_report.update(href_obj)
            body = json.dumps(serialized_call_report)
            self.headers['Content-Length'] = str(len(body))
            start_str = '%d %s' % (e.http_status_code, http_responses[e.http_status_code])
            start_response(start_str, [(k, v) for k, v in self.headers.items()])
            return [body]
