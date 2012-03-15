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

import datetime
import os
import sys
import traceback
import types

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + '/../common/')

import mock
import testutil

from pulp.common import dateutils
from pulp.server.db.model.dispatch import ArchivedCall
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.dispatch import exceptions as dispatch_exceptions
from pulp.server.dispatch.call import CallReport, CallRequest
from pulp.server.dispatch.task import AsyncTask, Task

# testing data -----------------------------------------------------------------

call_args = (1, 2, 3)
call_kwargs = {'a': 'foo', 'b': 'bar', 'c': 'baz'}

class Call(mock.Mock):
    # required for tests that cast call to str
    __name__ = 'Call'
    call = mock.Mock.__call__

def fail():
    raise RuntimeError('fail')

def call_without_callbacks():
    pass

def call_with_progress_callback(progress_callback=None):
    pass

def call_with_success_callback(success_callback=None):
    pass

def call_with_failure_callback(failure_callback=None):
    pass

def call_with_success_and_failure_callbacks(success_callback=None, failure_callback=None):
    pass

# task instance testing --------------------------------------------------------

class TaskInstanceTests(testutil.PulpTest):

    def test_task_instantiation(self):
        call_request = CallRequest(mock.Mock())
        call_report = CallReport()
        try:
            Task(call_request)
            Task(call_request, call_report)
        except:
            self.fail(traceback.format_exc())

    def test_str(self):
        call = Call()
        call_request = CallRequest(call.call, call_args, call_kwargs)
        task = Task(call_request)
        try:
            str(task)
        except:
            self.fail(traceback.format_exc())

    def test_eq(self):
        call_request = CallRequest(mock.Mock())
        task_1 = Task(call_request)
        task_2 = Task(call_request)
        self.assertTrue(task_1 == task_1)
        self.assertFalse(task_1 == task_2)

# task testing -----------------------------------------------------------------

class TaskTests(testutil.PulpTest):

    def setUp(self):
        super(TaskTests, self).setUp()
        self.call_request = CallRequest(Call(), call_args, call_kwargs)
        self.call_report = CallReport()
        self.task = Task(self.call_request, self.call_report)

    def tearDown(self):
        super(TaskTests, self).tearDown()
        self.call_request = None
        self.call_report = None
        self.task = None

    def test_run(self):
        self.assertTrue(self.call_report.state is dispatch_constants.CALL_WAITING_STATE)
        self.task.run()
        self.assertTrue(self.call_request.call.call_count == 1)
        self.assertTrue(self.call_request.call.call_args[0] == call_args,
                        '%s != %s' % (str(self.call_request.call.call_args[0]), str(call_args)))
        self.assertTrue(self.call_request.call.call_args[1] == call_kwargs)
        self.assertTrue(self.call_report.state is dispatch_constants.CALL_FINISHED_STATE)

    def test_complete(self):
        now = datetime.datetime.now(dateutils.utc_tz())
        self.task.run()
        self.assertTrue(self.call_report.finish_time > now)

    def test_complete_callback(self):
        callback = mock.Mock()
        self.task.complete_callback = callback
        self.task.run()
        self.assertTrue(callback.call_count == 1)
        self.assertTrue(callback.call_args[0][0] is self.task)

    def test_cancel_control_hook(self):
        callback = mock.Mock()
        self.call_request.add_control_hook(dispatch_constants.CALL_CANCEL_CONTROL_HOOK, callback)
        try:
            self.task.cancel()
        except:
            self.fail(traceback.format_exc())
        self.assertTrue(callback.call_count == 1)
        self.assertTrue(callback.call_args[0][0] is self.call_request)
        self.assertTrue(callback.call_args[0][1] is self.call_report)
        self.assertTrue(self.call_report.state is dispatch_constants.CALL_CANCELED_STATE,
                        self.call_report.state)

    def test_finish_execution_hook(self):
        hooks = [mock.Mock(), mock.Mock()]
        for h in hooks:
            self.call_request.add_life_cycle_callback(dispatch_constants.CALL_SUCCESS_LIFE_CYCLE_CALLBACK, h)
        self.task.run()
        for h in hooks:
            self.assertTrue(h.call_count == 1)
            self.assertTrue(h.call_args[0][0] is self.call_request)
            self.assertTrue(h.call_args[0][1] is self.call_report)

    def test_complete_execution_hook(self):
        hooks = [mock.Mock(), mock.Mock()]
        for h in hooks:
            self.call_request.add_life_cycle_callback(dispatch_constants.CALL_COMPLETE_LIFE_CYCLE_CALLBACK, h)
        self.task.run()
        for h in hooks:
            self.assertTrue(h.call_count == 1)

# run failure testing ----------------------------------------------------------

class FailTests(testutil.PulpTest):

    def setUp(self):
        self.call_request = CallRequest(fail)
        self.call_report = CallReport()
        self.task = Task(self.call_request, self.call_report)

    def tearDown(self):
        self.call_request = None
        self.call_report = None
        self.task = None

    def test_failed(self):
        self.task.run()
        self.assertTrue(self.call_report.state is dispatch_constants.CALL_ERROR_STATE,
                        self.call_report.state)
        self.assertTrue(isinstance(self.call_report.exception, RuntimeError),
                        str(type(self.call_report.exception)))
        self.assertTrue(isinstance(self.call_report.traceback, types.TracebackType))

    def test_error_execution_hook(self):
        hook = mock.Mock()
        self.call_request.add_life_cycle_callback(dispatch_constants.CALL_FAILURE_LIFE_CYCLE_CALLBACK, hook)
        self.task.run()
        self.assertTrue(hook.call_count == 1)
        self.assertTrue(hook.call_args[0][0] is self.call_request)
        self.assertTrue(hook.call_args[0][1] is self.call_report)

# async task testing -----------------------------------------------------------

class AsyncTaskTests(testutil.PulpTest):

    def setUp(self):
        self.call_request = CallRequest(Call(), call_args, call_kwargs)
        self.call_report = CallReport()
        self.task = AsyncTask(self.call_request, self.call_report)

    def tearDown(self):
        self.call_request = None
        self.call_report = None
        self.task = None

    def test_run(self):
        self.task.run()
        self.assertTrue(self.call_report.state is dispatch_constants.CALL_RUNNING_STATE)

    def test_succeeded(self):
        self.assertRaises(AssertionError, self.task._succeeded, None)
        self.task.run()
        self.task._succeeded(None)
        self.assertTrue(self.call_report.state is dispatch_constants.CALL_FINISHED_STATE)

    def test_failed(self):
        self.assertRaises(AssertionError, self.task._failed, None)
        self.task.run()
        self.task._failed()
        self.assertTrue(self.call_report.state is dispatch_constants.CALL_ERROR_STATE)

# task archival tests ----------------------------------------------------------

class TaskArchivalTests(testutil.PulpTest):

    def tearDown(self):
        super(TaskArchivalTests, self).tearDown()
        ArchivedCall.get_collection().drop()

    def test_task_archival(self):
        task = Task(CallRequest(call_without_callbacks, archive=True))
        try:
            task.run()
        except:
            self.fail(traceback.format_exc())
        collection = ArchivedCall.get_collection()
        archived_call = collection.find_one({'serialized_call_report.task_id': task.id})
        self.assertFalse(archived_call is None)

