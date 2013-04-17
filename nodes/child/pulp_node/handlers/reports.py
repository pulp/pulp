# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from pulp_node.reports import RepositoryReport, RepositoryProgress
from pulp_node.error import ErrorList


# --- summary reporting  -----------------------------------------------------


class SummaryReport(object):
    """
    Node synchronization summary report.
    :ivar errors: A list of error messages.
    :type errors: list
    :ivar repository: A dictionary of RepositoryReport keyed by repo_id.
    :type repository: dict
    """

    def __init__(self):
        self.errors = ErrorList()
        self.repository = {}

    def setup(self, bindings):
        """
        Setup (prime) the report using the specified bindings.
        A RepositoryReport is created for each repository referenced in the bindings.
        :param bindings:
        :return:
        """
        for bind in bindings:
            repo_id = bind['repo_id']
            self.repository[repo_id] = RepositoryReport(repo_id)

    def succeeded(self):
        """
        Get whether the update succeeded (or not).
        :return: True if succeeded.
        :rtype: bool
        """
        return not self.failed()

    def failed(self):
        """
        Get whether the update failed (or not).
        :return: True if failed.
        :rtype: bool
        """
        return len(self.errors) > 0

    def dict(self):
        """
        Dictionary representation.
        :return: A dictionary representation.
        :rtype: dict
        """
        return dict(
            errors=[e.dict() for e in self.errors],
            repositories=[r.dict() for r in self.repository.values()])

    def __getitem__(self, repo_id):
        return self.repository[repo_id]

    def __setitem__(self, repo_id, report):
        self.repository[repo_id] = report


# --- progress reporting  ----------------------------------------------------


class HandlerProgress(object):
    """
    The nodes handler progress report.
    :ivar conduit: A handler conduit.
    :type conduit: pulp.agent.lib.conduit.Conduit
    :ivar state: The current state of the synchronization.
    :type state: str
    :ivar progress: A list of RepositoryProgress reports.
    :type progress: list
    """

    PENDING = 'pending'
    STARTED = 'in-progress'
    FINISHED = 'finished'

    def __init__(self, conduit):
        """
        :param conduit: A handler conduit.
        :type conduit: pulp.agent.lib.conduit.Conduit
        """
        self.conduit = conduit
        self.state = self.PENDING
        self.progress = []

    def started(self, bindings):
        """
        Indicate the handler synchronization has started.
        State set to: STARTED.
        :param bindings: List of bindings used to populate the report.
        :type bindings: list
        """
        self.state = self.STARTED
        for bind in bindings:
            repo_id = bind['repo_id']
            p = RepositoryProgress(repo_id, self)
            self.progress.append(p)
        self._updated()

    def finished(self):
        """
        Indicate the handler synchronization has finished.
        State set to: FINISHED.
        """
        self.state = self.FINISHED
        self._updated()

    def find_report(self, repo_id):
        """
        Find a repository report by ID.
        :param repo_id: A repository ID.
        :type repo_id: str
        :return The report if found.
        :rtype RepositoryProgress
        :raise ValueError
        """
        for p in self.progress:
            if p.repo_id == repo_id:
                return p
        raise ValueError(repo_id)

    def updated(self, report):
        """
        Update the progress associated with a specific repository by repo_id.
        :param report: The update repository progress report.
        :type report: RepositoryProgress
        """
        for i, p in enumerate(self.progress):
            if p.repo_id == report.repo_id:
                self.progress[i] = report
            self._updated()
            break

    def _updated(self):
        """
        Notification that the report has been updated.
        Reported using the conduit.
        """
        self.conduit.update_progress(self.dict())

    def dict(self):
        return dict(
            state=self.state,
            progress=[r.dict() for r in self.progress]
        )