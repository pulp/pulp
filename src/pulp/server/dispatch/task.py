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
import logging
import sys
import time
import types
import uuid
from gettext import gettext as _

from pulp.common import dateutils
from pulp.server.dispatch import call
from pulp.server.dispatch import constants as dispatch_constants


_LOG = logging.getLogger(__name__)

# synchronous task -------------------------------------------------------------

class Task(object):
    """
    Task class
    Execution wrapper for a single call request
    """

    def __init__(self, call_request, call_report=None, asynchronous=False):

        assert isinstance(call_request, call.CallRequest)
        assert isinstance(call_report, (types.NoneType, call.CallReport))
        assert isinstance(asynchronous, types.BooleanType)

        self.id = str(uuid.uuid1(clock_seq=int(time.time() * 1000)))

        self.call_request = call_request
        self.serialized_call_request_id = None

        self.call_report = call_report or call.CallReport()
        self.call_report.state = dispatch_constants.CALL_WAITING_STATE
        self.call_report.task_id = self.id

        self.asynchronous = asynchronous

        self.complete_callback = None
        self.progress_callback = None

    def __str__(self):
        return 'Task %s: %s' % (self.id, str(self.call_request))

    def __eq__(self, other):
        if not isinstance(other, Task):
            raise TypeError('No comparison defined between task and %s' % type(other))
        return self.id == other.id

    # progress information -----------------------------------------------------

    def set_progress(self, arg, callback):
        self.call_request.kwargs[arg] = self._progress_pass_through
        self.progress_callback = callback

    def _progress_pass_through(self, *args, **kwargs):
        try:
            self.call_report.progress = self.progress_callback(*args, **kwargs)
        except Exception, e:
            _LOG.exception(e)
            raise

    # task lifecycle -----------------------------------------------------------

    def run(self):
        assert self.call_report.state in dispatch_constants.CALL_READY_STATES
        self.call_report.state = dispatch_constants.CALL_RUNNING_STATE
        self.call_report.start_time = datetime.datetime.now(dateutils.utc_tz())
        call = self.call_request.call
        args = copy.copy(self.call_request.args)
        kwargs = copy.copy(self.call_request.kwargs)
        result = None
        if self.asynchronous:
            kwargs['task'] = self
        try:
            result = call(*args, **kwargs)
        except Exception, e:
            tb = sys.exc_info()[1]
            _LOG.exception(e)
            self.failed(e, tb)
        if self.asynchronous:
            return
        self.succeeded(result)

    def succeeded(self, result):
        self.call_report.state = dispatch_constants.CALL_FINISHED_STATE
        self.call_report.result = result
        _LOG.info(_('%s SUCCEEDED') % str(self))
        self._complete()

    def failed(self, exception=None, traceback=None):
        self.call_report.state = dispatch_constants.CALL_ERROR_STATE
        self.call_report.exception = exception
        self.call_report.traceback = traceback
        _LOG.info(_('%s FAILED') % str(self))
        self._complete()

    def _complete(self):
        assert self.call_report.state in dispatch_constants.CALL_COMPLETE_STATES
        self.call_report.finish_time = datetime.datetime.now(dateutils.utc_tz())
        if self.complete_callback is None:
            return
        try:
            self.complete_callback(self)
        except Exception, e:
            _LOG.exception(e)

    # hook execution -----------------------------------------------------------

    def call_execution_hooks(self, key):
        for hook in self.call_request.execution_hooks[key]:
            hook(self.call_request, self.call_report)

    def cancel(self):
        if self.call_report.state in dispatch_constants.CALL_COMPLETE_STATES:
            return
        cancel_hook = self.call_request.control_hooks[dispatch_constants.CALL_CANCEL_CONTROL_HOOK]
        if cancel_hook is None:
            raise NotImplementedError('No cancel control hook provided for Task:%s' % self.id)
        cancel_hook(self.call_request, self.call_report)
        self.call_report.state = dispatch_constants.CALL_CANCELED_STATE
        self._complete()

