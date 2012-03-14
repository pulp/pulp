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
from gettext import gettext as _
from pprint import pformat
from threading import local


_LOG = logging.getLogger(__name__)

# context class ----------------------------------------------------------------

class Context(local):
    """
    Dispatch thread-local store, making pertinent information and calls
    available to calls being executed within a dispatch task.
    @ivar task_id: unique id of the task executing the call
    @type task_id: str or None
    @ivar job_id: unique id of the job the task is part of
    @type job_id: str or None
    @ivar report_progress: callback to pass progress information into
    @type report_progress: callable
    @ivar succeeded: callback to report success from an asynchronous call
    @type succeeded: callable
    @ivar failed: callback to report failure from an asynchronous call
    @type failed: callable
    """

    def __init__(self):
        super(Context, self).__init__()
        self.clear_task_attributes()

    def set_task_attributes(self, task):
        self.task_id = task.id
        self.job_id = task.call_report.job_id
        self.report_progress = task._report_progress
        if task.call_request.asynchronous:
            self.succeeded = task._succeeded
            self.failed = task._failed

    def clear_task_attributes(self):
        self.task_id = None
        self.job_id = None
        self.report_progress = self._report_progress
        self.succeeded = self._succeeded
        self.failed = self._failed

    def _report_progress(self, progress):
        msg = _('report_progress called on cleared dispatch context: %(p)s')
        _LOG.error(msg % {'p': pformat(progress)})

    def _succeeded(self, result=None):
        msg = _('succeeded called on cleared dispatch context: %(r)s')
        _LOG.critical(msg % {'r': pformat(result)})

    def _failed(self, exception=None, traceback=None):
        msg = _('failed called on cleared dispatch context: %(e)s, %(t)s')
        _LOG.critical(msg % {'e': pformat(exception), 't': pformat(traceback)})

# context factory --------------------------------------------------------------
# NOTE this is here and not in the factory module to prevent circular imports

_CONTEXT = None


def initialize():
    global _CONTEXT
    assert _CONTEXT is None
    _CONTEXT = Context()


def context():
    assert isinstance(_CONTEXT, Context)
    return _CONTEXT
