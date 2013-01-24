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

"""
Provides classes that implement unit synchronization strategies.
Citrus importer plugins delegate synchronization to one of
the strategies provided here.
"""


from gettext import gettext as _
from pulp.plugins.model import Unit
from pulp.server.config import config as pulp_conf
from pulp.citrus.manifest import Manifest
from pulp.citrus.progress import ProgressReport
from pulp.citrus.transport import DownloadTracker, DownloadRequest
from logging import getLogger


log = getLogger(__name__)


# --- Import Strategies -----------------------------------------------------------------


class Strategy:
    """
    This object provides the transport independent content unit synchronization
    strategy used by citrus importer plugins.
    @ivar cancelled: The flag indicating that the current operation
        has been cancelled.
    @type cancelled: bool
    @ivar conduit: Provides access to relevant Pulp functionality
    @type conduit: L{pulp.server.conduits.repo_sync.RepoSyncConduit}
    @ivar config: The plugin configuration.
    @type config: L{pulp.server.plugins.config.PluginCallConfiguration}
    @ivar transport: A transport fully configured object used to download files.
    @type transport: object
    @ivar progress: A progress reporting object.
    @type progress: L{Progress}
    """

    def __init__(self, conduit, config, transport):
        """
        @ivar cancelled: The flag indicating that the current operation
            has been cancelled.
        @type cancelled: bool
        @param conduit: Provides access to relevant Pulp functionality.
        @type conduit: L{pulp.server.conduits.repo_sync.RepoSyncConduit}
        @param config: The plugin configuration.
        @type config: L{pulp.server.plugins.config.PluginCallConfiguration}
        @param transport: A fully configured transport object used to download files.
        @type transport: object
        """
        self.cancelled = False
        self.conduit = conduit
        self.config = config
        self.transport = transport
        self.progress = Progress(conduit)

    def synchronize(self, repo_id):
        """
        Synchronize the content units associated with the specified repository.
        Specific strategies defined by subclasses.
        @param repo_id: The repository ID.
        @type repo_id: str
        @return: A synchronization report.
        @rtype: L{Report}
        """
        raise NotImplementedError()

    def cancel(self):
        """
        Cancel the synchronization in progress.
        """
        self.cancelled = True
        self.transport.cancel()

    def add_unit(self, unit):
        """
        Add the specified unit to the local inventory using the conduit.
        The conduit will automatically associate the unit to the repository
        to which it's pre-configured.
        @param unit: The unit to be added.
        @type unit: L{Unit}
        """
        self.conduit.save_unit(unit)
        self.progress.set_action('unit_added', str(unit.unit_key))

    def _unit_inventory(self, repo_id):
        """
        Build the unit inventory.
        @param repo_id: A repository ID.
        @rtype repo_id: str
        @return: The built inventory.
        @rtype: L{UnitInventory}
        """
        # fetch local units
        local = {}
        try:
            self.progress.push_step('fetch_local')
            units = self._units_local()
            local.update(units)
            self.progress.set_status(Progress.SUCCEEDED)
        except Exception:
            msg = _('Fetch local units failed for repository: %(r)s')
            msg = msg % {'r':repo_id}
            log.exception(msg)
            self.progress.error(msg)
            raise Exception(msg)
        # fetch upstream units
        upstream = {}
        try:
            self.progress.push_step('fetch_upstream')
            units = self._units_upstream()
            upstream.update(units)
            self.progress.set_status(Progress.SUCCEEDED)
        except Exception:
            msg = _('Fetch local units failed for repository: %(r)s')
            msg = msg % {'r':repo_id}
            log.exception(msg)
            self.progress.error(msg)
            raise Exception(msg)
        return UnitInventory(local, upstream)

    def _missing_units(self, unit_inventory):
        """
        Determine the list of units defined upstream inventory that are
        not in the local inventory.
        @param unit_inventory: The inventory of both upstream and local content units.
        @type unit_inventory: L{UnitInventory}
        @return: The list of units to be added.
            Each item: (unit_upstream, unit_to_be_added)
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
        Determine the list of units contained in the upstream inventory
        but are not contained in the local inventory and add them.
        For each unit, this is performed in the following steps:
          1. Download the file (if defined) associated with the unit.
          2. Add the unit to the local inventory.
          3. Associate the unit to the repository.
        The unit is added only:
          1. If no file is associated with unit.
          2. The file associated with the unit is successfully downloaded.
        For units with files, the unit is added to the inventory as part of the
        transport callback.
        @param unit_inventory: The inventory of both upstream and local content units.
        @type unit_inventory: L{UnitInventory}
        @return: The list of failed that failed to be added.
            Each item is: (unit, exception)
        @rtype: list
        """
        failed = []
        tracker = Tracker(self)
        units = self._missing_units(unit_inventory)
        self.progress.push_step('add_units', len(units))
        requests = []
        for unit, local_unit in units:
            if self.cancelled:
                return failed
            download = unit.get('_download')
            # unit has no file associated
            if not download:
                try:
                    self.add_unit(local_unit)
                except Exception, e:
                    failed.append((local_unit, e))
                continue
            request = DownloadRequest(tracker, unit, local_unit)
            requests.append(request)
        # download units
        self.transport.download(requests)
        failed.extend(tracker.get_failed())
        return failed

    def _delete_units(self, unit_inventory):
        """
        Determine the list of units contained in the upstream inventory
        but are not contained in the local inventory and un-associate them.
        @param unit_inventory: The inventory of both upstream and local content units.
        @type unit_inventory: L{UnitInventory}
        @return: The list of units that failed to be un-associated.
            Each item is: (unit, exception)
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
        return failed

    def _units_local(self):
        """
        Fetch the local units using the conduit.  The conduit will
        restrict this search to only those associated with the repository
        to which it is pre-configured.
        @return: A dictionary of units keyed by L{UnitKey}.
        @rtype: dict
        """
        units = self.conduit.get_units()
        return self._unit_dictionary(units)

    def _units_upstream(self):
        """
        Fetch the list of units published by the upstream citrus distributor.
        This is performed by reading the manifest at the URL defined in
        the configuration.
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
        Build a dictionary of units keyed by L{UnitKey} using
        the specified list of units.
        @param units: A list of content units.
            Each unit is either: (L{Unit}|dict)
        @type units: list
        @return: A dictionary of units keyed by L{UnitKey}.
        @rtype: dict
        """
        items = [(UnitKey(u), u) for u in units]
        return dict(items)


class Mirror(Strategy):
    """
    The I{mirror} strategy is used to ensure that the content units associated
    with a repository locally exactly matches the units associated with the same
    repository upstream.  Maintains an exact mirror.
    """

    def synchronize(self, repo_id):
        """
        Performs the following steps:
          1. Read the (upstream) manifest.
          2. Fetch the local units associated with the repository.
          3. Add missing units.
          4. Delete units specified locally but not upstream.
        @param repo_id: The repository ID.
        @type repo_id: str
        @return: A synchronization report.
        @rtype: L{Report}
        """
        unit_inventory = self._unit_inventory(repo_id)

        # add missing units
        add_failed = []
        try:
            failed = self._add_units(unit_inventory)
            if failed:
                add_failed.extend(failed)
                self.progress.set_status(Progress.FAILED)
            else:
                self.progress.set_status(Progress.SUCCEEDED)
        except Exception, e:
            msg = _('Add units failed on repository: %(r)s')
            msg = msg % {'r':repo_id}
            log.exception(msg)
            self.progress.error(msg)
            raise Exception(msg)

        # delete extra units
        delete_failed = []
        try:
            failed = self._delete_units(unit_inventory)
            if failed:
                delete_failed.extend(failed)
                self.progress.set_status(Progress.FAILED)
            else:
                self.progress.set_status(Progress.SUCCEEDED)
        except Exception, e:
            msg = _('Purge units failed on repository: %(r)s')
            msg = msg % {'r':repo_id}
            log.exception(msg)
            self.progress.error(msg)
            raise Exception(msg)

        return Report(add_failed, delete_failed)


class Additive(Strategy):
    """
    The I{additive} strategy is used to ensure that the content units associated
    with a repository locally contains all of the units associated with the same
    repository upstream.  However, any units contained in the local inventory
    that are not contained in the upstream inventory are permitted to remain.
    """

    def synchronize(self, repo_id):
        """
        Performs the following steps:
          1. Read the (upstream) manifest.
          2. Fetch the local units associated with the repository.
          3. Add missing units.
        @param repo_id: The repository ID.
        @type repo_id: str
        @return: A synchronization report.
        @rtype: L{Report}
        """
        unit_inventory = self._unit_inventory(repo_id)

        # add missing units
        add_failed = []
        try:
            failed = self._add_units(unit_inventory)
            if failed:
                add_failed.extend(failed)
                self.progress.set_status(Progress.FAILED)
            else:
                self.progress.set_status(Progress.SUCCEEDED)
        except Exception, e:
            msg = _('Add units failed on repository: %(r)s')
            msg = msg % {'r':repo_id}
            log.exception(msg)
            self.progress.error(msg)
            raise Exception(msg)

        return Report(add_failed, [])


# --- Supporting Objects ----------------------------------------------------------------


class Progress(ProgressReport):
    """
    Progress report provides integration between the citrus progress
    report and the plugin progress reporting facility.
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
        Send progress report using the conduit when the report is updated.
        """
        ProgressReport._updated(self)
        self.conduit.set_progress(self.dict())


class Report:
    """
    A report that provides both summary and details regarding the importing
    of content units associated with a repository.
    @ivar add_failed: List of units that failed to be added.
        Each item is: (L{Unit}, Exception)
    @type add_failed: list
    @ivar delete_failed: List of units that failed to be deleted.
        Each item is: (L{Unit}, Exception)
    @type delete_failed: list
    """

    @staticmethod
    def key_and_repr(units):
        """
        Convert to list of unit_key and exception tuple into a list of
        tuple containing the unit_key and string representation of the
        exception.  This could just be done inline but more descriptive
        to wrap in a method.
        @param units: List of: (Unit, Exception)
        @type units: list
        @return: List of: (dict, str)
        @rtype: list
        """
        return [(u[0].unit_key, repr(u[1])) for u in units]

    def __init__(self, add_failed, delete_failed):
        """
        @param add_failed: List of units that failed to be added.
            Each item is: (L{Unit}, Exception)
        @type add_failed: list
        @param delete_failed: List of units that failed to be deleted.
            Each item is: (L{Unit}, Exception)
        @type delete_failed: list
        """
        self.add_failed = Report.key_and_repr(add_failed)
        self.delete_failed = Report.key_and_repr(delete_failed)
        self.succeeded = not (self.add_failed or self.delete_failed)

    def dict(self):
        """
        Get a dictionary representation.
        """
        return self.__dict__


class UnitKey:
    """
    A unique unit key consisting of a unit's type_id & unit_key.
    The unit key is sorted to ensure consistency.
    @ivar uid: The unique ID.
    @type uid: A tuple of: (type_id, unit_key)
    """

    def __init__(self, unit):
        """
        @param unit: A content unit.
        @type unit: (dict|L{Unit})
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
    The unit inventory contains both the upstream and local inventory
    of content units associated with a specific repository.  Each is contained
    within a dictionary keyed by {UnitKey} to ensure uniqueness.
    @ivar local: The local inventory.
    @type local: dict
    @ivar upstream: The upstream inventory.
    @type upstream: dict
    """

    def __init__(self, local, upstream):
        """
        @param local: The local inventory.
        @type local: dict
        @param upstream: The upstream inventory.
        @type upstream: dict
        """
        self.local = local
        self.upstream = upstream

    def upstream_only(self):
        """
        Listing of units contained in the upstream inventory
        but not contained in the local inventory.
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
        but not contained in the upstream inventory.
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
    The unit download tracker (listener).
    @ivar _strategy: A strategy object.
    @type _strategy: L{Strategy}
    @ivar _failed: The list of units that failed to be downloaded and the
        exception raised during the download.
    @type _failed: list
    """

    def __init__(self, strategy):
        """
        @param repository: The strategy object.
        @type repository: L{Strategy}
        """
        self._strategy = strategy
        self._failed = []

    def succeeded(self, request):
        """
        Called when a download request succeeds.
        Add to succeeded list and notify the strategy.
        @param request: The download request that succeeded.
        @type request: L{DownloadRequest}
        """
        unit = request.local_unit
        try:
            self._strategy.add_unit(unit)
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

    def get_failed(self):
        """
        Get a list of units that failed to download.
          Each item is: (unit, exception)
        @return: List of units that failed to download.
        """
        return self._failed