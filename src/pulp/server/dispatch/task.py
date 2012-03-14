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

import copy
import datetime
import inspect
import logging
import sys
import time
import types
import uuid
from gettext import gettext as _

from pulp.common import dateutils
from pulp.server.db.model.dispatch import ArchivedCall
from pulp.server.dispatch import call
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.dispatch import exceptions as dispatch_exceptions
from pulp.server.dispatch import history as dispatch_history


_LOG = logging.getLogger(__name__)

# synchronous task -------------------------------------------------------------

class Task(object):
    """
    Task class
    Execution wrapper for a single call request
    @ivar id: unique uuid string
    @type id: str
    @ivar call_request: call request object task was created for
    @type call_request: CallRequest instance
    @ivar call_report: call report for the execution of the call_request
    @type call_report: CallReport instance
    @ivar queued_call_id: db id for serialized queued call
    @type queued_call_id: str
    @ivar complete_callback: task queue callback called on completion
    @type complete_callback: callable or None
    @ivar progress_callback: call request progress callback called to report execution progress
    @type progress_callback: callable or None
    @ivar blocking_tasks: set of task ids that block the execution of this task
    @type blocking_tasks: set
    """

    def __init__(self, call_request, call_report=None):

        assert isinstance(call_request, call.CallRequest)
        assert isinstance(call_report, (types.NoneType, call.CallReport))

        self.id = str(uuid.uuid1(clock_seq=int(time.time() * 1000)))

        self.call_request = call_request
        self.queued_call_id = None

        self.call_report = call_report or call.CallReport()
        self.call_report.state = dispatch_constants.CALL_WAITING_STATE
        self.call_report.task_id = self.id

        self.complete_callback = None
        self.blocking_tasks = set()

    def __str__(self):
        return 'Task %s: %s' % (self.id, str(self.call_request))

    def __eq__(self, other):
        if not isinstance(other, Task):
            raise TypeError('No comparison defined between task and %s' % type(other))
        return self.id == other.id

    # progress information -----------------------------------------------------

    def set_progress_callback(self, kwarg_name):
        """
        Set the call request progress callback as the given key word argument.
        @param kwarg_name: name of the key word argument
        @type  kwarg_name: str
        """
        spec = inspect.getargspec(self.call_request.call)
        if kwarg_name not in spec[0]:
            raise dispatch_exceptions.MissingProgressCallbackKeywordArgument(kwarg_name)
        self.call_request.kwargs[kwarg_name] = self._report_progress

    def _report_progress(self, progress):
        """
        Progress report callback
        """
        self.call_report.progress = progress

    # task lifecycle -----------------------------------------------------------

    def run(self):
        """
        Run the call request.
        """
        assert self.call_report.state in dispatch_constants.CALL_READY_STATES
        self.call_report.state = dispatch_constants.CALL_RUNNING_STATE
        self.call_report.start_time = datetime.datetime.now(dateutils.utc_tz())
        call = self.call_request.call
        args = copy.copy(self.call_request.args)
        kwargs = copy.copy(self.call_request.kwargs)
        try:
            result = call(*args, **kwargs)
        except:
            e, tb = sys.exc_info()[1:]
            _LOG.exception(e)
            return self._failed(e, tb)
        return self._succeeded(result)

    def _succeeded(self, result=None):
        """
        Mark the task completion as successful.
        @param result: result of the call
        @type  result: any
        """
        assert self.call_report.state is dispatch_constants.CALL_RUNNING_STATE
        self.call_report.result = result
        _LOG.info(_('%s SUCCEEDED') % str(self))
        self.call_execution_hooks(dispatch_constants.CALL_SUCCESS_LIFE_CYCLE_CALLBACK)
        self._complete(dispatch_constants.CALL_FINISHED_STATE)

    def _failed(self, exception=None, traceback=None):
        """
        Mark the task completion as a failure.
        @param exception: exception that occurred, if any
        @type  exception: Exception instance or None
        @param traceback: traceback information, if any
        @type  traceback: TracebackType instance
        """
        assert self.call_report.state is dispatch_constants.CALL_RUNNING_STATE
        self.call_report.exception = exception
        self.call_report.traceback = traceback
        _LOG.info(_('%s FAILED') % str(self))
        self.call_execution_hooks(dispatch_constants.CALL_FAILURE_LIFE_CYCLE_CALLBACK)
        self._complete(dispatch_constants.CALL_ERROR_STATE)

    def _complete(self, state=dispatch_constants.CALL_FINISHED_STATE):
        """
        Cleanup and state finalization for call on either success or failure.
        """
        assert state in dispatch_constants.CALL_COMPLETE_STATES
        self.call_report.finish_time = datetime.datetime.now(dateutils.utc_tz())
        self.call_execution_hooks(dispatch_constants.CALL_COMPLETE_LIFE_CYCLE_CALLBACK)
        self._call_complete_callback()
        # don't set the state to complete until the task is actually complete
        self.call_report.state = state
        if not self.call_request.archive:
            return
        # archive the completed call
        dispatch_history.archive_call(self.call_request, self.call_report)

    def _call_complete_callback(self):
        """
        Safely call the complete_callback, if there is one.
        """
        if self.complete_callback is None:
            return
        try:
            self.complete_callback(self)
        except Exception, e:
            _LOG.exception(e)

    # hook execution -----------------------------------------------------------

    def call_execution_hooks(self, key):
        """
        Execute all the execution hooks for the given key.
        Key must be a member of dispatch_constants.CALL_EXECUTION_HOOKS
        """
        assert key in dispatch_constants.CALL_LIFE_CYCLE_CALLBACKS
        for hook in self.call_request.execution_hooks[key]:
            hook(self.call_request, self.call_report)

    def cancel(self):
        """
        Call the cancel control hook if available, otherwise rains a
        NotImplemented exception.
        """
        if self.call_report.state in dispatch_constants.CALL_COMPLETE_STATES:
            return
        cancel_hook = self.call_request.control_hooks[dispatch_constants.CALL_CANCEL_CONTROL_HOOK]
        if cancel_hook is None:
            raise dispatch_exceptions.MissingCancelControlHook(str(self))
        cancel_hook(self.call_request, self.call_report)
        self.call_execution_hooks(dispatch_constants.CALL_CANCEL_LIFE_CYCLE_CALLBACK)
        self._complete(dispatch_constants.CALL_CANCELED_STATE)

# asynchronous task ------------------------------------------------------------

class AsyncTask(Task):
    """
    Task class whose control flow is not solely determined by the run method.
    Instead, the run method executes the call and passes in its _succeeded and
    _failed methods as key word callbacks to be called externally upon the
    task's success or failure.
    NOTE: failing to call one of these methods will result in the task failing
    to complete.
    """

    def set_success_failure_callback_kwargs(self,
                                            success_callback_kwarg_name,
                                            failure_callback_kwarg_name):
        """
        Set the success and failure callback keyword arguments to the task's
        _succeeded and _failed methods.
        """
        spec = inspect.getargspec(self.call_request.call)
        if success_callback_kwarg_name not in spec[0]:
            raise dispatch_exceptions.MissingSuccessCallbackKeywordArgument(success_callback_kwarg_name)
        if failure_callback_kwarg_name not in spec[0]:
            raise dispatch_exceptions.MissingFailureCallbackKeywordArgument(failure_callback_kwarg_name)
        self.call_request.kwargs[success_callback_kwarg_name] = self._succeeded
        self.call_request.kwargs[failure_callback_kwarg_name] = self._failed

    def run(self):
        """
        Run the call request
        """
        assert self.call_report.state in dispatch_constants.CALL_READY_STATES
        self.call_report.state = dispatch_constants.CALL_RUNNING_STATE
        self.call_report.start_time = datetime.datetime.now(dateutils.utc_tz())
        call = self.call_request.call
        args = copy.copy(self.call_request.args)
        kwargs = copy.copy(self.call_request.kwargs)
        # TODO check to see that the _succeeded and _failed callbacks were set
        try:
            return call(*args, **kwargs)
        except:
            # NOTE: this is making an assumption here that the call failed to
            # execute, if this isn't the case, or it got far enough, we may be
            # faced with _succeeded or _failed being called again
            e, tb = sys.exc_info()[1:]
            _LOG.exception(e)
            return self._failed(e, tb)

