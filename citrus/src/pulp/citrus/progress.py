# Copyright (c) 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from logging import getLogger

log = getLogger(__name__)


class ProgressReport:
    """
    Citrus synchronization progress reporting object.
    @ivar step: A list package steps.
        Each step is: (name, status)
    @type step: tuple
    @ivar details: Details about actions taking place
        in the current step.
    """

    PENDING = None
    SUCCEEDED = True
    FAILED = False

    def __init__(self):
        """
        Constructor.
        """
        self.steps = []
        self.details = {}

    def push_step(self, name):
        """
        Push the specified step.
        First, update the last status to SUCCEEDED.
        @param name: The step name to push.
        @type name: str
        """
        self.set_status(self.SUCCEEDED)
        self.steps.append([name, self.PENDING])
        self.details = {}
        self._updated()

    def set_status(self, status):
        """
        Update the status of the current step.
        @param status: The status.
        @type status: bool
        """
        if not self.steps:
            return
        last = self.steps[-1]
        if last[1] is self.PENDING:
            last[1] = status
            self.details = {}
            self._updated()

    def set_action(self, action, subject):
        """
        Set the specified package action for the current step.
        @param action: The action being performed.
        @type action: str
        @param subject: The subject of the action.
        @type subject: object
        """
        self.details = dict(action=action, subject=str(subject))
        self._updated()

    def error(self, msg):
        """
        Report an error on the current step.
        @param msg: The error message to report.
        @type msg: str
        """
        self.set_status(self.FAILED)
        self.details = dict(error=msg)
        self._updated()

    def _updated(self):
        """
        Notification that the report has been updated.
        Designed to be overridden and reported.
        """
        log.info('PROGRESS: %s %s', self.steps[-1:], self.details)
