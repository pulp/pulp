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

from celery.result import AsyncResult

from pulp.server.async.tasks import TaskResult
from pulp.server.compat import json, json_util, http_responses
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
            report = e.call_report
            if isinstance(e.call_report, AsyncResult):
                report = TaskResult.from_async_result(e.call_report)
            serialized_call_report = report.serialize()
            for task in serialized_call_report['spawned_tasks']:
                href_obj = serialization.dispatch.task_result_href(task)
                task.update(href_obj)

            body = json.dumps(serialized_call_report, default=json_util.default)

            self.headers['Content-Length'] = str(len(body))
            start_str = '%d %s' % (e.http_status_code, http_responses[e.http_status_code])

            start_response(start_str, [(k, v) for k, v in self.headers.items()])
            return [body]
