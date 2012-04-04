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
import logging
import os

_LOG = logging.getLogger(__name__)
DRPM_TYPE_ID="drpm"
DRPM_UNIT_KEY = ("epoch", "version", "release",  "fileName", "checksum", "checksumtype")

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

def get_new_drpms_and_units(available_drpms, existing_units, sync_conduit):
    """
    Determines what rpms are new and will initialize new units to match these drpms

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
            drpm["fileName"] = os.path.basename(drpm["fileName"])
            new_drpms[key] = drpm
            unit_key = form_drpm_unit_key(drpm)
            metadata = form_drpm_metadata(drpm)
            new_units[key] = sync_conduit.init_unit(DRPM_TYPE_ID, unit_key, metadata, drpm["pkgpath"])
            drpm["pkgpath"] = new_units[key].storage_path
    return new_drpms, new_units

def form_drpm_metadata(drpm):
    metadata = {}
    for key in DRPM_METADATA:
        metadata[key] = drpm[key]
    return metadata

def form_lookup_drpm_key(drpm):
    drpm_key = (drpm["epoch"], drpm["version"], drpm["release"],  drpm["fileName"], drpm["checksum"], drpm["checksumtype"])
    return drpm_key

def form_drpm_unit_key(rpm):
    unit_key = {}
    for key in DRPM_UNIT_KEY:
        unit_key[key] = rpm[key]
    return unit_key

