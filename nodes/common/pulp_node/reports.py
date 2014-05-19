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

# --- summary reporting  -----------------------------------------------------


class RepositoryReport(object):
    """
    Repository merge report.
    :ivar repo_id: The repository ID.
    :type repo_id: str
    :ivar action: The action taken on the repository.
    :param action: str
    :ivar units: A content unit report.
    :type units: UnitReport
    :ivar sources: The content sources container statistics.
    :type sources: dict
    """

    # actions
    PENDING = 'pending'
    CANCELLED = 'cancelled'
    ADDED = 'added'
    MERGED = 'merged'
    DELETED = 'deleted'

    def __init__(self, repo_id, action=PENDING):
        """
        :param repo_id: The repository ID.
        :type repo_id: str
        :param action: The action taken on the repository.
        :param action: str
        """
        self.repo_id = repo_id
        self.action = action
        self.units = UnitReport()
        self.sources = {}

    def dict(self):
        """
        Dictionary representation.
        :return: A dictionary representation.
        :rtype: dict
        """
        return dict(
            repo_id=self.repo_id,
            action=self.action,
            units=self.units.dict(),
            sources=self.sources)


class UnitReport(object):
    """
    Content unit synchronization summary report.
    :ivar added: Count of units added.
    :type added: int
    :ivar updated: Count of units updated.
    :type updated: int
    :ivar removed: Count of units removed.
    :type removed: int
    """

    def __init__(self):
        self.added = 0
        self.updated = 0
        self.removed = 0

    def dict(self):
        """
        Dictionary representation.
        :return: A dictionary representation.
        :rtype: dict
        """
        return self.__dict__


# --- progress reporting  ----------------------------------------------------


class RepositoryProgress(object):
    """
    Tracks the progress of a repository in the pulp nodes synchronization process.
    """

    PENDING = 'pending'
    MERGING = 'merging'
    IMPORTING = 'import_started'
    DOWNLOADING_MANIFEST = 'downloading_manifest'
    ADDING_UNITS = 'adding_units'
    FINISHED = 'import_finished'

    def __init__(self, repo_id, listener=None):
        """
        :param repo_id: A repository ID.
        :type repo_id: str
        :param listener: Progress change listener.  An object that supports
            a method updated() with this object as a parameter.  The listener is
            is notified each time the report has changed.
        :type listener: object
        """
        self.repo_id = repo_id
        self.listener = listener
        self.state = self.PENDING
        self.unit_add = dict(total=0, completed=0, details=None)

    def begin_merging(self):
        """
        Update the report to reflect that merging has started.
        Set state=MERGING.
        """
        self.state = self.MERGING
        self.updated()

    def begin_importing(self):
        """
        Update the report to reflect that the importer has stared synchronizing.
        Set state=IMPORTING.
        """
        self.state = self.IMPORTING
        self.updated()

    def begin_manifest_download(self):
        """
        Update the report to reflect that the importer has started downloading the manifest.
        Set state=DOWNLOADING_MANIFEST.
        """
        self.state = self.DOWNLOADING_MANIFEST
        self.updated()

    def begin_adding_units(self, total):
        """
        Update the report to reflect that the importer has stared adding/downloading units.
        Set state=ADDING_UNITS.  Updates the total number of units expected to be added.
        :param total: The expected total number of units to be added.
        :type total: int
        """
        self.state = self.ADDING_UNITS
        self.unit_add['total'] = total
        self.updated()

    def unit_added(self, added=1, details=None):
        """
        Update the report to reflect that one or more units have been added.
        :param added: The number of units added since last reported.
        :type added: int
        :param details: Details (optional) about the unit added.
        :type details: object
        """
        self.unit_add['completed'] += added
        self.unit_add['details'] = details
        self.updated()

    def finished(self):
        """
        Update the report to reflect that the synchronization has finished.
        Set state=FINISHED.
        """
        self.state = self.FINISHED
        self.updated()

    def updated(self):
        """
        The report has changed.  Notify the listener.
        """
        if self.listener is not None:
            self.listener.updated(self)

    def dict(self):
        return dict(
            repo_id=self.repo_id,
            state=self.state,
            unit_add=self.unit_add
        )
