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
    @ivar task_group_id: unique id of the task_group the task is part of
    @type task_group_id: str or None
    @ivar report_progress: callback to pass progress information into
    @type report_progress: callable
    """

    def __init__(self):
        super(Context, self).__init__()
        self.clear_task_attributes()

    def set_task_attributes(self, task):
        self.task_id = task.id
        self.task_group_id = task.call_report.task_group_id
        self.report_progress = task._report_progress

    def clear_task_attributes(self):
        self.task_id = None
        self.task_group_id = None
        self.report_progress = self._report_progress

    def _report_progress(self, progress):
        msg = _('report_progress called on cleared dispatch context: %(p)s')
        _LOG.debug(msg % {'p': pformat(progress)})

# context global ---------------------------------------------------------------
# NOTE this is here and not in the factory module to prevent circular imports

# NOTE this is not initialized by a method as each thread needs to call __init__
CONTEXT = Context()
