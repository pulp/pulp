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


from pulp_node.progress import ProgressReport

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


class ImporterReport(object):
    """
    A report that provides both summary and details regarding the importing
    of content units associated with a repository.
    :ivar add_failed: List of units that failed to be added.
        Each item is: (Unit, Exception)
    :type add_failed: list
    :ivar delete_failed: List of units that failed to be deleted.
        Each item is: (Unit, Exception)
    :type delete_failed: list
    """

    def __init__(self, add_failed, delete_failed):
        """
        :param add_failed: List of units that failed to be added.
            Each item is: (Unit, Exception)
        :type add_failed: list
        :param delete_failed: List of units that failed to be deleted.
            Each item is: (Unit, Exception)
        :type delete_failed: list
        """
        self.add_failed = key_and_repr(add_failed)
        self.delete_failed = key_and_repr(delete_failed)
        self.succeeded = not (self.add_failed or self.delete_failed)

    def dict(self):
        """
        Get a dictionary representation.
        """
        return self.__dict__


class ImporterProgress(ProgressReport):
    """
    Progress report provides integration between the nodes progress
    report and the plugin progress reporting facility.
    :ivar conduit: The importer conduit.
    :type  conduit: pulp.server.conduits.repo_sync.RepoSyncConduit
    """

    def __init__(self, conduit):
        """
        :param conduit: The importer conduit.
        :type  conduit: pulp.server.conduits.repo_sync.RepoSyncConduit
            """
        self.conduit = conduit
        ProgressReport.__init__(self)

    def _updated(self):
        """
        Send progress report using the conduit when the report is updated.
        """
        ProgressReport._updated(self)
        self.conduit.set_progress(self.dict())