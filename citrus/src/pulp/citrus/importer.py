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

from pulp.plugins.model import Unit
from pulp.server.config import config as pulp_conf
from pulp.citrus.manifest import Manifest
from pulp.citrus.progress import ProgressReport
from pulp.citrus.transport import DownloadTracker, DownloadRequest
from logging import getLogger


log = getLogger(__name__)


class Progress(ProgressReport):
    """
    Progress report provides integration between the
    citrus progress report and the plugin progress reporting facility.
    @ivar conduit: The importer conduit.
    @type  conduit: L{pulp.server.conduits.repo_sync.RepoSyncConduit}
    """

    def __init__(self, conduit):
        """
        @param conduit: The importer conduit.
        @type  conduit: L{pulp.server.conduits.repo_sync.RepoSyncConduit}
            """
        self.conduit = conduit
        ProgressReport.__init__(self)

    def _updated(self):
        """
        Send progress report using the conduit when the
        report is updated.
        """
        ProgressReport._updated(self)
        self.conduit.set_progress(self.dict())


class Report:
    """
    Final import report.
    @ivar added: List of added units by unit_key.
    @type added: list
    @ivar removed: List of removed units by unit_key.
    @type removed: list
    @ivar removed: List of failed units by unit_key.
    @type removed: list
    @ivar errors: List of error messages.
    @type errors: list
    """

    @staticmethod
    def units(units):
        if units:
            return [u.unit_key for u in units]
        else:
            return []

    def __init__(self, added=None, removed=None, failed=None, errors=None):
        """
        @param added: List of added units by unit_key.
        @type added: list
        @param removed: List of removed units by unit_key.
        @type removed: list
        @param removed: List of failed units by unit_key.
        @type removed: list
        @param errors: List of error messages.
        @type errors: list
        """
        self.added = Report.units(added)
        self.removed = Report.units(removed)
        self.failed = Report.units(failed)
        self.errors = errors or []

    def dict(self):
        """
        Dictionary representation.
        """
        return self.__dict__


class CitrusImporter:
    """
    Provides the generic synchronization behavior.
    @ivar cancelled: Indicates the current synchronization has been cancelled.
    @type cancelled: bool
    @ivar conduit: provides access to relevant Pulp functionality
    @type conduit: L{pulp.server.conduits.repo_sync.RepoSyncConduit}
    @ivar config: plugin configuration
    @type config: L{pulp.server.plugins.config.PluginCallConfiguration}
    @ivar transport: A transport object used to download files associated
        with content units.
    @type transport: object
    @ivar progress: A progress report object.
    @type progress: L{ImportProgress}
    """

    def __init__(self, conduit, config, transport):
        """
        @ivar cancelled: The flag indicating that the
            current operation has been cancelled.
        @type cancelled: bool
        @param conduit: provides access to relevant Pulp functionality
        @type conduit: L{pulp.server.conduits.repo_sync.RepoSyncConduit}
        @param config: plugin configuration
        @type config: L{pulp.server.plugins.config.PluginCallConfiguration}
        @param transport: A transport object used to download files
            associated with content units.
        @type transport: object
        """
        self.cancelled = False
        self.conduit = conduit
        self.config = config
        self.transport = transport
        self.progress = Progress(conduit)

    def synchronize(self, repo_id):
        """
        Synchronize content units associated with the repository.
        Performs the following:
          1. Read the (upstream) units.json
          2. Fetch the local (downstream) units associated with the repository.
          3. Add missing units.
          4. Delete units specified locally but not upstream.
        @param repo_id: The repository ID.
        @type repo_id: str
        @return: A synchronization report.
        @rtype: L{Report}
        """

        # fetch local units
        local_units = {}
        try:
            self.progress.push_step('fetch_local')
            units = self._local_units()
            local_units.update(units)
        except Exception, e:
            msg = 'Fetch local units failed for repository: %s' % repo_id
            log.exception(msg)
            self.progress.error(msg)
            return Report(errors=[msg])

        # fetch upstream units
        upstream_units = {}
        try:
            self.progress.push_step('fetch_upstream')
            units = self._upstream_units()
            upstream_units.update(units)
        except Exception, e:
            msg = 'Fetch local units failed for repository: %s' % repo_id
            log.exception(msg)
            self.progress.error(msg)
            return Report(errors=[msg])

        units_failed = []
        unit_inventory = UnitInventory(local_units, upstream_units)

        # add missing units
        units_added = []
        try:
            added, failed = self._add_units(unit_inventory)
            units_added.extend(added)
            if failed:
                units_failed.extend(failed)
                self.progress.set_status(ProgressReport.FAILED)
            else:
                self.progress.set_status(ProgressReport.SUCCEEDED)
        except Exception, e:
            msg = 'Add units failed on repository: %s' % repo_id
            log.exception(msg)
            self.progress.error(msg)
            return Report(errors=[msg])

        # purge extra units
        units_purged = []
        try:
            purged, failed = self._purge_units(unit_inventory)
            units_purged.extend(purged)
            if failed:
                units_failed.extend(failed)
                self.progress.set_status(ProgressReport.FAILED)
            else:
                self.progress.set_status(ProgressReport.SUCCEEDED)
        except Exception, e:
            msg = 'Purge units failed on repository: %s' % repo_id
            log.exception(msg)
            self.progress.error(msg)
            return Report(errors=[msg])

        return Report(units_added, units_purged, units_failed)

    def cancel(self):
        """
        Cancel the synchronization in progress.
        """
        self.cancelled = True
        self.transport.cancel()

    def _missing_units(self, unit_inventory):
        """
        Listing of units contained in the upstream inventory but
        not in the local inventory.
        @param unit_inventory: The inventory of content units.
        @type unit_inventory: L{UnitInventory}
        @return: The list of units to be added.
            Each item: (upstream_unit, new_unit)
        @rtype: list
        """
        new_units = []
        storage_dir = pulp_conf.get('server', 'storage_dir')
        for unit in unit_inventory.upstream_only():
            unit['metadata'].pop('_id')
            unit['metadata'].pop('_ns')
            type_id = unit['type_id']
            unit_key = unit['unit_key']
            metadata = unit['metadata']
            storage_path = unit.get('storage_path')
            if storage_path:
                relative_path = unit['_relative_path']
                storage_path = '/'.join((storage_dir, relative_path))
            unit_in = Unit(type_id, unit_key, metadata, storage_path)
            new_units.append((unit, unit_in))
        return new_units

    def _add_units(self, unit_inventory):
        """
        Download specified units.
        @param unit_inventory: The inventory of content units.
        @type unit_inventory: L{UnitInventory}
        @return: A tuple(2) of: (units_added, errors)
        @rtype: tuple
        """
        failed = []
        succeeded = []
        tracker = Tracker(self)
        units = self._missing_units(unit_inventory)
        self.progress.push_step('add_units', len(units))
        requests = []
        for unit, local_unit in units:
            if self.cancelled:
                return (succeeded, failed)
            download = unit.get('_download')
            if not download:
                try:
                    self._add_unit(local_unit)
                    succeeded.append(local_unit)
                except Exception, e:
                    failed.append((local_unit, e))
                continue
            request = DownloadRequest(tracker, unit, local_unit)
            requests.append(request)
        # download units
        self.transport.download(requests)
        succeeded.extend(tracker.get_succeeded())
        failed.extend(tracker.get_failed())
        return (succeeded, failed)

    def _add_unit(self, unit):
        """
        Add units inventoried upstream but not locally.
        @param unit: A unit to be added.
        @type unit: L{Unit}
        """
        self.conduit.save_unit(unit)
        self.progress.set_action('unit_added', str(unit.unit_key))

    def _purge_units(self, unit_inventory):
        """
        Purge units inventoried locally but not upstream.
        @param unit_inventory: The inventory of content units.
        @type unit_inventory: L{UnitInventory}
        @return: The tuple(2) of (purged, errors).
        @rtype: list
        """
        failed = []
        succeeded = []
        units = unit_inventory.local_only()
        self.progress.push_step('purge_units', len(units))
        for unit in units:
            try:
                self.progress.set_action('delete_unit', unit.unit_key)
                self.conduit.remove_unit(unit)
                succeeded.append(unit)
            except Exception, e:
                failed.append((unit, e))
        return (succeeded, failed)

    def _local_units(self):
        """
        Fetch all local units.
        @return: A dictionary of units keyed by L{UnitKey}.
        @rtype: dict
        """
        units = self.conduit.get_units()
        return self._unit_dictionary(units)

    def _upstream_units(self):
        """
        Fetch upstream units.
        @param repo_id: The repository ID.
        @type repo_id: str
        @return: A dictionary of units keyed by L{UnitKey}.
        @rtype: dict
        """
        url = self.config.get('manifest_url')
        manifest = Manifest()
        units = manifest.read(url)
        return self._unit_dictionary(units)

    def _unit_dictionary(self, units):
        """
        Construct a dictionary of units.
        @param units: A list of content units.
        @type units: list
        @return: A dictionary of units keyed by L{UnitKey}.
        @rtype: dict
        """
        items = [(UnitKey(u), u) for u in units]
        return dict(items)

    def cancel_sync_repo(self, call_request, call_report):
        pass


class UnitKey:
    """
    A unique unit key consisting of the unit's
    type_id & unit_key to be used in unit dictionaries.
    The unit key is sorted to ensure consistency.
    @ivar uid: The unique ID.
    @type uid: tuple
    """

    def __init__(self, unit):
        """
        @param unit: A content unit.
        @type unit: dict
        """
        if isinstance(unit, dict):
            type_id = unit['type_id']
            unit_key = tuple(sorted(unit['unit_key'].items()))
        else:
            type_id = unit.type_id
            unit_key = tuple(sorted(unit.unit_key.items()))
        self.uid = (type_id, unit_key)

    def __hash__(self):
        return hash(self.uid)

    def __eq__(self, other):
        return self.uid == other.uid

    def __ne__(self, other):
        return self.uid != other.uid


class UnitInventory:
    """
    Unit inventory.
    @ivar local: The dictionary of unit in the local inventory.
    @type local: dict
    @ivar upstream: The dictionary of unit in the upstream inventory.
    @type upstream: dict
    """

    def __init__(self, local, upstream):
        """
        @param local: The dictionary of unit in the local inventory.
        @type local: dict
        @param upstream: The dictionary of unit in the upstream inventory.
        @type upstream: dict
        """
        self.local = local
        self.upstream = upstream

    def upstream_only(self):
        """
        Listing of units contained in the upstream inventory
        but not not in the local inventory.
        @return: List of units that need to be added.
        @rtype: list
        """
        units = []
        for k, unit in self.upstream.items():
            if k not in self.local:
                units.append(unit)
        return units

    def local_only(self):
        """
        Listing of units contained in the local inventory
        but not not in the upstream inventory.
        @return: List of units that need to be purged.
        @rtype: list
        """
        units = []
        for k, unit in self.local.items():
            if k not in self.upstream:
                units.append(units)
        return units


class Tracker(DownloadTracker):
    """
    The unit download tracker.
    Maintains the list of succeeded and failed downloads.  Provides feedback
    to the importer so that progress can be reported and units added to the
    database based on the download success.
    @ivar _repository: The repository object.
    @type _repository: L{Importer}
    @ivar _succeeded: The list of downloaded units.
    @type _succeeded: list
    @ivar _failed: The list of failed units and exception raised.
    @type _failed: list
    """

    def __init__(self, repository):
        """
        @param repository: The importer object.
        @type repository: L{Repository}
        """
        self._repository = repository
        self._succeeded = []
        self._failed = []

    def succeeded(self, request):
        """
        Called when a download request succeeds.
        Add to succeeded list and notify the importer.
        @param request: The download request that succeeded.
        @type request: L{DownloadRequest}
        """
        unit = request.local_unit
        try:
            self._repository._add_unit(unit)
            self._succeeded.append(unit)
        except Exception, e:
            self._failed.append((unit, e))

    def failed(self, request, exception):
        """
        Called when a download request fails.
        Add to the failed list.
        @param request: The download request that failed.
        @type request: L{DownloadRequest}
        """
        unit = request.local_unit
        self._failed.append((unit, exception))

    def get_succeeded(self):
        """
        Get a list of successfully downloaded units.
        @return: List of successfully downloaded units.
        """
        return self._succeeded

    def get_failed(self):
        """
        Get a list of units that failed to download.
          Each item is: (unit, exception)
        @return: List of units that failed to download.
        """
        return self._failed