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

"""
Provides classes that implement unit synchronization strategies.
Nodes importer plugins delegate synchronization to one of
the strategies provided here.
"""


from gettext import gettext as _
from logging import getLogger

from pulp.plugins.model import Unit
from pulp.server.config import config as pulp_conf

from pulp_node.manifest import Manifest
from pulp_node.importers.reports import ImporterReport, ImporterProgress
from pulp_node.importers.inventory import UnitInventory, unit_dictionary
from pulp_node.importers.download import Batch, DownloadListener


log = getLogger(__name__)


# --- i18n ------------------------------------------------------------------------------

FETCH_CHILD_UNITS_FAILED = _('Fetch child units failed for repository: %(r)s')
FETCH_PARENT_UNITS_FAILED = _('Fetch parent units failed for repository: %(r)s')
ADD_UNITS_FAILED = _('Add units failed on repository: %(r)s')
PURGE_UNITS_FAILED = _('Purge units failed on repository: %(r)s')
STRATEGY_UNSUPPORTED = _('Importer strategy "%(s)s" not supported')


# --- abstract strategy  ----------------------------------------------------------------


class ImporterStrategy(object):
    """
    This object provides the transport independent content unit
    synchronization strategies used by nodes importer plugins.
    :ivar cancelled: The flag indicating that the current operation
        has been cancelled.
    :type cancelled: bool
    :ivar conduit: Provides access to relevant Pulp functionality
    :type conduit: pulp.server.conduits.repo_sync.RepoSyncConduit
    :ivar config: The plugin configuration.
    :type config: pulp.server.plugins.config.PluginCallConfiguration
    :ivar downloader: A fully configured file downloader.
    :type downloader: pulp.common.download.backends.base.DownloadBackend
    :ivar progress: A progress reporting object.
    :type progress: ImporterProgress
    """

    def __init__(self, conduit, config, downloader):
        """
        :param conduit: Provides access to relevant Pulp functionality.
        :type conduit: pulp.server.conduits.repo_sync.RepoSyncConduit
        :param config: The plugin configuration.
        :type config: pulp.server.plugins.config.PluginCallConfiguration
        :param downloader: A fully configured file downloader.
        :type downloader: pulp.common.download.backends.base.DownloadBackend
        """
        self.cancelled = False
        self.conduit = conduit
        self.config = config
        self.downloader = downloader
        self.progress = ImporterProgress(conduit)

    def synchronize(self, repo_id):
        """
        Synchronize the content units associated with the specified repository.
        Specific strategies defined by subclasses.
        :param repo_id: The repository ID.
        :type repo_id: str
        :return: A synchronization report.
        :rtype: Report
        """
        raise NotImplementedError()

    def cancel(self):
        """
        Cancel the synchronization in progress.
        """
        self.cancelled = True
        self.downloader.cancel()

    def add_unit(self, unit):
        """
        Add the specified unit to the child inventory using the conduit.
        The conduit will automatically associate the unit to the repository
        to which it's pre-configured.
        :param unit: The unit to be added.
        :type unit: Unit
        """
        self.conduit.save_unit(unit)
        self.progress.set_action('unit_added', str(unit.unit_key))

    # --- protected ---------------------------------------------------------------------

    def _unit_inventory(self, repo_id):
        """
        Build the unit inventory.
        :param repo_id: A repository ID.
        :rtype repo_id: str
        :return: The built inventory.
        :rtype: UnitInventory
        """
        # fetch child units
        child = {}
        try:
            self.progress.push_step('fetch_child')
            units = self._child_units()
            child.update(units)
            self.progress.set_status(ImporterProgress.SUCCEEDED)
        except Exception:
            msg = FETCH_CHILD_UNITS_FAILED % {'r': repo_id}
            log.exception(msg)
            self.progress.error(msg)
            raise Exception(msg)
        # fetch parent units
        parent = {}
        try:
            self.progress.push_step('fetch_parent')
            units = self._parent_units()
            parent.update(units)
            self.progress.set_status(ImporterProgress.SUCCEEDED)
        except Exception:
            msg = FETCH_PARENT_UNITS_FAILED % {'r': repo_id}
            log.exception(msg)
            self.progress.error(msg)
            raise Exception(msg)
        return UnitInventory(child, parent)

    def _missing_units(self, unit_inventory):
        """
        Determine the list of units defined parent inventory that are
        not in the child inventory.
        :param unit_inventory: The inventory of both parent and child content units.
        :type unit_inventory: UnitInventory
        :return: The list of units to be added.
            Each item: (parent_unit, unit_to_be_added)
        :rtype: list
        """
        new_units = []
        storage_dir = pulp_conf.get('server', 'storage_dir')
        for unit in unit_inventory.parent_only():
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
        Determine the list of units contained in the parent inventory
        but are not contained in the child inventory and add them.
        For each unit, this is performed in the following steps:
          1. Download the file (if defined) associated with the unit.
          2. Add the unit to the child inventory.
          3. Associate the unit to the repository.
        The unit is added only:
          1. If no file is associated with unit.
          2. The file associated with the unit is successfully downloaded.
        For units with files, the unit is added to the inventory as part of the
        transport callback.
        :param unit_inventory: The inventory of both parent and child content units.
        :type unit_inventory: UnitInventory
        :return: The list of failed that failed to be added.
            Each item is: (unit, exception)
        :rtype: list
        """
        failed = []
        units = self._missing_units(unit_inventory)
        self.progress.push_step('add_units', len(units))
        batch = Batch()
        for unit, child_unit in units:
            if self.cancelled:
                break
            download = unit.get('_download')
            # unit has no file associated
            if not download:
                try:
                    self.add_unit(child_unit)
                except Exception, e:
                    failed.append((child_unit, e))
                continue
            url = download['url']
            batch.add(url, child_unit)
        if not self.cancelled:
            listener = DownloadListener(self, batch)
            self.downloader.event_listener = listener
            self.downloader.download(batch.request_list)
            failed.extend(listener.failed)
        return failed

    def _delete_units(self, unit_inventory):
        """
        Determine the list of units contained in the child inventory
        but are not contained in the parent inventory and un-associate them.
        :param unit_inventory: The inventory of both parent and child content units.
        :type unit_inventory: UnitInventory
        :return: The list of units that failed to be un-associated.
            Each item is: (unit, exception)
        :rtype: list
        """
        failed = []
        succeeded = []
        units = unit_inventory.child_only()
        self.progress.push_step('purge_units', len(units))
        for unit in units:
            if self.cancelled:
                break
            try:
                self.progress.set_action('delete_unit', unit.unit_key)
                self.conduit.remove_unit(unit)
                succeeded.append(unit)
            except Exception, e:
                failed.append((unit, e))
        return failed

    def _child_units(self):
        """
        Fetch the child units using the conduit.  The conduit will
        restrict this search to only those associated with the repository
        to which it is pre-configured.
        :return: A dictionary of units keyed by UnitKey.
        :rtype: dict
        """
        units = self.conduit.get_units()
        return unit_dictionary(units)

    def _parent_units(self):
        """
        Fetch the list of units published by the parent nodes distributor.
        This is performed by reading the manifest at the URL defined in
        the configuration.
        :param repo_id: The repository ID.
        :type repo_id: str
        :return: A dictionary of units keyed by UnitKey.
        :rtype: dict
        """
        url = self.config.get('manifest_url')
        manifest = Manifest()
        units = manifest.read(url, self.downloader)
        return unit_dictionary(units)


# --- strategies ------------------------------------------------------------------------


class Mirror(ImporterStrategy):
    """
    The *mirror* strategy is used to ensure that the content units associated
    with a child repository exactly matches the units associated with the same
    repository in the parent.  Maintains an exact mirror.
    """

    def synchronize(self, repo_id):
        """
        Performs the following steps:
          1. Read the (parent) manifest.
          2. Fetch the child units associated with the repository.
          3. Add missing units.
          4. Delete units specified in the child but not in the parent.
        :param repo_id: The repository ID.
        :type repo_id: str
        :return: A synchronization report.
        :rtype: Report
        """
        unit_inventory = self._unit_inventory(repo_id)

        # add missing units
        add_failed = []
        try:
            failed = self._add_units(unit_inventory)
            if failed:
                add_failed.extend(failed)
                self.progress.set_status(ImporterProgress.FAILED)
            else:
                self.progress.set_status(ImporterProgress.SUCCEEDED)
        except Exception:
            msg = ADD_UNITS_FAILED % {'r': repo_id}
            log.exception(msg)
            self.progress.error(msg)
            raise Exception(msg)

        # delete extra units
        delete_failed = []
        try:
            failed = self._delete_units(unit_inventory)
            if failed:
                delete_failed.extend(failed)
                self.progress.set_status(ImporterProgress.FAILED)
            else:
                self.progress.set_status(ImporterProgress.SUCCEEDED)
        except Exception:
            msg = PURGE_UNITS_FAILED % {'r': repo_id}
            log.exception(msg)
            self.progress.error(msg)
            raise Exception(msg)

        return ImporterReport(add_failed, delete_failed)


class Additive(ImporterStrategy):
    """
    The I{additive} strategy is used to ensure that the content units associated
    with a child repository contains all of the units associated with the same
    repository in the parent.  However, any units contained in the child inventory
    that are not contained in the parent inventory are permitted to remain.
    """

    def synchronize(self, repo_id):
        """
        Performs the following steps:
          1. Read the (parent) manifest.
          2. Fetch the child units associated with the repository.
          3. Add missing units.
        :param repo_id: The repository ID.
        :type repo_id: str
        :return: A synchronization report.
        :rtype: Report
        """
        unit_inventory = self._unit_inventory(repo_id)

        # add missing units
        add_failed = []
        try:
            failed = self._add_units(unit_inventory)
            if failed:
                add_failed.extend(failed)
                self.progress.set_status(ImporterProgress.FAILED)
            else:
                self.progress.set_status(ImporterProgress.SUCCEEDED)
        except Exception:
            msg = ADD_UNITS_FAILED % {'r': repo_id}
            log.exception(msg)
            self.progress.error(msg)
            raise Exception(msg)

        return ImporterReport(add_failed, [])


# --- factory ---------------------------------------------------------------------------


STRATEGIES = {
    'mirror' : Mirror,
    'additive': Additive,
}


class StrategyUnsupported(Exception):

    def __init__(self, name):
        msg = STRATEGY_UNSUPPORTED % {'s': name}
        Exception.__init__(self, msg)


def find_strategy(name):
    """
    Find a strategy (class) by name.
    :param name: A strategy name.
    :type name: str
    :return: A strategy class.
    :rtype: HandlerStrategy
    :raise: StrategyUnsupported when not found.
    """
    try:
        return STRATEGIES[name]
    except KeyError:
        raise StrategyUnsupported(name)
