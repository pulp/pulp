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

from pulp.citrus.progress import ProgressReport


class MergeReport:
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


class HandlerReport:
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


class HandlerProgress(ProgressReport):
    """
    The citrus handler progress report.
    Extends progress report base class to provide integration
    with the handler conduit.
    """

    def __init__(self, conduit):
        """
        :param conduit: A handler conduit.
        :type conduit: pulp.agent.lib.conduit.Conduit
        """
        self.conduit = conduit
        ProgressReport.__init__(self)

    def _updated(self):
        """
        Notification that the report has been updated.
        Reported using the conduit.
        """
        ProgressReport._updated(self)
        self.conduit.update_progress(self.dict())