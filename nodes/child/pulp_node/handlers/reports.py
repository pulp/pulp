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

from pulp_node.progress import RepositoryProgress


class MergeReport(object):
    """
    Repository merge report.
    :ivar added: List of added repositories
        Each item is a repo_id.
    :type added: list
    :ivar merged: List of merged repositories.
        Each item is a repo_id.
    :type merged: list
    :ivar removed: List of removed repositories.
        Each item is a repo_id.
    :type removed: list
    """

    def __init__(self):
        self.added = []
        self.merged = []
        self.removed = []

    def dict(self):
        """
        Dictionary representation.
        :return: A dictionary representation.
        :rtype: dict
        """
        return self.__dict__


class HandlerReport(object):
    """
    Strategy synchronization() report.
    Aggregates the MergeReport and importer reports.
    :ivar errors: A list of error messages.
    :type errors: list
    :ivar merge_report: A repository merge report.
    :type merge_report: MergeReport
    """

    def __init__(self):
        self.errors = []
        self.merge_report = MergeReport()
        self.importer_reports = {}

    def dict(self):
        """
        Dictionary representation.
        :return: A dictionary representation.
        :rtype: dict
        """
        return dict(
            errors=self.errors,
            merge_report=self.merge_report.dict(),
            importer_reports=self.importer_reports)


class HandlerProgress(object):
    """
    The nodes handler progress report.
    Extends progress report base class to provide integration
    with the handler conduit.
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
        :raise KeyError
        """
        for p in self.progress:
            if p.repo_id == repo_id:
                return p
        raise KeyError(repo_id)

    def updated(self, report):
        """
        Notification that the report has been updated.
        Reported using the conduit.
        """
        for i in range(0, len(self.progress)):
            if self.progress[i].repo_id == report.repo_id:
                self.progress[i] = report
            self._updated()
            break

    def _updated(self):
        self.conduit.update_progress(self.dict())

    def dict(self):
        return dict(
            state=self.state,
            progress=[r.dict() for r in self.progress]
        )