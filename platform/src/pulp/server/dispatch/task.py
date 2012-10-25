# -*- coding: utf-8 -*-
#
# Copyright © 2011-2012 Red Hat, Inc.
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
import logging
import sys
import threading
import types
from gettext import gettext as _

from pulp.common import dateutils
from pulp.server.dispatch import call
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.dispatch import context as dispatch_context
from pulp.server.dispatch import exceptions as dispatch_exceptions
from pulp.server.dispatch import history as dispatch_history
from pulp.server.managers import factory as managers_factory


_LOG = logging.getLogger(__name__)

# synchronous task -------------------------------------------------------------

class Task(object):
    """
    Task class
    Execution wrapper for a single call request

    @ivar call_request: call request object task was created for
    @type call_request: L{call.CallRequest}
    @ivar call_report: call report for the execution of the call_request
    @type call_report: L{call.CallReport}
    @ivar call_request_exit_state: exit state of the call request used for conditional dependencies
    @type call_request_exit_state: None or str
    @ivar queued_call_id: db id for serialized queued call
    @type queued_call_id: str
    @ivar complete_callback: task queue callback called on completion
    @type complete_callback: callable or None
    @ivar progress_callback: call request progress callback called to report execution progress
    @type progress_callback: callable or None
    """

    def __init__(self, call_request, call_report=None):

        assert isinstance(call_request, call.CallRequest)
        assert isinstance(call_report, (types.NoneType, call.CallReport))

        self.call_request = call_request
        self.call_report = call_report or call.CallReport()

        self.call_request_exit_state = None
        self.queued_call_id = None
        self.complete_callback = None

        self.call_report.call_request_id = self.call_request.id
        self.call_report.call_request_group_id = self.call_request.group_id
        self.call_report.call_request_tags = self.call_request.tags
        self.call_report.principal_login = self.call_report.principal_login or self.call_request.principal and self.call_request.principal['login']
        self.call_report.state = dispatch_constants.CALL_WAITING_STATE

    def __str__(self):
        return 'Task %s: %s' % (self.call_request.id, str(self.call_request))

    def __eq__(self, other):
        if not isinstance(other, Task):
            raise TypeError('No comparison defined between task and %s' % type(other))
        return self.call_request.id == other.call_request.id

    # progress information -----------------------------------------------------

    def _report_progress(self, progress):
        """
        Progress report callback
        """
        self.call_report.progress = progress

    # task lifecycle -----------------------------------------------------------

    def skip(self):
        """
        Mark the task as skipped. Called *instead* of run.
        """
        assert self.call_report.state in dispatch_constants.CALL_READY_STATES
        self._complete(dispatch_constants.CALL_SKIPPED_STATE)

    def run(self):
        """
        Public wrapper to kick off the call in the call_request in a new thread.
        """
        assert self.call_report.state in dispatch_constants.CALL_READY_STATES
        # NOTE using run wrapper so that state transition is protected by the
        # task queue lock and doesn't occur in another thread
        self.call_report.state = dispatch_constants.CALL_RUNNING_STATE
        task_thread = threading.Thread(target=self._run)
        task_thread.start()
        # I'm fairly certain these will always be called *before* the context
        # switch to the task_thread
        self.call_life_cycle_callbacks(dispatch_constants.CALL_RUN_LIFE_CYCLE_CALLBACK)

    def _run(self):
        """
        Run the call in the call request.
        Generally the target of a new thread.
        """
        # used for calling _run directly during testing
        principal_manager = managers_factory.principal_manager()
        principal_manager.set_principal(self.call_request.principal)
        # generally set in the wrapper, but not when called directly
        if self.call_report.state in dispatch_constants.CALL_READY_STATES:
            self.call_report.state = dispatch_constants.CALL_RUNNING_STATE
        self.call_report.start_time = datetime.datetime.now(dateutils.utc_tz())
        dispatch_context.CONTEXT.set_task_attributes(self)
        call = self.call_request.call
        args = copy.copy(self.call_request.args)
        kwargs = copy.copy(self.call_request.kwargs)
        try:
            result = call(*args, **kwargs)
        except:
            e, tb = sys.exc_info()[1:]
            _LOG.exception(e)
            # to bad 2.4 doesn't support try/except/finally blocks
            principal_manager.clear_principal()
            dispatch_context.CONTEXT.clear_task_attributes()
            return self._failed(e, tb)
        principal_manager.clear_principal()
        dispatch_context.CONTEXT.clear_task_attributes()
        return self._succeeded(result)

    def _succeeded(self, result=None):
        """
        Mark the task completion as successful.
        @param result: result of the call
        @type  result: any
        """
        assert self.call_report.state is dispatch_constants.CALL_RUNNING_STATE
        self.call_report.result = result
        _LOG.info(_('SUCCESS: %(t)s') % {'t': str(self)})
        self.call_life_cycle_callbacks(dispatch_constants.CALL_SUCCESS_LIFE_CYCLE_CALLBACK)
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
        _LOG.info(_('FAILURE: %(t)s') % {'t': str(self)})
        self.call_life_cycle_callbacks(dispatch_constants.CALL_FAILURE_LIFE_CYCLE_CALLBACK)
        self._complete(dispatch_constants.CALL_ERROR_STATE)

    def _complete(self, state=dispatch_constants.CALL_FINISHED_STATE):
        """
        Cleanup and state finalization for call on either success or failure.
        """
        assert state in dispatch_constants.CALL_COMPLETE_STATES
        self.call_report.finish_time = datetime.datetime.now(dateutils.utc_tz())
        self.call_request_exit_state = state
        self._call_complete_callback()
        # don't set the state to complete in the report until the task is actually complete
        self.call_report.state = state
        self.call_life_cycle_callbacks(dispatch_constants.CALL_COMPLETE_LIFE_CYCLE_CALLBACK)
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

    # callback and hook execution ----------------------------------------------

    def call_life_cycle_callbacks(self, key):
        """
        Execute all the execution hooks for the given key.
        Key must be a member of dispatch_constants.CALL_EXECUTION_HOOKS
        """
        assert key in dispatch_constants.CALL_LIFE_CYCLE_CALLBACKS
        for hook in self.call_request.execution_hooks[key]:
            hook(self.call_request, self.call_report)

    def cancel(self):
        """
        Call the cancel control hook if available, otherwise raises a
        MissingCancelControlHook exception.

        NOTE that this method returns a "best effort" approach in that it will
        cancel the task if it hasn't yet run, will attempt to call the cancel
        control hook if the task is running, and simply return if the task has
        already completed.

        NOTE cancel life cycle callbacks are only executed if the task was
        actually cancelled (i.e. this method returns True)

        @return: None if the task had already completed, False if the task is
                 running but no control hook exists to interrupt it, True if the
                 task was cancelled
        @rtype:  bool or None
        """
        # XXX this method assumes that it is being called under the protection
        # of the task queue lock. If that is not the case, a race condition
        # occurs on the state of the task.

        # a complete task cannot be cancelled
        if self.call_report.state in dispatch_constants.CALL_COMPLETE_STATES:
            return None
        # to cancel a running task, the cancel control hook *must* be called
        if self.call_report.state == dispatch_constants.CALL_RUNNING_STATE:
            try:
                self._call_cancel_control_hook()
            except Exception, e:
                _LOG.exception(e)
                return False
        # nothing special needs to happen to cancel a task in a ready state
        self.call_life_cycle_callbacks(dispatch_constants.CALL_CANCEL_LIFE_CYCLE_CALLBACK)
        self._complete(dispatch_constants.CALL_CANCELED_STATE)
        return True

    def _call_cancel_control_hook(self):
        cancel_hook = self.call_request.control_hooks[dispatch_constants.CALL_CANCEL_CONTROL_HOOK]
        if cancel_hook is None:
            field = dispatch_constants.call_control_hook_to_string(dispatch_constants.CALL_CANCEL_CONTROL_HOOK)
            raise dispatch_exceptions.MissingCancelControlHook(field)
        # it is expected that this hook can and even will throw an exception
        # if this occurs, the task DID NOT CANCEL and should not proceed as if
        # it has
        cancel_hook(self.call_request, self.call_report)

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

    def _run(self):
        """
        Run the call in the call request.
        Generally the target of a new thread.
        """
        # used for calling _run directly during testing
        principal_manager = managers_factory.principal_manager()
        principal_manager.set_principal(self.call_request.principal)
        # usually set in the wrapper, unless called directly
        if self.call_report.state in dispatch_constants.CALL_READY_STATES:
            self.call_report.state = dispatch_constants.CALL_RUNNING_STATE
        self.call_report.start_time = datetime.datetime.now(dateutils.utc_tz())
        dispatch_context.CONTEXT.set_task_attributes(self)
        call = self.call_request.call
        args = copy.copy(self.call_request.args)
        kwargs = copy.copy(self.call_request.kwargs)
        try:
            result = call(*args, **kwargs)
        except:
            # NOTE: this is making an assumption here that the call failed to
            # execute, if this isn't the case, or it got far enough, we may be
            # faced with _succeeded or _failed being called again
            e, tb = sys.exc_info()[1:]
            _LOG.exception(e)
            # too bad 2.4 doesn't support try/except/finally blocks
            principal_manager.clear_principal()
            dispatch_context.CONTEXT.clear_task_attributes()
            return self._failed(e, tb)
        principal_manager.clear_principal()
        dispatch_context.CONTEXT.clear_task_attributes()
        return result

