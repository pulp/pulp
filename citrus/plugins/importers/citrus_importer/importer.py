# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from gettext import gettext as _
from pulp.server.config import config as pulp_conf
from pulp.plugins.model import Unit
from pulp.plugins.importer import Importer
from pulp.citrus.manifest import Manifest
from pulp.citrus.progress import ProgressReport
from logging import getLogger


_LOG = getLogger(__name__)


class UnitKey:
    """
    A unique unit key consisting of the unit's
    type_id & unit_key to be used in unit dictonaries.
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


class ImporterProgress(ProgressReport):
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


class CitrusImporter(Importer):

    @classmethod
    def metadata(cls):
        return {
            'id':'citrus_importer',
            'display_name':'Pulp Citrus Importer',
            'types':['rpm',]
        }

    def __init__(self):
        """
        @ivar cancelled: The flag indicating that the
            current operation has been cancelled.
        @type cancelled: bool
        """
        Importer.__init__(self)
        self.cancelled = False

    def validate_config(self, repo, config, related_repos):
        msg = _('Missing required configuration property: %(p)s')
        for key in ('manifest_url',):
            value = config.get(key)
            if not value:
                return (False, msg % dict(p=key))
        return (True, None)

    def sync_repo(self, repo, conduit, config):
        """
        Synchronize content units associated with the repository.
        Steps:
          1. Read the (upstream) units.json
          2. Fetch the local (downstream) units associated with the repository.
          3. Add missing units.
          4. Delete units specified locally but not upstream.
        @param repo: metadata describing the repository
        @type  repo: L{pulp.server.plugins.model.Repository}
        @param conduit: provides access to relevant Pulp functionality
        @type  conduit: L{pulp.server.conduits.repo_sync.RepoSyncConduit}
        @param config: plugin configuration
        @type  config: L{pulp.server.plugins.config.PluginCallConfiguration}
        @return: report of the details of the sync
        @rtype:  L{pulp.server.plugins.model.SyncReport}
        """
        context = Context(conduit, config)
        context.progress.push_step('fetch_local')
        local_units = self._local_units(context)
        context.progress.push_step('fetch_upstream')
        upstream_units = self._upstream_units(context)
        unit_inventory = UnitInventory(local_units, upstream_units)

        # add missing units
        added = []
        try:
            added = self._add_units(context, unit_inventory)
            context.progress.set_status(ImporterProgress.SUCCEEDED)
        except Exception, e:
            _LOG.exception('Add units failed.')
            context.progress.error(str(e))

         # purge extra units
        added = []
        try:
            purged = self._purge_units(context, unit_inventory)
            context.progress.set_status(ImporterProgress.SUCCEEDED)
        except Exception, e:
            _LOG.exception('Purge units failed.')
            context.progress.error(str(e))

        return conduit.build_success_report({}, {})

    def _missing_units(self, unit_inventory):
        """
        Listing of units contained in the upstream inventory but
        not in the local inventory.
        @param context: The operation context.
        @type context: L{Context}
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

    def _add_units(self, context, unit_inventory):
        """
        Download specified units.
        @param context: The operation context.
        @type context: L{Context}
        @param unit_inventory: The inventory of content units.
        @type unit_inventory: L{UnitInventory}
        """
        added = []
        units = self._missing_units(unit_inventory)
        context.progress.push_step('add_units', len(units))
        requests = []
        for unit, local_unit in units:
            download = unit.get('_download')
            if not download:
                self._add_unit(context, local_unit)
                added.append(local_unit)
                continue
            request = Download(self, context, unit, local_unit)
            requests.append(request)
        # transport hacked in here
        for local_unit in TransportLayer.download(requests):
            added.append(local_unit)
        return added

    def _add_unit(self, context, unit):
        """
        Add units inventoried upstream but not locally.
        @param context: The operation context.
        @type context: L{Context}
        @param unit: A unit to be added.
        @type unit: L{Unit}
        """
        context.conduit.save_unit(unit)
        context.progress.set_action('unit_added', str(unit.unit_key))

    def _purge_units(self, context, unit_inventory):
        """
        Purge units inventoried locally but not upstream.
        @param context: The operation context.
        @type context: L{Context}
        @param unit_inventory: The inventory of content units.
        @type unit_inventory: L{UnitInventory}
        @return: The list of purged units.
        @rtype: list
        """
        purged = []
        units = unit_inventory.local_only()
        context.progress.push_step('purge_units', len(units))
        for unit in units:
            context.progress.set_action('delete_unit', unit.unit_key)
            context.conduit.remove_unit(unit)
            purged.append(unit)
        return purged

    def _local_units(self, context):
        """
        Fetch all local units.
        @param context: The operation context.
        @type context: L{Context}
        @return: A dictionary of units keyed by L{UnitKey}.
        @rtype: dict
        """
        units = context.conduit.get_units()
        return self._unit_dictionary(units)

    def _upstream_units(self, context):
        """
        Fetch upstream units.
        @param context: The operation context.
        @type context: L{Context}
        @param repo_id: The repository ID.
        @type repo_id: str
        @return: A dictionary of units keyed by L{UnitKey}.
        @rtype: dict
        """
        url = context.config.get('manifest_url')
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


class Context:
    """
    Current operation environment.
    @ivar conduit: Provides safe access to pulp sever functionality.
    @type conduit: object
    @ivar config: plugin configuration
    @type config: L{pulp.server.plugins.config.PluginCallConfiguration}
    @ivar progress: A progress report for the current operation.
    @type progress: L{ImporterProgress}
    """

    def __init__(self, conduit, config):
        """
        @param conduit: Provides safe access to pulp sever functionality.
        @type conduit: object
        @param config: plugin configuration
        @type config: L{pulp.server.plugins.config.PluginCallConfiguration}
        """
        self.conduit = conduit
        self.config = config
        self.progress = ImporterProgress(conduit)


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


class Download:
    """
    The download request provides integration between the importer
    and the transport layer.  It's used to request the download of
    the file referenced by a content unit.
    @ivar importer: The importer making the request.
    @type importer: L{CitrusImporter}
    @ivar context: The current operation context.
    @type context: L{Context}
    @ivar unit: The upstream content unit.
    @type unit: dict
    @ivar local_unit: A local content unit that is in the process of
        being added.  The request is to download the file referenced
        in the unit.
    @type local_unit: L{Unit}
    """

    def __init__(self, importer, context, unit, local_unit):
        """
        @param importer: The importer making the request.
        @type importer: L{CitrusImporter}
        @param context: The current operation context.
        @type context: L{Context}
        @param unit: The upstream content unit.
        @type unit: dict
        @param local_unit: A local content unit that is in the process of
            being added.  The request is to download the file referenced
            in the unit.
        @type local_unit: L{Unit}
        """
        self.importer = importer
        self.context = context
        self.unit = unit
        self.local_unit = local_unit

    def protocol(self):
        """
        Get the protocol specified by the upstream unit to be used for
        the download.  A value of 'None' indicates that there is no file
        to be downloaded.
        @return: The protocol name.
        @rtype: str
        """
        download = self.unit.get('_download')
        if download:
            return download.get('protocol')

    def details(self):
        """
        Get the details specified by the upstream unit to be used for
        the download.  A value of 'None' indicates that there is no file
        to be downloaded.  Contains information such as URL for http transports.
        @return: The download specification.
        @rtype: dict
        """
        download = self.unit.get('_download')
        if download:
            return download.get('details')

    def succeeded(self):
        """
        Called by the transport to indicate the requested download succeeded.
        """
        self.importer._add_unit(self.context, self.local_unit)

    def failed(self, exception):
        """
        Called by the transport to indicate the requested download failed.
        @param exception: The exception raised.
        @type exception: Exception
        """
        _LOG.exception('download failed: %s', self.details())


# --- Hacking in the transport -----------------------------------------------------------

import os
import urllib




class HttpTransport:

    def download(self, requests):
        downloaded = []
        for request in requests:
          try:
              self._download(request)
              request.succeeded()
              downloaded.append(request.local_unit)
          except Exception, e:
              request.failed(e)
        return downloaded

    def _download(self, request):
        url = request.details()['url']
        fp_in = urllib.urlopen(url)
        try:
            storage_path = request.local_unit.storage_path
            self._mkdir(storage_path)
            fp_out = open(storage_path, 'w+')
            try:
                while True:
                    bfr = fp_in.read(0x100000)
                    if bfr:
                        fp_out.write(bfr)
                    else:
                        break
            finally:
                fp_out.close()
        finally:
            fp_in.close()

    def _mkdir(self, file_path):
        dir_path = os.path.dirname(file_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)


class TransportLayer:

    TRANSPORTS = {
        'http':HttpTransport,
    }

    @classmethod
    def download(self, requests):
        tr = HttpTransport()
        return tr.download(requests)