#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

import functools
import logging
import sys
import traceback
from datetime import timedelta
from gettext import gettext as _

try:
    import json
except ImportError:
    import simplejson as json

import web
from pymongo import json_util

from pulp.server import async
from pulp.server.auth.authentication import (
    check_username_password, cert_authentication)
from pulp.server.auth.authorization import is_authorized, is_superuser
from pulp.server.auth.principal import clear_principal, set_principal
from pulp.server.tasking.task import task_complete_states
from pulp.server.webservices import http


_log = logging.getLogger(__name__)


class JSONController(object):
    """
    Base controller class with convenience methods for JSON serialization
    """
    @staticmethod
    def error_handler(method):
        """
        Static controller method wrapper that catches internal errors and
        reports them as JSON serialized trace back strings
        """
        @functools.wraps(method)
        def report_error(self, *args, **kwargs):
            try:
                return method(self, *args, **kwargs)
            except Exception:
                exc_info = sys.exc_info()
                tb_msg = ''.join(traceback.format_exception(*exc_info))
                _log.error("%s" % (traceback.format_exc()))
                return self.internal_server_error(tb_msg)
        return report_error

    @staticmethod
    def auth_required(operation=None):
        """
        """
        def _auth_required(method, super_user_only=False):
            authen_fail_msg = _('Authorization failed. Check your username and password or your certificate')
            author_fail_msg = _('Authorization failed. You do not have permission on this resource.')

            @functools.wraps(method)
            def _auth_decorator(self, *args, **kwargs):
                user = None
                # first, try username:password authentication
                username, password = http.username_password()
                if username is not None:
                    user = check_username_password(username, password)
                    if user is None:
                        return self.unauthorized(authen_fail_msg)
                # second, try user certificate authentication
                if user is None:
                    cert_pem = http.ssl_client_cert()
                    if cert_pem is None:
                        return self.unauthorized(authen_fail_msg)
                    user = cert_authentication(cert_pem)
                    if user is None:
                        return self.unauthorized(authen_fail_msg)
                # third, check authorization
                if super_user_only and not is_superuser(user):
                    return self.unauthorized(author_fail_msg)
                elif not is_authorized(http.resource_path(), user, operation):
                    return self.unauthorized(author_fail_msg)
                # everything ok, manage the principal and call the method
                set_principal(user)
                value = method(self, *args, **kwargs)
                clear_principal()
                return value

            return _auth_decorator
        return _auth_required

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

    def filters(self, valid):
        """
        Fetch any parameters passed on the url
        @type valid: list of str's
        @param valid: list of expected query parameters
        @return: dict of param: [value(s)] of uri query parameters
        """
        return http.query_parameters(valid)

    # result methods ----------------------------------------------------------

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
        http.header('Content-Type', 'application/json')
        return json.dumps(data, default=json_util.default)

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

    def no_content(self):
        """
        Return a no content response
        @return: JSON encoded response
        """
        http.status_no_content()
        return self._output(None)

    def bad_request(self, msg=None):
        """
        Return a not found error.
        @type msg: str
        @param msg: optional error message
        @return: JSON encoded response
        """
        http.status_bad_request()
        return self._output(msg)

    def unauthorized(self, msg=None):
        """
        Return an unauthorized error.
        @type msg: str
        @param msg: optional error message
        @return: JSON encoded response
        """
        http.status_unauthorized()
        return self._output(msg)

    def not_found(self, msg=None):
        """
        Return a not found error.
        @type msg: str
        @param msg: optional error message
        @return: JSON encoded response
        """
        http.status_not_found()
        return self._output(msg)

    def method_not_allowed(self, msg=None):
        """
        Return a method not allowed error.
        @type msg: str
        @param msg: optional error message
        @return: JSON encoded response
        """
        http.status_method_not_allowed()
        return None

    def not_acceptable(self, msg=None):
        """
        Return a not acceptable error.
        @type msg: str
        @param msg: optional error message
        @return: JSON encoded response
        """
        http.status_not_acceptable()
        return self._output(msg)

    def conflict(self, msg=None):
        """
        Return a conflict error.
        @type msg: str
        @param msg: optional error message
        @return: JSON encoded response
        """
        http.status_conflict()
        return self._output(msg)

    def internal_server_error(self, msg=None):
        """
        Return an internal server error.
        @type msg: str
        @param msg: optional error message
        @return: JSON encoded response
        """
        http.status_internal_server_error()
        return self._output(msg)


class AsyncController(JSONController):
    """
    Base controller class with convenience methods for executing asynchronous
    tasks.
    """

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
        fields = ('id', 'method_name', 'state', 'start_time', 'finish_time',
                 'result', 'exception', 'traceback', 'progress')
        return dict((f, getattr(task, f)) for f in fields)

    def _status_path(self, id):
        """
        Construct a URL path that can be used to poll a task's status
        A status path is constructed as follows:
        /<collection>/<object id>/<action>/<action id>/
        A GET request sent to this path will get a JSON encoded status object
        """
        parts = web.ctx.path.split('/')
        if parts[-2] == id:
            return http.uri_path()
        return http.extend_uri_path(id)

    # sync task methods -------------------------------------------------------

    def start_task(self,
                   func,
                   args=[],
                   kwargs={},
                   timeout=None,
                   unique=False):
        """
        Execute the function and its arguments as an asynchronous task.
        @param func: python callable
        @param args: positional arguments for func
        @param kwargs: key word arguments for func
        @return: dict representing the task
        """
        return async.run_async(func, args, kwargs, timeout, unique)

    def cancel_task(self, task):
        """
        Cancel the passed in task
        @type task: Task instance
        @param task: task to cancel
        @return: True if the task was successfully canceled, False otherwise
        """
        if task is None or task.state in task_complete_states:
            return False
        async.cancel_async(task)
        return True

    def task_status(self, id):
        """
        Get the current status of an asynchronous task.
        @param id: task id
        @return: TaskModel instance
        """
        task = self.find_task(id)
        if task is None:
            return None
        status = self._task_to_dict(task)
        status.update({'status_path': self._status_path(id)})
        return status

    def find_task(self, id):
        """
        Find and return a task with the given id
        @type id: str
        @param id: id of task to find
        @return: Task instance if a task with the id exists, None otherwise
        """
        tasks = async.find_async(id=id)
        if not tasks:
            return None
        return tasks[0]

    def timeout(self, data):
        """
        Parse any timeout values out of the passed in data
        @type data: dict
        @param data: values passed in via a request body
        @return: datetime.timedelta instance corresponding to a properly
                 formatted timeout value if found in data, None otherwise
        """
        timeout = data.get('timeout', None)
        if timeout is None:
            return None
        timeouts = {
            'days': lambda x: timedelta(days=x),
            'seconds': lambda x: timedelta(seconds=x),
            'microseconds': lambda x: timedelta(microseconds=x),
            'milliseconds': lambda x: timedelta(milliseconds=x),
            'minutes': lambda x: timedelta(minutes=x),
            'hours': lambda x: timedelta(hours=x),
            'weeks': lambda x: timedelta(weeks=x)
        }
        if timeout.find(':') < 0:
            return None
        units, length = timeout.split(':', 1)
        units = units.strip().lower()
        if units not in timeouts:
            return None
        try:
            length = int(length.strip())
        except ValueError:
            return None
        return timeouts[units](length)

    # http response methods ---------------------------------------------------

    def accepted(self, status):
        """
        Return an accepted response with status information in the body.
        @return: JSON encoded response
        """
        http.status_accepted()
        status.update({'status_path': self._status_path(status['id'])})
        return self._output(status)
