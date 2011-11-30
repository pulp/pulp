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

import datetime
import logging
import sys
import threading
import time
import uuid
from gettext import gettext as _

from pulp.common import dateutils
from pulp.server.dispatch import call


_LOG = logging.getLogger(__name__)

# synchronous task -------------------------------------------------------------

class Task(object):
    """
    Task class
    Execution wrapper for a single call request
    """

    def __init__(self, call_request):

        self.id = str(uuid.uuid1(clock_seq=int(time.time() * 1000)))

        self.call_request = call_request
        self.serialized_call_request_id = None

        for field in call_request.all_fields:
            value = getattr(call_request, field)
            setattr(self, field, value)

        self.state = call.CALL_WAITING

        self.start_time = None
        self.finish_time = None

        self.complete_callback = None
        self.progress_callback = None

        self.progress = None
        self.result = None
        self.exception = None
        self.traceback = None

    def __str__(self):
        return 'Task %s: %s' % (self.id, str(self.call_request))

    def __eq__(self, other):
        if not isinstance(other, Task):
            raise TypeError('No comparison defined between task and %s' % type(other))
        return self.id == other.id

    # progress information -----------------------------------------------------

    def set_progress(self, arg, callback):
        self.kwargs[arg] = self.progress_pass_through
        self.progress_callback = callback

    def progress_pass_through(self, *args, **kwargs):
        try:
            self.progress = self.progress_callback(*args, **kwargs)
        except Exception, e:
            _LOG.exception(e)
            raise

    # task lifecycle -----------------------------------------------------------

    def run(self):
        assert self.state in call.CALL_READY_STATES
        self.state = call.CALL_RUNNING
        self.start_time = datetime.datetime.now(dateutils.utc_tz())
        try:
            result = self.call(*self.args, **self.kwargs)
            self.initialize(result)
        except Exception, e:
            tb = sys.exc_info()[1]
            _LOG.exception(e)
            self.failed(e, tb)

    def initialize(self, result=None):
        self.succeeded(result)

    def succeeded(self, result):
        self.state = call.CALL_FINISHED
        self.result = result
        _LOG.info(_('%s SUCCEEDED') % str(self))
        self.finalize()

    def failed(self, exception=None, traceback=None):
        self.state = call.CALL_ERROR
        self.exception = exception
        self.traceback = traceback
        _LOG.info(_('%s FAILED') % str(self))
        self.finalize()

    def finalize(self):
        assert self.state in call.CALL_COMPLETE_STATES
        self.finish_time = datetime.datetime.now(dateutils.utc_tz())
        if self.complete_callback is None:
            return
        try:
            self.complete_callback(self)
        except Exception, e:
            _LOG.exception(e)

    # hook execution -----------------------------------------------------------

    def call_execution_hook(self, name):
        hook = self.execution_hooks(name, None)
        if hook is None:
            return None
        return hook(self)

    def call_control_hook(self, name):
        hook = self.control_hooks.get(name, None)
        if hook is None:
            raise NotImplementedError('No %s control hook provided' % name)
        return hook(self)

    def cancel(self):
        if self.state in call.CALL_COMPLETE_STATES:
            return
        self.call_control_hook('cancel')
        self.state = call.CALL_CANCELED
        self.finalize()

    # reporting ----------------------------------------------------------------

    def call_report(self):
        report = call.CallReport(state=self.state,
                                 task_id=self.id,
                                 progress=self.progress,
                                 result=self.result,
                                 exception=self.exception,
                                 traceback=self.traceback)
        return report

# asynchronous task ------------------------------------------------------------

class AsyncTask(Task):

    _current = threading.local()

    @classmethod
    def current(cls):
        return getattr(cls._current, 'task', None)

    def run(self):
        self._current.task = self
        try:
            super(AsyncTask, self).run()
        finally:
            self._current = None

    def initialize(self, result=None):
        pass
