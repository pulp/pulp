# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
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
DeltaRPM Support for Yum Importer
"""
import os
from pulp.server.managers.repo.unit_association_query import Criteria
from pulp_rpm.yum_plugin import util

_LOG = util.getLogger(__name__)
DRPM_TYPE_ID="drpm"
DRPM_UNIT_KEY = ("epoch", "version", "release",  "filename", "checksum", "checksumtype")

DRPM_METADATA = ("size", "sequence", "new_package")


def get_available_drpms(drpm_items):
    """
    @param drpm_items list of dictionaries containing info on each drpm, see grinder.YumInfo.__getDRPMs() for more info
    @type drpm_items [{}]

    @return a dictionary, key is the drpm lookup_key and the value is a dictionary with drpm info
    @rtype {():{}}
    """
    available_drpms = {}
    for drpm in drpm_items:
        key = form_lookup_drpm_key(drpm)
        available_drpms[key] = drpm
    return available_drpms

def get_existing_drpm_units(sync_conduit):
   """
   @param sync_conduit
   @type sync_conduit pulp.server.content.conduits.repo_sync.RepoSyncConduit

   @return a dictionary of existing units, key is the drpm lookup_key and the value is the unit
   @rtype {():pulp.server.content.plugins.model.Unit}
   """
   existing_drpm_units = {}
   criteria = Criteria(type_ids=[DRPM_TYPE_ID])
   for u in sync_conduit.get_units(criteria):
       key = form_lookup_drpm_key(u.unit_key)
       existing_drpm_units[key] = u
   return existing_drpm_units

def get_new_drpms_and_units(available_drpms, existing_units, sync_conduit):
    """
    Determines what drpms are new and will initialize new units to match these drpms

    @param available_drpms a dict of available drpms
    @type available_drpms {}

    @param existing_units dict of existing Units
    @type existing_units {pulp.server.content.plugins.model.Unit}

    @param sync_conduit
    @type sync_conduit pulp.server.content.conduits.repo_sync.RepoSyncConduit

    @return a tuple of 2 dictionaries.  First dict is of missing drpms, second dict is of missing units
    @rtype ({}, {})
    """
    new_drpms = {}
    new_units = {}
    for key in available_drpms:
        if key not in existing_units:
            drpm = available_drpms[key]
            pkgpath = os.path.join(drpm["pkgpath"], drpm["filename"])
            new_drpms[key] = drpm
            unit_key = form_drpm_unit_key(drpm)
            metadata = form_drpm_metadata(drpm)
            new_units[key] = sync_conduit.init_unit(DRPM_TYPE_ID, unit_key, metadata, pkgpath)
            drpm["pkgpath"] = os.path.dirname(new_units[key].storage_path).split("/drpms")[0]
    return new_drpms, new_units

def form_drpm_metadata(drpm):
    metadata = {}
    for key in DRPM_METADATA:
        metadata[key] = drpm[key]
    return metadata

def form_lookup_drpm_key(drpm):
    # drpm provides 'fileName', for consistency will rest of Pulp we will add a 'filename'
    if not drpm.has_key("filename"):
        drpm["filename"] = drpm["fileName"]
    drpm_key = (drpm["epoch"], drpm["version"], drpm["release"],  drpm["filename"], drpm["checksum"], drpm["checksumtype"])
    return drpm_key

def form_drpm_unit_key(rpm):
    unit_key = {}
    for key in DRPM_UNIT_KEY:
        unit_key[key] = rpm[key]
    return unit_key

def purge_orphaned_drpm_units(sync_conduit, repo, orphaned_units):
    """
    @param sync_conduit
    @type sync_conduit L{pulp.server.content.conduits.repo_sync.RepoSyncConduit}

    @param repo
    @type repo  L{pulp.server.content.plugins.data.Repository}

    @param orphaned_units
    @type orphaned_units  list of L{pulp.server.content.plugins.model.Unit}
    """
    _LOG.info("purging orphaned drpm units")
    for unit in orphaned_units:
        _LOG.info("Removing unit <%s>" % unit)
        sync_conduit.remove_unit(unit)
        sym_link = os.path.join(repo.working_dir, repo.id, unit.unit_key["filename"])
        if os.path.lexists(sym_link):
            _LOG.debug("Remove link: %s" % sym_link)
            os.unlink(sym_link)

