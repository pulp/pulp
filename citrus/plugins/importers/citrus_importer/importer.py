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

import hashlib

from pulp.server.config import config as pulp_conf
from pulp.server.compat import json
from pulp.plugins.model import Unit
from pulp.plugins.importer import Importer
from pulp.citrus.transport import HttpReader
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


class CitrusImporter(Importer):

    @classmethod
    def metadata(cls):
        return {
            'id':'citrus_importer',
            'display_name':'Pulp Citrus Importer',
            'types':['rpm',]
        }

    def validate_config(self, repo, config, related_repos):
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
        base_url = config.get('base_url')
        reader = HttpReader(base_url)
        return self._synchronize(repo.id, reader, conduit)

    def _synchronize(self, repo_id, reader, conduit):
        local_units = self._local_units(conduit)
        upstream_units = self._upstream_units(repo_id, reader)
        # add missing units
        storage_dir = pulp_conf.get('server', 'storage_dir')
        for k, unit in upstream_units.items():
            if k in local_units:
                continue
            unit['metadata'].pop('_id')
            unit['metadata'].pop('_ns')
            unit_in = Unit(
                unit['type_id'],
                unit['unit_key'],
                unit['metadata'],
                '/'.join((storage_dir, unit['storage_path'])))
            conduit.save_unit(unit_in)
            reader.download(repo_id, unit, unit_in)
         # purge extra units
        for k, unit in local_units.items():
            if k not in upstream_units:
                conduit.remove_unit(unit)

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

    def _upstream_units(self, repo_id, reader):
        """
        Fetch upstream units.
        @param repo_id: The repository ID.
        @type repo_id: str
        @return: A dictionary of units keyed by L{UnitKey}.
        @rtype: dict
        """
        manifest = Manifest(reader, repo_id)
        units = manifest.read()
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


class Manifest:
    """
    An http based upstream units (json) document.
    Download the document and perform the JSON conversion.
    @ivar repo_id: A repository ID.
    @type repo_id: str
    """

    def __init__(self, reader, repo_id):
        """
        @param repo_id: A repository ID.
        @type repo_id: str
        """
        self.reader = reader
        self.repo_id = repo_id

    def read(self):
        """
        Fetch the document.
        @return: The downloaded json document.
        @rtype: str
        """
        fp_in = self.reader.open(self.repo_id, 'units.json')
        try:
            return json.load(fp_in)
        finally:
            fp_in.close()
