"""
Provides classes that implement unit synchronization strategies.
Nodes importer plugins delegate synchronization to one of
the strategies provided here.
"""

import os
import errno

from gettext import gettext as _
from logging import getLogger
from urlparse import urlparse, ParseResult

from pulp.plugins.model import Unit, AssociatedUnit
from pulp.server.config import config as pulp_conf
from pulp.server.content.sources.container import ContentContainer

from pulp_node import constants
from pulp_node import pathlib
from pulp_node.conduit import NodesConduit
from pulp_node.manifest import Manifest, RemoteManifest
from pulp_node.importers.inventory import UnitInventory
from pulp_node.importers.download import ContentDownloadListener
from pulp_node.error import (NodeError, GetChildUnitsError, GetParentUnitsError, AddUnitError,
                             DeleteUnitError, InvalidManifestError, CaughtException)


_log = getLogger(__name__)


STRATEGY_UNSUPPORTED = _('Importer strategy "%(s)s" not supported')


class Request(object):
    """
    Represents a specific request to synchronize a repository on a child node.
    It contains the resources needed by the strategy to complete the request
    and maintains the state of the request.
    :ivar conduit: Provides access to relevant Pulp functionality.
    :type conduit: pulp.server.conduits.repo_sync.RepoSyncConduit
    :ivar config: The plugin configuration.
    :type config: pulp.server.plugins.config.PluginCallConfiguration
    :ivar downloader: A fully configured file downloader.
    :type downloader: nectar.downloaders.base.Downloader
    :ivar progress: A progress reporting object.
    :type progress: pulp_node.importers.reports.RepositoryProgress
    :ivar summary: A summary report.
    :type summary: pulp_node.importers.reports.SummaryReport
    :ivar repo_id: The ID of a repository to synchronize.
    :type repo_id: str
    :ivar working_dir: The absolute path to a directory to be used as temporary storage.
    :type working_dir: str
    """

    def __init__(self, cancel_event, conduit, config, downloader, progress, summary, repo):
        """
        :param cancel_event: Event used to signal that the synchronization has been
            canceled by another thread.
        :type cancel_event: threading.Event
        :param conduit: Provides access to relevant Pulp functionality.
        :type conduit: pulp.server.conduits.repo_sync.RepoSyncConduit
        :param config: The plugin configuration.
        :type config: pulp.server.plugins.config.PluginCallConfiguration
        :param downloader: A fully configured file downloader.
        :type downloader: nectar.downloaders.base.Downloader
        :param progress: A progress reporting object.
        :type progress: pulp_node.importers.reports.RepositoryProgress
        :param summary: A summary report.
        :type summary: pulp_node.importers.reports.SummaryReport
        :param repo: The repository to synchronize.
        :type repo_id: pulp.server.plugins.model.Repository
        """
        self.cancel_event = cancel_event
        self.conduit = conduit
        self.config = config
        self.downloader = downloader
        self.progress = progress
        self.summary = summary
        self.repo_id = repo.id
        self.working_dir = repo.working_dir

    def started(self):
        """
        Processing the request has started.
        """
        self.progress.begin_importing()

    def cancelled(self):
        """
        Get whether the request has been cancelled.
        :return: True if cancelled.
        :rtype: bool
        """
        return self.cancel_event.isSet()


# --- abstract strategy  ----------------------------------------------------------------


class ImporterStrategy(object):
    """
    This object provides the transport independent content unit
    synchronization strategies used by nodes importer plugins.
    """

    def synchronize(self, request):
        """
        Synchronize the content units associated with the specified repository.
        :param request: A synchronization request.
        :type request: SyncRequest
        """
        request.started()

        try:
            self._synchronize(request)
        except NodeError, ne:
            request.summary.errors.append(ne)
        except Exception, e:
            _log.exception(request.repo_id)
            request.summary.errors.append(CaughtException(e, request.repo_id))

    def _synchronize(self, request):
        """
        Specific strategies defined by subclasses.
        :param request: A synchronization request.
        :type request: SyncRequest
        """
        raise NotImplementedError()

    def add_unit(self, request, unit):
        """
        Add the specified unit to the child inventory using the conduit.
        The conduit will automatically associate the unit to the repository
        to which it's pre-configured.
        :param request: A synchronization request.
        :type request: SyncRequest
        :param unit: The unit to be added.
        :type unit: dict
        """
        try:
            new_unit = Unit(
                type_id=unit['type_id'],
                unit_key=unit['unit_key'],
                metadata=unit['metadata'],
                storage_path=unit['storage_path'])
            request.conduit.save_unit(new_unit)
            request.progress.unit_added(details=new_unit.storage_path)
        except Exception:
            _log.exception(unit['unit_id'])
            request.summary.errors.append(AddUnitError(request.repo_id))

    # --- protected ---------------------------------------------------------------------

    def _unit_inventory(self, request):
        """
        Build the unit inventory.
        :param request: A synchronization request.
        :type request: SyncRequest
        :return: The built inventory.
        :rtype: UnitInventory
        """
        # fetch child units
        try:
            conduit = NodesConduit()
            child_units = conduit.get_units(request.repo_id)
        except NodeError:
            raise
        except Exception:
            _log.exception(request.repo_id)
            raise GetChildUnitsError(request.repo_id)

        # fetch parent units
        try:
            request.progress.begin_manifest_download()
            url = request.config.get(constants.MANIFEST_URL_KEYWORD)
            manifest = Manifest(request.working_dir)
            try:
                manifest.read()
            except IOError, e:
                if e.errno == errno.ENOENT:
                    pass
            except ValueError:
                # json decoding failed
                pass
            fetched_manifest = RemoteManifest(url, request.downloader, request.working_dir)
            fetched_manifest.fetch()
            if manifest != fetched_manifest or \
                    not manifest.is_valid() or not manifest.has_valid_units():
                fetched_manifest.write()
                fetched_manifest.fetch_units()
                manifest = fetched_manifest
            if not manifest.is_valid():
                raise InvalidManifestError()
        except NodeError:
            raise
        except Exception:
            _log.exception(request.repo_id)
            raise GetParentUnitsError(request.repo_id)

        # build the inventory
        parent_units = manifest.get_units()
        base_URL = manifest.publishing_details[constants.BASE_URL]
        inventory = UnitInventory(base_URL, parent_units, child_units)
        return inventory

    def _reset_storage_path(self, unit):
        """
        Reset the storage_path using the storage_dir defined in
        server.conf and the relative_path injected when the unit was published.
        :param unit: A published unit.
        :type unit: dict
        :return: The re-oriented storage path.
        :rtype: str
        """
        storage_path = unit.get(constants.STORAGE_PATH)
        if not storage_path:
            return
        storage_dir = pulp_conf.get('server', 'storage_dir')
        relative_path = unit[constants.RELATIVE_PATH]
        storage_path = pathlib.join(storage_dir, relative_path)
        unit[constants.STORAGE_PATH] = storage_path

    def _add_units(self, request, unit_inventory):
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
        unit download manager callback.
        :param request: A synchronization request.
        :type request: SyncRequest
        :param unit_inventory: The inventory of both parent and child content units.
        :type unit_inventory: UnitInventory
        """
        download_list = []
        units = unit_inventory.units_on_parent_only()
        request.progress.begin_adding_units(len(units))
        listener = ContentDownloadListener(self, request)
        for unit, unit_ref in units:
            if request.cancelled():
                return
            self._reset_storage_path(unit)
            if not self._needs_download(unit):
                # unit has no file associated
                self.add_unit(request, unit_ref.fetch())
                continue
            unit_url, destination = self._url_and_destination(unit_inventory.base_URL, unit)
            _request = listener.create_request(unit_url, destination, unit, unit_ref)
            download_list.append(_request)
        if request.cancelled():
            return
        container = ContentContainer()
        request.summary.sources = \
            container.download(request.cancel_event, request.downloader, download_list, listener)
        request.summary.errors.extend(listener.error_list)

    def _update_units(self, request, unit_inventory):
        """
        Update units that have been updated on the parent since
        added or last updated in the child inventory.
        :param request: A synchronization request.
        :type request: SyncRequest
        :param unit_inventory: The inventory of both parent and child content units.
        :type unit_inventory: UnitInventory
        """
        download_list = []
        units = unit_inventory.updated_units()
        listener = ContentDownloadListener(self, request)
        for unit, unit_ref in units:
            storage_path = unit[constants.STORAGE_PATH]
            if storage_path:
                self._reset_storage_path(unit)
                unit_url, destination = self._url_and_destination(unit_inventory.base_URL, unit)
                _request = listener.create_request(unit_url, destination, unit, unit_ref)
                download_list.append(_request)
            else:
                unit = unit_ref.fetch()
                self.add_unit(request, unit)
        if not download_list:
            return
        container = ContentContainer()
        request.summary.sources = container.download(
            request.cancel_event,
            request.downloader,
            download_list,
            listener)
        request.summary.errors.extend(listener.error_list)

    def _url_and_destination(self, base_url, unit):
        """
        Get the download URL and download destination.
        :param base_url: The base URL.
        :type base_url: str
        :param unit: A content unit.
        :type unit: dict
        :return: (url, destination)
        :rtype: tuple(2)
        """
        storage_path = unit[constants.STORAGE_PATH]
        tar_path = unit.get(constants.TARBALL_PATH)
        if not tar_path:
            # The pulp/nodes/content endpoint provides all content.
            # This replaced the publishing of individual links for each unit.
            parsed = urlparse(base_url)
            relative_path = unit[constants.RELATIVE_PATH]
            path = pathlib.join(constants.CONTENT_PATH, pathlib.quote(relative_path))
            base_url = ParseResult(
                scheme=parsed.scheme,
                netloc=parsed.netloc,
                path=path,
                params=parsed.params,
                query=parsed.query,
                fragment=parsed.fragment)
            return base_url.geturl(), storage_path
        else:
            return pathlib.url_join(base_url, pathlib.quote(tar_path)),\
                pathlib.join(os.path.dirname(storage_path), os.path.basename(tar_path))

    def _needs_download(self, unit):
        """
        Get whether the unit has an associated file that needs to be downloaded.
        :param unit: A content unit.
        :type unit: dict
        :return: True if has associated file that needs to be downloaded.
        :rtype: bool
        """
        storage_path = unit.get(constants.STORAGE_PATH)
        if storage_path:
            if not os.path.exists(storage_path):
                return True
            if os.path.getsize(storage_path) != unit[constants.FILE_SIZE]:
                return True
        return False

    def _delete_units(self, request, unit_inventory):
        """
        Determine the list of units contained in the child inventory
        but are not contained in the parent inventory and un-associate them.
        :param request: A synchronization request.
        :type request: SyncRequest
        :param unit_inventory: The inventory of both parent and child content units.
        :type unit_inventory: UnitInventory
        """
        for unit in unit_inventory.units_on_child_only():
            if request.cancelled():
                return
            try:
                _unit = AssociatedUnit(
                    type_id=unit['type_id'],
                    unit_key=unit['unit_key'],
                    metadata={},
                    storage_path=None,
                    created=None,
                    updated=None)
                _unit.id = unit['unit_id']
                request.conduit.remove_unit(_unit)
            except Exception:
                _log.exception(unit['unit_id'])
                request.summary.errors.append(DeleteUnitError(request.repo_id))


class Mirror(ImporterStrategy):
    """
    The *mirror* strategy is used to ensure that the content units associated
    with a child repository exactly matches the units associated with the same
    repository in the parent.  Maintains an exact mirror.
    """

    def _synchronize(self, request):
        """
        Performs the following steps:
          1. Read the (parent) manifest.
          2. Fetch the child units associated with the repository.
          3. Add missing units.
          4. Delete units specified in the child but not in the parent.
        :param request: A synchronization request.
        :type request: SyncRequest
        """
        unit_inventory = self._unit_inventory(request)
        self._add_units(request, unit_inventory)
        self._update_units(request, unit_inventory)
        self._delete_units(request, unit_inventory)


class Additive(ImporterStrategy):
    """
    The I{additive} strategy is used to ensure that the content units associated
    with a child repository contains all of the units associated with the same
    repository in the parent.  However, any units contained in the child inventory
    that are not contained in the parent inventory are permitted to remain.
    """

    def _synchronize(self, request):
        """
        Performs the following steps:
          1. Read the (parent) manifest.
          2. Fetch the child units associated with the repository.
          3. Add missing units.
        :param request: A synchronization request.
        :type request: SyncRequest
        """
        unit_inventory = self._unit_inventory(request)
        self._add_units(request, unit_inventory)
        self._update_units(request, unit_inventory)


STRATEGIES = {
    constants.MIRROR_STRATEGY: Mirror,
    constants.ADDITIVE_STRATEGY: Additive,
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
    :rtype: callable
    :raise: StrategyUnsupported when not found.
    """
    try:
        return STRATEGIES[name]
    except KeyError:
        raise StrategyUnsupported(name)
