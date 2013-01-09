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

    def __init__(self, conduit):
        self.conduit = conduit
        ProgressReport.__init__(self)

    def _updated(self):
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

    def validate_config(self, repo, config, related_repos):
        msg = _('Missing required configuration property: %(p)s')
        for key in ('manifest_url',):
            value = config.get(key)
            if not value:
                return (False, msg % dict(p=key))
        return (True, None)

    def sync_repo(self, repo, conduit, config):
        """
        Synchronizes content into the given repository. This call is responsible
        for adding new content units to Pulp as well as associating them to the
        given repository.

        While this call may be implemented using multiple threads, its execution
        from the Pulp server's standpoint should be synchronous. This call should
        not return until the sync is complete.

        It is not expected that this call be atomic. Should an error occur, it
        is not the responsibility of the importer to rollback any unit additions
        or associations that have been made.

        The returned report object is used to communicate the results of the
        sync back to the user. Care should be taken to i18n the free text "log"
        attribute in the report if applicable.

        Steps:
          1. Read the (upstream) units.json
          2. Fetch the local (downstream) units associated with the repostory.
          3. Add missing units.
          4. Delete units specified locally but not upstream.

        @param repo: metadata describing the repository
        @type  repo: L{pulp.server.plugins.model.Repository}
        @param sync_conduit: provides access to relevant Pulp functionality
        @type  sync_conduit: L{pulp.server.conduits.repo_sync.RepoSyncConduit}
        @param config: plugin configuration
        @type  config: L{pulp.server.plugins.config.PluginCallConfiguration}
        @return: report of the details of the sync
        @rtype:  L{pulp.server.plugins.model.SyncReport}
        """
        manifest_url = config.get('manifest_url')
        progress = ImporterProgress(conduit)
        progress.push_step('fetch_local')
        local_units = self._local_units(conduit)
        progress.push_step('fetch_upstream')
        upstream_units = self._upstream_units(manifest_url)

        # add missing units
        added = []
        try:
            added = self._add_units(conduit, progress, local_units, upstream_units)
            progress.set_status(progress.SUCCEEDED)
        except Exception, e:
            _LOG.exception('Add units failed.')
            progress.error(str(e))

        # download added units
        try:
            downloaded = self._download_units(progress, added)
            progress.set_status(progress.SUCCEEDED)
        except Exception, e:
            _LOG.exception('Download units failed.')
            progress.error(str(e))

         # purge extra units
        try:
            purge = self._purge_units(conduit, progress, local_units, upstream_units)
            progress.set_status(progress.SUCCEEDED)
        except Exception, e:
            _LOG.exception('Purge units failed.')
            progress.error(str(e))

        return conduit.build_success_report({}, {})

    def _add_units(self, conduit, progress, local, upstream):
        """
        Add units inventoried upstream but not locally.
        @param conduit: provides access to relevant Pulp functionality
        @type  conduit: L{pulp.server.conduits.repo_sync.RepoSyncConduit}
        @param progress: A progress report.
        @type progress: L{ImporterProgress}
        @param local: A dictionary of locally defined units.
        @type local: dict
        @param upstream: A dictionary of units defined upstream.
        @type upstream: dict
        @return: The list of purged units.
        @rtype: list
        """
        missing = []
        for k, unit in upstream.items():
            if k not in local:
                missing.append(unit)
        storage_dir = pulp_conf.get('server', 'storage_dir')
        progress.push_step('add_units', len(missing))
        added = []
        for unit in missing:
            unit['metadata'].pop('_id')
            unit['metadata'].pop('_ns')
            type_id = unit['type_id']
            unit_key = unit['unit_key']
            metadata = unit['metadata']
            storage_path = unit.get('storage_path')
            if storage_path:
                storage_path = '/'.join((storage_dir, storage_path))
            unit_in = Unit(type_id, unit_key, metadata, storage_path)
            progress.set_action('save_unit', unit_key)
            conduit.save_unit(unit_in)
            added.append((unit, unit_in))
        return added

    def _download_units(self, progress, units):
        """
        Download specified units.
        @param progress: A progress report.
        @type progress: L{ImporterProgress}
        @param units: List of unit tuple (unit, local_unit)
        @type units: list
        @return: list of downloaded units.
        @rtype: list
        """
        progress.push_step('download_units', len(units))
        downloaded = []
        request_list = []
        for unit, local_unit in units:
            download = unit['_download']
            protocol = download['protocol']
            details = download['details']
            storage_path = local_unit.storage_path
            if not storage_path:
                # not all units are associated with files.
                progress.set_action('skipped', '')
                continue
            request = DownloadRequest(protocol, details, storage_path)
            request_list.append(request)
        def _fn(request):
            progress.set_action('downloaded', request.storage_path)
            downloaded.append(request.storage_path)
        # transport hacked in here
        TransportLayer.download(request_list, _fn)
        return downloaded

    def _purge_units(self, conduit, progress, local, upstream):
        """
        Purge units inventoried locally but not upstream.
        @param conduit: provides access to relevant Pulp functionality
        @type  conduit: L{pulp.server.conduits.repo_sync.RepoSyncConduit}
        @param progress: A progress report.
        @type progress: L{ImporterProgress}
        @param local: A dictionary of locally defined units.
        @type local: dict
        @param upstream: A dictionary of units defined upstream.
        @type upstream: dict
        @return: The list of purged units.
        @rtype: list
        """
        unwanted = []
        for k, unit in local.items():
            if k not in upstream:
                unwanted.append(unit)
        purged = []
        progress.push_step('purge_units', len(purged))
        for unit in unwanted:
            progress.set_action('delete_unit', unit.unit_key)
            conduit.remove_unit(unit)
            purged.append(unit)
        return purged

    def _local_units(self, conduit):
        """
        Fetch all local units.
        @param conduit: provides access to relevant Pulp functionality
        @type  conduit: L{pulp.server.conduits.repo_sync.RepoSyncConduit}
        @return: A dictionary of units keyed by L{UnitKey}.
        @rtype: dict
        """
        units = conduit.get_units()
        return self._unit_dictionary(units)

    def _upstream_units(self, manifest_url):
        """
        Fetch upstream units.
        @param repo_id: The repository ID.
        @type repo_id: str
        @return: A dictionary of units keyed by L{UnitKey}.
        @rtype: dict
        """
        manifest = Manifest()
        units = manifest.read(manifest_url)
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



# --- Hacking in the transport -----------------------------------------------------------

import os
import urllib

class DownloadRequest:

    def __init__(self, protocol, details, storage_path):
        self.protocol = protocol
        self.details = details
        self.storage_path = storage_path

class HttpTransport:

    def download(self, request_list, callback):
        for request in request_list:
            url = request.details['url']
            fp_in = urllib.urlopen(url)
            try:
                self._mkdir(request.storage_path)
                fp_out = open(request.storage_path, 'w+')
                try:
                    while True:
                        bfr = fp_in.read(0x100000)
                        if bfr:
                            fp_out.write(bfr)
                        else:
                            break
                finally:
                    fp_out.close()
                    callback(request)
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
    def download(self, request_list, callback):
        tr = HttpTransport()
        tr.download(request_list, callback)