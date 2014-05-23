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

from pulp.server.content.sources.model import DownloadReport
from pulp_node.error import ErrorList

# --- utils -----------------------------------------------------------------------------


def key_and_repr(units):
    """
    Convert to list of unit_key and exception tuple into a list of
    tuple containing the unit_key and string representation of the
    exception.  This could just be done inline but more descriptive
    to wrap in a method.
    :param units: List of: (Unit, Exception)
    :type units: list
    :return: List of: (dict, str)
    :rtype: list
    """
    return [(u[0].unit_key, repr(u[1])) for u in units]


# --- reports ---------------------------------------------------------------------------


class SummaryReport(object):
    """
    A report that provides both summary and details regarding the importing
    of content units associated with a repository.
    :ivar errors: List of errors.
    :type errors: ErrorList
    :ivar sources: The content sources container statistics.
    :type sources: DownloadReport
    """

    def __init__(self):
        self.errors = ErrorList()
        self.sources = DownloadReport()

    def dict(self):
        """
        Dictionary representation.
        :return: A dictionary representation.
        :rtype: dict
        """
        return dict(errors=[e.dict() for e in self.errors], sources=self.sources.dict())


class ProgressListener(object):
    """
    Progress listener provides integration with plugin progress reporting facility.
    :ivar conduit: The importer conduit.
    :type  conduit: pulp.server.conduits.repo_sync.RepoSyncConduit
    """

    def __init__(self, conduit):
        """
        :param conduit: The importer conduit.
        :type  conduit: pulp.server.conduits.repo_sync.RepoSyncConduit
        """
        self.conduit = conduit

    def updated(self, report):
        """
        Send progress report using the conduit when the report is updated.
        """
        self.conduit.set_progress(report.dict())