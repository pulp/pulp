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
Distribution Support for Yum Importer
"""
import logging
import os
from pulp.server.managers.repo.unit_association_query import Criteria
from pulp_rpm.yum_plugin import util

_LOG = logging.getLogger(__name__)
DISTRO_TYPE_ID="distribution"

DISTRO_UNIT_KEY = ("id", "family", "variant", "version", "arch")
DISTRO_METADATA = ("files",)

def get_available_distributions(distro_items):
    """
    @param distro_items list of dictionaries containing info on each distribution info
    @type distro_items [{}]

    @return a dictionary, key is the distro lookup_key and the value is a dictionary with distro info
    @rtype {():{}}
    """
    available_distros = {}
    if distro_items:
        distro_items = [distro_items]
    for dinfo in distro_items:
        key = form_lookup_distro_key(dinfo)
        available_distros[key] = dinfo
    return available_distros

def get_existing_distro_units(sync_conduit):
    """
    @param sync_conduit
    @type sync_conduit pulp.server.content.conduits.repo_sync.RepoSyncConduit

    @return a dictionary of existing units, key is the distribution lookup_key and the value is the unit
    @rtype {():pulp.server.content.plugins.model.Unit}
    """
    existing_distro_units = {}
    criteria = Criteria(type_ids=[DISTRO_TYPE_ID])
    for u in sync_conduit.get_units(criteria):
        key = form_lookup_distro_key(u.unit_key)
        existing_distro_units[key] = u
    return existing_distro_units

def get_new_distros_and_units(available_distros, existing_distro_units, sync_conduit):
    """
    Determines what distro are new and will initialize new units to match these distros

    @param available_distros a dict of available distross
    @type available_distros {}

    @param existing_distro_units dict of existing Units
    @type existing_distro_units {pulp.server.content.plugins.model.Unit}

    @param sync_conduit
    @type sync_conduit pulp.server.content.conduits.repo_sync.RepoSyncConduit

    @return a tuple of 2 dictionaries.  First dict is of new distro files, second dict is of new units
    @rtype ({}, {})
    """
    new_distros = {}
    new_units = {}
    new_distro_files = {}
    for key in available_distros:
        if key not in existing_distro_units:
            distro = available_distros[key]
            new_distros[key] = distro
            unit_key = form_distro_unit_key(distro)
            metadata = form_distro_metadata(distro)
            pkg_path = distro["id"]
            new_units[key] = sync_conduit.init_unit(DISTRO_TYPE_ID, unit_key, metadata, pkg_path)
            for ksfile in distro['files']:
                pkgpath = os.path.join(new_units[key].storage_path, ksfile["relativepath"])
                ksfile["pkgpath"] = os.path.dirname(pkgpath)
                ksfile["filename"] = ksfile["fileName"] #= os.path.basename(pkgpath)
            new_distro_files[key] = distro['files']
    return new_distro_files, new_units

def get_missing_distros_and_units(available_distro, existing_distro_units, verify_options={}):
    """
    @param available_distro dict of available distributions
    @type available_distro {}

    @param existing_distro_units dict of existing Units
    @type existing_distro_units {key:pulp.server.content.plugins.model.Unit}

    @return a tuple of 2 dictionaries.  First dict is of missing distros files, second dict is of missing units
    @rtype ({}, {})
    """
    missing_distro = {}
    missing_units = {}
    missing_distro_files = {}
    for key in available_distro:
        if key in existing_distro_units:
            missing_distro_files[key] = []
            for ksfile in existing_distro_units[key].metadata.get("files"):
                distro_file_path = os.path.join(existing_distro_units[key].storage_path, ksfile["fileName"])
                if not util.verify_exists(distro_file_path, ksfile['checksum'],
                    ksfile['checksumtype'], verify_options):
                    _LOG.info("Missing an existing unit: %s.  Will add to resync." % distro_file_path)
                    # Adjust storage path to match intended location
                    # Grinder will use this 'pkgpath' to write the file
                    ksfile["pkgpath"] = os.path.dirname(distro_file_path)
                    missing_distro_files[key].append(ksfile)
                    missing_distro[key] = available_distro[key]
                    missing_units[key] = existing_distro_units[key]
    return missing_distro_files, missing_units

def form_lookup_distro_key(dinfo):
    dinfo_key = (dinfo["id"], dinfo["family"], dinfo["variant"],  dinfo["version"], dinfo["arch"])
    return dinfo_key

def form_distro_unit_key(distro):
    unit_key = {}
    for key in DISTRO_UNIT_KEY:
        unit_key[key] = distro[key]
    return unit_key

def form_distro_metadata(distro):
    metadata = {}
    for key in DISTRO_METADATA:
        metadata[key] = distro[key]
    return metadata



