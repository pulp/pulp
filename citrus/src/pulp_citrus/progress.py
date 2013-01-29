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
    Represents a progress report.
    :ivar step: A list package steps.
        Each step is: [name, status, num_actions]
          name - the name of the step.
          status - the status of the step.
          action_ratio - a tuple (<completed>, <total>) representing
            the ratio of complete and total actions to included in a step.
    :type step: tuple
    :ivar details: Details about actions taking place
        in the current step.
    :cvar PENDING: The step is pending.
    :cvar SUCCEEDED: The step is finished and succeeded.
    :cvar FAILED: The step is finished and failed.
    """

    PENDING = None
    SUCCEEDED = True
    FAILED = False

    def __init__(self, parent=None):
        """
        :param parent: An optional parent report.
        :type parent: ProgressReport
        """
        self.steps = []
        self.action = {}
        self.nested_report = None
        self.parent = parent
        if parent:
            parent.nested_report = self

    def push_step(self, name, total_actions=0):
        """
        Push the specified step.
        First, update the last status to SUCCEEDED.
        :param name: The step name to push.
        :type name: str
        :param total_actions: Number of anticipated actions to complete the step.
        :type total_actions: int
        """
        self.set_status(self.SUCCEEDED)
        self.steps.append([name, self.PENDING, [0, total_actions]])
        self.action = {}
        self.nested_report = None
        self._updated()

    def set_status(self, status):
        """
        Update the status of the current step.
        :param status: The status.
        :type status: bool
        """
        if not self.steps:
            return
        last = self.current_step()
        if last[1] is self.PENDING:
            last[1] = status
            self.action = {}
            self.nested_report = None
            self._updated()

    def set_action(self, action, subject):
        """
        Set the specified package action for the current step.  If the action_ratio
        has been specified, update the number of completed actions.
        Reminder: action_ratio is a tuple of (<completed>/<total>) actions.
        representation of a nested ProgressReport.
        :param action: The action being performed.
        :type action: str
        :param subject: The subject of the action.
        :type subject: object
        """
        action_ratio = self.current_step()[2]
        if action_ratio[0] < action_ratio[1]:
            action_ratio[0] += 1
        self.action = dict(action=action, subject=subject)
        self._updated()

    def set_nested_report(self, report):
        """
        Set the nested progress report for the current step.
        :param report: A progress report
        :type report: ProgressReport
        """
        report.parent = self
        self.nested_report = report
        self._updated()

    def error(self, msg):
        """
        Report an error on the current step.
        :param msg: The error message to report.
        :type msg: str
        """
        self.set_status(self.FAILED)
        self.action = dict(error=msg)
        self._updated()

    def end(self):
        """
        End progress reporting.
        """
        self.set_status(self.SUCCEEDED)

    def current_step(self):
        """
        Get the current step.
        :return: The current step: [name, status, action_ratio]
        :rtype: list
        """
        return self.steps[-1]

    def dict(self):
        """
        Dictionary representation.
        :return: self as a dictionary.
        :rtype: dict
        """
        if self.nested_report:
            nested_report = self.nested_report.dict()
        else:
            nested_report = {}
        return dict(steps=self.steps, action=self.action, nested_report=nested_report)

    def _updated(self):
        """
        Notification that the report has been updated.
        Designed to be overridden and reported.
        """
        if self.parent:
            self.parent._updated()
        else:
            log.debug('PROGRESS: %s', self.dict())
