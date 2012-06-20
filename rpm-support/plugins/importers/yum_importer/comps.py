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
Comps (Package Group/Category) Support for Yum Importer
"""
import gzip
import os
import sys
import time
import yum
import logging
from pulp_rpm.yum_plugin import comps_util, util
from pulp.server.managers.repo.unit_association_query import Criteria

_LOG = logging.getLogger(__name__)

PKG_GROUP_TYPE_ID="package_group"
PKG_CATEGORY_TYPE_ID="package_category"

#We are adding the 'repo_id' to unit_key for each group/category
#to ensure that each group/category is defined only for that given repo_id
#We do not want to allow sharing a single group or category between repos.
PKG_GROUP_UNIT_KEY = ("id", "repo_id")
PKG_GROUP_METADATA = (  "name", "description", "default", "user_visible", "langonly", "display_order", \
                        "mandatory_package_names", "conditional_package_names", 
                        "optional_package_names", "default_package_names", 
                        "translated_description", "translated_name")

PKG_CATEGORY_UNIT_KEY = ("id", "repo_id")
PKG_CATEGORY_METADATA = (   "name", "description", "display_order", "translated_name", "translated_description", \
                            "packagegroupids")

def form_group_unit_key(grp, repo_id):
    unit_key = {}
    for key in PKG_GROUP_UNIT_KEY:
        if key == "repo_id":
            unit_key["repo_id"] = repo_id
        else:
            unit_key[key] = grp[key]
    return unit_key

def form_group_metadata(grp):
    metadata = {}
    for key in PKG_GROUP_METADATA:
        metadata[key] = grp[key]
    return metadata

def form_category_unit_key(cat, repo_id):
    unit_key = {}
    for key in PKG_CATEGORY_UNIT_KEY:
        if key == "repo_id":
            unit_key["repo_id"] = repo_id
        else:
            unit_key[key] = cat[key]
    return unit_key

def form_category_metadata(cat):
    metadata = {}
    for key in PKG_CATEGORY_METADATA:
        metadata[key] = cat[key]
    return metadata

def get_orphaned_groups(available_groups, existing_groups):
    """
    @param available_groups a dict of groups
    @type available_groups {}

    @param existing_groups dict of units
    @type existing_groups {key:pulp.server.content.plugins.model.Unit}

    @return a dictionary of orphaned units, key is the group id and the value is the unit
    @rtype {key:pulp.server.content.plugins.model.Unit}
    """
    orphaned_groups = {}
    for key in existing_groups:
        if key not in available_groups:
            orphaned_groups[key] = existing_groups[key]
    return orphaned_groups

def get_orphaned_categories(available_categories, existing_categories):
    """
    @param available_categories a dict of categories
    @type available_categories {}

    @param existing_categories dict of units
    @type existing_categories {key:pulp.server.content.plugins.model.Unit}

    @return a dictionary of orphaned units, key is the category id and the value is the unit
    @rtype {key:pulp.server.content.plugins.model.Unit}
    """
    orphaned_categories = {}
    for key in existing_categories:
        if key not in available_categories:
            orphaned_categories[key] = existing_categories[key]
    return orphaned_categories

def get_new_category_units(available_categories, existing_categories, sync_conduit, repo):
    """
        Determines which categories to add or remove and will initialize new units

        @param available_categories a dict of available groups
        @type available_categories {}

        @param existing_categories dict of existing group Units
        @type existing_categories {pulp.server.content.plugins.model.Unit}

        @param sync_conduit
        @type sync_conduit pulp.server.content.conduits.repo_sync.RepoSyncConduit

        @param repo: metadata describing the repository
        @type  repo: L{pulp.server.content.plugins.data.Repository}

        @return a tuple of 2 dictionaries.  First dict is of new categories, second dict is of new units
        @rtype ({}, {}, pulp.server.content.conduits.repo_sync.RepoSyncConduit)
    """
    new_cats = {}
    new_units = {}
    for key in available_categories:
        if key not in existing_categories:
            cat = available_categories[key]
            new_cats[key] = cat
            unit_key  = form_category_unit_key(cat, repo.id)
            metadata =  form_category_metadata(cat)
            new_units[key] = sync_conduit.init_unit(PKG_CATEGORY_TYPE_ID, unit_key, metadata, None)
    return new_cats, new_units

def get_new_group_units(available_groups, existing_groups, sync_conduit, repo):
    """
        Determines which groups to add or remove and will initialize new units

        @param available_groups a dict of available groups
        @type available_groups {}

        @param existing_groups dict of existing group Units
        @type existing_groups {pulp.server.content.plugins.model.Unit}

        @param sync_conduit
        @type sync_conduit pulp.server.content.conduits.repo_sync.RepoSyncConduit

        @param repo: metadata describing the repository
        @type  repo: L{pulp.server.content.plugins.data.Repository}

        @return a tuple of 2 dictionaries.  First dict is of new groups, second dict is of new units
        @rtype ({}, {}, pulp.server.content.conduits.repo_sync.RepoSyncConduit)
    """
    new_groups = {}
    new_units = {}
    for key in available_groups:
        if key not in existing_groups:
            grp = available_groups[key]
            new_groups[key] = grp
            unit_key  = form_group_unit_key(grp, repo.id)
            metadata =  form_group_metadata(grp)
            new_units[key] = sync_conduit.init_unit(PKG_GROUP_TYPE_ID, unit_key, metadata, None)
    return new_groups, new_units

def get_groups_metadata_file(repo_dir, md_types=None):
    """
    @param repo_dir path to a repo
    @type repo_dir str 

    @param md_types May override the metadata type names, defaults to ['group', 'group_gz']
    @type md_types str

    @return path to group metadata file or None if repo doesn't have groups metadata, and the type, "group" or "group_gz"
    @rtype string, str
    """
    valid_md_types = ["group", "group_gz"]
    if md_types:
        valid_md_types = md_types
    repomd_xml = os.path.join(repo_dir, "repodata/repomd.xml")
    if not os.path.exists(repomd_xml):
        return None
    md_types = util.get_repomd_filetypes(repomd_xml)
    for ret_type in valid_md_types:
        if ret_type in md_types:
            ret_file = util.get_repomd_filetype_path(repomd_xml, ret_type)
            return ret_file, ret_type 
    return None, None

def get_available(repo_dir, md_types=None, group_file=None, group_type=None):
    """
    @param repo_dir path to a repository, expects 'repodata' to be a child of the path
    @type repo_dir str

    @param md_types May override the metadata type names, defaults to ['group', 'group_gz']
    @type md_types str

    @param group_file: optional path to override the comps.xml to parse
    @type group_file: str

    @param group_type: optional value to specify type of group_file, valid values are ['group', 'group_gz']
    @type group_type: str

    @return groups
    @rtype {}
    """
    comps_gzipped = None
    groups = {}
    categories = {}
    if not repo_dir \
            or not os.path.exists(os.path.join(repo_dir, "repodata")) \
            or not os.path.isdir(os.path.join(repo_dir, "repodata")):
        _LOG.info("Repo dir <%s> doesn't exist, skipping package group/category parsing" % (repo_dir))
        return groups, categories
    try:
        try:
            ####
            # We want to support _both_  'group' and 'group_gz' metadata types
            ####
            if group_file is None:
                group_file, group_type = get_groups_metadata_file(repo_dir, md_types)
            if group_file:
                group_file = os.path.join(repo_dir, group_file)
            yc = yum.comps.Comps()
            if group_type is None:
                # Assume regular comps.xml if no group_type was specified, value is 'group'
                group_type = "group"
            _LOG.debug("Parsing yum package group/category from metadata type '%s' with value %s" % (group_type, \
                    group_file))
            if group_file and group_type == "group":
                yc.add(group_file)
            elif group_file and group_type == "group_gz":
                comps_gzipped = gzip.GzipFile(group_file, 'r')
                yc.add(comps_gzipped)
            else:
                _LOG.info("No package group/category data found in <%s>" % (repo_dir))
                return groups, categories

            for g in yc.groups:
                grp = comps_util.yum_group_to_model_group(g)
                groups[grp["id"]] = grp
            for c in yc.categories:
                cat = comps_util.yum_category_to_model_category(c)
                categories[cat["id"]] = cat
            _LOG.info("Successfully parsed package group/category info from <%s> with %s groups and %s categories" % \
                    (repo_dir, len(groups), len(categories)))
            return groups, categories
        finally:
            if comps_gzipped:
                comps_gzipped.close()
    except yum.Errors.CompsException, e:
        _LOG.exception("Caught exception parsing comps data from: %s" % (group_file))
        raise

def get_existing_groups(sync_conduit):
    """
     Lookup existing package group units in pulp

     @param sync_conduit
     @type sync_conduit pulp.server.content.conduits.repo_sync.RepoSyncConduit

     @return a dictionary of existing units, dict key is the group_id
     @rtype {():pulp.server.content.plugins.model.Unit}
    """
    existing_units = {}
    criteria = Criteria(type_ids=PKG_GROUP_TYPE_ID)
    for u in sync_conduit.get_units(criteria=criteria):
        key = u.unit_key['id']
        existing_units[key] = u
    return existing_units

def get_existing_categories(sync_conduit):
    """
     Lookup existing package categories units in pulp

     @param sync_conduit
     @type sync_conduit pulp.server.content.conduits.repo_sync.RepoSyncConduit

     @return a dictionary of existing units, dict key is the category_id
     @rtype {():pulp.server.content.plugins.model.Unit}
    """
    existing_units = {}
    criteria = Criteria(type_ids=PKG_CATEGORY_TYPE_ID)
    for u in sync_conduit.get_units(criteria=criteria):
        key = u.unit_key['id']
        existing_units[key] = u
    return existing_units

class ImporterComps(object):
    def __init__(self):
        self.canceled = False

    def cancel_sync(self):
        self.canceled = True

    def sync(self, repo, sync_conduit, config, importer_progress_callback=None):
        """
          Invokes comps sync sequence importing:
           - package group metadata
           - package category metadata

          @param repo: metadata describing the repository
          @type  repo: L{pulp.server.content.plugins.data.Repository}

          @param sync_conduit
          @type sync_conduit pulp.server.content.conduits.repo_sync.RepoSyncConduit

          @param config: plugin configuration
          @type  config: L{pulp.server.content.plugins.config.PluginCallConfiguration}

          @param importer_progress_callback callback to report progress info to sync_conduit
          @type importer_progress_callback function

          @return a tuple of state, dict of sync summary and dict of sync details
          @rtype (bool, {}, {})
          Returns false only when an error occurs or we've been canceled. 
                  true is returned, even if no groups metadata was present.
        """
        def set_progress(status):
            if importer_progress_callback:
                importer_progress_callback("comps", status)

        skip_content_types = config.get("skip_content_types")
        if skip_content_types and "packagegroup" in skip_content_types:
            progress = {"state":"SKIPPED"}
            set_progress(progress)
            return True, {"skipped":"1"}, {}

        if self.canceled:
            return False, {}, {}

        repo_dir = "%s/%s" % (repo.working_dir, repo.id)
        progress = {
                "state":"IN_PROGRESS", 
                "num_available_groups":0,
                "num_available_categories":0,
                "num_existing_groups": 0,
                "num_existing_categories": 0,
                "num_orphaned_groups": 0,
                "num_orphaned_categories": 0,
                "num_new_groups": 0,
                "num_new_categories": 0}
        set_progress(progress)

        start = time.time()

        available_groups, available_categories = get_available(repo_dir)
        _LOG.info("Parsed comps data from <%s>: %s groups and %s categories are available in <%s>" % \
                (repo_dir, len(available_groups), len(available_categories), repo.id))

        existing_groups = get_existing_groups(sync_conduit)
        existing_categories = get_existing_categories(sync_conduit)
        _LOG.info("Existing package groups/categories from <%s>: %s groups, %s categories" % \
                (repo.id, len(existing_groups), len(existing_categories)))

        new_groups, new_group_units = get_new_group_units(available_groups, existing_groups, sync_conduit, repo)
        new_categories, new_category_units = get_new_category_units(available_categories, 
                existing_categories, sync_conduit, repo)
        ###
        # Save the new units
        ###
        for u in new_group_units.values():
            sync_conduit.save_unit(u)
        for u in new_category_units.values():
            sync_conduit.save_unit(u)
        ###
        # Clean up any orphaned units
        ###
        orphaned_group_units = get_orphaned_groups(available_groups, existing_groups)
        orphaned_category_units = get_orphaned_categories(available_categories, existing_categories)
        for u in orphaned_group_units.values():
            sync_conduit.remove_unit(u)
        for u in orphaned_category_units.values():
            sync_conduit.remove_unit(u)
        end = time.time()

        progress = {
                "state":"FINISHED", 
                "num_available_groups":len(available_groups),
                "num_available_categories":len(available_categories),
                "num_orphaned_groups": len(orphaned_group_units),
                "num_orphaned_categories": len(orphaned_category_units),
                "num_new_groups": len(new_groups),
                "num_new_categories": len(new_categories)}
        set_progress(progress)

        summary = dict()
        summary["num_available_groups"] = len(available_groups)
        summary["num_available_categories"] = len(available_categories)
        summary["num_new_groups"] = len(new_group_units)
        summary["num_new_categories"] = len(new_category_units)
        summary["num_orphaned_groups"] = len(orphaned_group_units)
        summary["num_orphaned_categories"] = len(orphaned_category_units)
        summary["time_total_sec"] = end - start

        details = dict()
        _LOG.info("Comps Summary: %s \n Details: %s" % (summary, details))
        return True, summary, details
