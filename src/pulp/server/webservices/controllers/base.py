# -*- coding: utf-8 -*-
#
# Copyright © 2010 Red Hat, Inc.
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
from gettext import gettext as _

import web
from pymongo import json_util

from pulp.common import dateutils
from pulp.server import async
from pulp.server.compat import json
from pulp.server.tasking.scheduler import (
    ImmediateScheduler, AtScheduler, IntervalScheduler)
from pulp.server.tasking.task import task_complete_states
from pulp.server.webservices import http


_log = logging.getLogger(__name__)


class JSONController(object):
    """
    Base controller class with convenience methods for JSON serialization
    """
    # input methods -----------------------------------------------------------

    def params(self):
        """
        JSON decode the objects in the requests body and return them
        @return: dict of parameters passed in through the body
        """
        data = web.data()
        if not data:
            return {}
        return json.loads(data)

    def data(self):
        """
        Get binary POST/PUT payload.
        @return: raw data.
        """
        return web.data()

    def filters(self, valid):
        """
        Fetch any parameters passed on the url
        @type valid: list of str's
        @param valid: list of expected query parameters
        @return: dict of param: [value(s)] of uri query parameters
        """
        return http.query_parameters(valid)

    # result methods ----------------------------------------------------------

    def _task_to_dict(self, task):
        """
        Convert a task to a dictionary (non-destructive) while retaining the
        pertinent information for a status check but in a more convenient form
        for JSON serialization.
        @type task: Task instance
        @param task: task to convert
        @return dict representing task
        """
        fields = ('id', 'job_id', 'class_name', 'method_name', 'args', 'state', 'result',
                  'exception', 'traceback', 'progress')
        d = dict((f, getattr(task, f)) for f in fields)
        # time fields must be in iso8601 format
        fields = ('start_time', 'finish_time', 'scheduled_time')
        for f in fields:
            t = getattr(task, f, None)
            d[f] = t and dateutils.format_iso8601_datetime(t)
        # add scheduler information so we can differentiate between recurring
        # and non-recurring tasks
        d['scheduler'] = None
        if isinstance(task.scheduler, ImmediateScheduler):
            d['scheduler'] = 'immediate'
        elif isinstance(task.scheduler, AtScheduler):
            d['scheduler'] = 'at'
        elif isinstance(task.scheduler, IntervalScheduler):
            d['scheduler'] = 'interval'
        return d

    def _job_to_dict(self, job):
        tasks = []
        d = dict(id=job.id, tasks=tasks)
        for t in job.tasks:
            tasks.append(self._task_to_dict(t))
        return d


    def filter_results(self, results, filters):
        """
        @deprecated: use mongo.filters_to_re_spec and pass the result into
                     pulp's api instead
        @type results: iterable of pulp model instances
        @param results: results from a db query
        @type filters: dict of str: list
        @param filters: result filters passed in, in the uri
        @return: list of model instances that meet the criteria in the filters
        """
        if not filters:
            return results
        new_results = []
        for result in results:
            is_good = True
            for filter, criteria in filters.items():
                if result[filter] not in criteria:
                    is_good = False
                    break
            if is_good:
                new_results.append(result)
        return new_results

    # http response methods ---------------------------------------------------

    def _output(self, data):
        """
        JSON encode the response and set the appropriate headers
        """
        body = json.dumps(data, default=json_util.default)
        http.header('Content-Type', 'application/json')
        http.header('Content-Length', len(body))
        return body

    def _error_dict(self, msg, code=None):
        """
        Standardized error returns
        """
        if code is None:
            code = _('not set')
        d = {'error_message': msg,
             'error_code': code, # reserved for future use
             'http_status': web.ctx.status, }
        return d

    def ok(self, data):
        """
        Return an ok response.
        @type data: mapping type
        @param data: data to be returned in the body of the response
        @return: JSON encoded response
        """
        http.status_ok()

        return self._output(data)

    def created(self, location, data):
        """
        Return a created response.
        @type location: str
        @param location: URL of the created resource
        @type data: mapping type
        @param data: data to be returned in the body of the response
        @return: JSON encoded response
        """
        http.status_created()
        http.header('Location', location)
        return self._output(data)

    def accepted(self, status):
        """
        Return an accepted response with status information in the body.
        @return: JSON encoded response
        """
        http.status_accepted()
        return self._output(status)

    def no_content(self):
        """
        Return a no content response
        @return: JSON encoded response
        """
        http.status_no_content()
        return self._output(None)

    def partial_content(self, data):
        '''
        Returns a partial content response. Typically, the returned data should
        include:
        - a list of successful content updates
        - a list of failed content updates
        - an overarching error message if applicable
        '''
        http.status_partial()
        return self._output(data)

    def bad_request(self, msg=None):
        """
        Return a not found error.
        @param msg: optional error message
        @return: JSON encoded response
        """
        http.status_bad_request()
        return self._output(msg)

    def unauthorized(self, msg=None):
        """
        Return an unauthorized error.
        @param msg: optional error message
        @return: JSON encoded response
        """
        http.status_unauthorized()
        return self._output(msg)

    def not_found(self, msg=None):
        """
        Return a not found error.
        @param msg: optional error message
        @return: JSON encoded response
        """
        http.status_not_found()
        return self._output(msg)

    def method_not_allowed(self, msg=None):
        """
        Return a method not allowed error.
        @param msg: optional error message
        @return: JSON encoded response
        """
        http.status_method_not_allowed()
        return None

    def not_acceptable(self, msg=None):
        """
        Return a not acceptable error.
        @param msg: optional error message
        @return: JSON encoded response
        """
        http.status_not_acceptable()
        return self._output(msg)

    def conflict(self, msg=None):
        """
        Return a conflict error.
        @param msg: optional error message
        @return: JSON encoded response
        """
        http.status_conflict()
        return self._output(msg)

    def internal_server_error(self, msg=None):
        """
        Return an internal server error.
        @param msg: optional error message
        @return: JSON encoded response
        """
        http.status_internal_server_error()
        return self._output(msg)

    def not_implemented(self, msg=None):
        """
        Return a not implemented error.
        @param msg: optional error message
        @return: JSON encoded response
        @rtype: str
        """
        http.status_not_implemented()
        return self._output(msg)
