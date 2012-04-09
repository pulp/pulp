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

import logging
import os
import time

from grinder.BaseFetch import BaseFetch
from grinder.GrinderCallback import ProgressReport
from grinder.RepoFetch import YumRepoGrinder
from pulp.server.managers.repo.unit_association_query import Criteria
import drpm
from pulp.yum_plugin import util

_LOG = logging.getLogger(__name__)
#_LOG.addHandler(logging.FileHandler('/var/log/pulp/yum-importer.log'))

RPM_TYPE_ID="rpm"
SRPM_TYPE_ID="srpm"
RPM_UNIT_KEY = ("name", "epoch", "version", "release", "arch", "filename", "checksum", "checksumtype")


PROGRESS_REPORT_FIELDS = ["state", "items_total", "items_left", "size_total", "size_left", 
    "num_error", "num_success", "details", "error_details"]

def get_existing_units(sync_conduit, criteria=None):
   """
   @param sync_conduit
   @type sync_conduit pulp.server.content.conduits.repo_sync.RepoSyncConduit

   @return a dictionary of existing units, key is the rpm lookup_key and the value is the unit
   @rtype {():pulp.server.content.plugins.model.Unit}
   """
   existing_units = {}
   for u in sync_conduit.get_units(criteria):
       key = form_lookup_key(u.unit_key)
       existing_units[key] = u
   return existing_units

def get_available_rpms(rpm_items):
    """
    @param rpm_items list of dictionaries containing info on each rpm, see grinder.YumInfo.__getRPMs() for more info
    @type rpm_items [{}]

    @return a dictionary, key is the rpm lookup_key and the value is a dictionary with rpm info
    @rtype {():{}}
    """
    available_rpms = {}
    for rpm in rpm_items:
        key = form_lookup_key(rpm)
        available_rpms[key] = rpm
    return available_rpms

def get_orphaned_units(available_rpms, existing_units):
    """
    @param available_rpms a dict of rpms
    @type available_rpms {}

    @param existing_units dict of units
    @type existing_units {key:pulp.server.content.plugins.model.Unit}

    @return a dictionary of orphaned units, key is the rpm lookup_key and the value is the unit
    @rtype {key:pulp.server.content.plugins.model.Unit}
    """
    orphaned_units = {}
    for key in existing_units:
        if key not in available_rpms:
            orphaned_units[key] = existing_units[key]
    return orphaned_units

def get_new_rpms_and_units(available_rpms, existing_units, sync_conduit):
    """
    Determines what rpms are new and will initialize new units to match these rpms

    @param available_rpms a dict of available rpms
    @type available_rpms {}

    @param existing_units dict of existing Units
    @type existing_units {pulp.server.content.plugins.model.Unit}

    @param sync_conduit
    @type sync_conduit pulp.server.content.conduits.repo_sync.RepoSyncConduit

    @return a tuple of 2 dictionaries.  First dict is of missing rpms, second dict is of missing units
    @rtype ({}, {})
    """
    new_rpms = {}
    new_units = {}
    for key in available_rpms:
        if key not in existing_units:
            rpm = available_rpms[key]
            new_rpms[key] = rpm
            unit_key = form_rpm_unit_key(rpm)
            metadata = form_rpm_metadata(rpm)
            pkgpath = os.path.join(rpm["pkgpath"], rpm["filename"])
            if rpm['arch'] == 'src':
                # initialize unit as a src rpm
                new_units[key] = sync_conduit.init_unit(SRPM_TYPE_ID, unit_key, metadata, pkgpath)
            else:
                new_units[key] = sync_conduit.init_unit(RPM_TYPE_ID, unit_key, metadata, pkgpath)
            # We need to determine where the unit should be stored and update
            # rpm["pkgpath"] so Grinder will store the rpm to the correct location
            rpm["pkgpath"] = os.path.dirname(new_units[key].storage_path)
    return new_rpms, new_units

def get_missing_rpms_and_units(available_rpms, existing_units):
    """
    @param available_rpms dict of available rpms
    @type available_rpms {}

    @param existing_units dict of existing Units
    @type existing_units {key:pulp.server.content.plugins.model.Unit}

    @return a tuple of 2 dictionaries.  First dict is of missing rpms, second dict is of missing units
    @rtype ({}, {})
    """
    missing_rpms = {}
    missing_units = {}
    for key in available_rpms:
        if key in existing_units:
            rpm_path = existing_units[key].storage_path
            if not verify_exists(rpm_path):
                _LOG.info("Missing an existing unit: %s.  Will add to resync." % (rpm_path))
                missing_rpms[key] = available_rpms[key]
                missing_units[key] = existing_units[key]
                # Adjust storage path to match intended location
                # Grinder will use this 'pkgpath' to write the file
                missing_rpms[key]["pkgpath"] = missing_units[key].storage_path
    return missing_rpms, missing_units

def form_rpm_unit_key(rpm):
    unit_key = {}
    for key in RPM_UNIT_KEY:
        unit_key[key] = rpm[key]
    return unit_key

def form_rpm_metadata(rpm):
    metadata = {}
    for key in ("vendor", "description", "buildhost", "license", "vendor", "requires", "provides", "relativepath"):
        metadata[key] = rpm[key]
    return metadata

def form_lookup_key(rpm):
    rpm_key = (rpm["name"], rpm["epoch"], rpm["version"], rpm["arch"],
        rpm["filename"], rpm["checksumtype"], rpm["checksum"])
    return rpm_key

def form_report(report):
    """
    @param report grinder synchronization report
    @type report grinder.ParallelFetch.SyncReport

    @return dict
    @rtype dict
    """
    ret_val = {}
    ret_val["successes"] = report.successes
    ret_val["downloads"] = report.downloads
    ret_val["errors"] = report.errors
    ret_val["details"] = report.last_progress.details
    ret_val["error_details"] = report.last_progress.error_details
    ret_val["items_total"] = report.last_progress.items_total
    ret_val["items_left"] = report.last_progress.items_left
    ret_val["size_total"] = report.last_progress.size_total
    ret_val["size_left"] = report.last_progress.size_left
    return ret_val

def verify_download(missing_rpms, new_rpms, new_units):
    """
    Will verify that intended items have been downloaded.
    Items not downloaded will be removed from passed in dicts

    @param missing_rpms dict of rpms determined to be missing from repo prior to sync
    @type missing_rpms {}

    @param new_rpms dict of rpms determined to be new to repo prior to sync
    @type new_rpms {}

    @param new_units
    @type new_units {key:pulp.server.content.plugins.model.Unit}

    @return dict of rpms which have not been downloaded
    @rtype {}
    """
    not_synced = {}
    for key in new_rpms.keys():
        rpm = new_rpms[key]
        rpm_path = os.path.join(rpm["pkgpath"], rpm["filename"])
        if not verify_exists(rpm_path):
            not_synced[key] = rpm
            del new_rpms[key]
    for key in missing_rpms.keys():
        rpm = missing_rpms[key]
        rpm_path = os.path.join(rpm["pkgpath"], rpm["filename"])
        if not verify_exists(rpm_path):
            not_synced[key] = rpm
            del missing_rpms[key]
    for key in not_synced:
        del new_units[key]
    return not_synced

def verify_exists(file_path):
    return os.path.exists(file_path)


def get_yumRepoGrinder(repo_id, tmp_path, config):
    """
    @param repo_id repo id
    @type repo_id str

    @param tmp_path temporary path for sync
    @type tmp_path str

    @param config plugin config parameters
    @param config pulp.server.content.plugins.config.PluginCallConfiguration

    @return an instantiated YumRepoGrinder instance
    @rtype grinder.RepoFetch.YumRepoGrinder
    """
    repo_label = repo_id
    repo_url = config.get("feed_url")
    num_threads = config.get("num_threads") or 5
    proxy_url = config.get("proxy_url")
    proxy_port = config.get("proxy_port")
    proxy_user = config.get("proxy_user")
    proxy_pass = config.get("proxy_pass")
    sslverify = config.get("ssl_verify")
    cacert = config.get("ssl_ca_cert")
    clicert = config.get("ssl_client_cert")
    clikey = config.get("ssl_client_key")
    max_speed = config.get("max_speed")
    verify_checksum = config.get("verify_checksum") or False
    verify_size = config.get("verify_size") or False
    verify_options = {"checksum":verify_checksum, "size":verify_size}
    newest = config.get("newest") or False
    remove_old = config.get("remove_old") or False
    purge_orphaned = config.get("purge_orphaned") or True
    num_old_packages = config.get("num_old_packages") or 0
    skip = config.get("skip")
    yumRepoGrinder = YumRepoGrinder(repo_label=repo_label, repo_url=repo_url, parallel=num_threads,\
        mirrors=None, newest=newest, cacert=cacert, clicert=clicert, clikey=clikey,\
        proxy_url=proxy_url, proxy_port=proxy_port, proxy_user=proxy_user,\
        proxy_pass=proxy_pass, sslverify=sslverify, packages_location="./",\
        remove_old=remove_old, numOldPackages=num_old_packages, skip=skip, max_speed=max_speed,\
        purge_orphaned=purge_orphaned, distro_location=None, tmp_path=tmp_path)
    return yumRepoGrinder

def _search_for_error(rpm_dict):
    errors = {}
    for key in rpm_dict:
        if rpm_dict[key].has_key("error"):
            _LOG.debug("Saw an error with: %s" % (rpm_dict[key]))
            errors[key] = rpm_dict[key]
    return errors

def search_for_errors(new_rpms, missing_rpms):
    errors = {}
    errors.update(_search_for_error(new_rpms))
    errors.update(_search_for_error(missing_rpms))
    return errors

def remove_unit(sync_conduit, repo, unit):
    """
    @param sync_conduit
    @type sync_conduit L{pulp.server.content.conduits.repo_sync.RepoSyncConduit}

    @param repo
    @type repo  L{pulp.server.content.plugins.data.Repository}

    @param unit
    @type unit L{pulp.server.content.plugins.model.Unit}
    
    Goals:
     1) Remove the unit from the database
     2) Remove the unit from the file system
     3) Remove the symlink stored under the repo.workingdir
    """
    _LOG.info("Removing unit <%s>" % (unit))
    sync_conduit.remove_unit(unit)
    error = False
    sym_link = os.path.join(repo.working_dir, repo.id, unit.unit_key["filename"])
    paths = [unit.storage_path, sym_link]
    for f in paths:
        if os.path.lexists(f):
            _LOG.debug("Delete: %s" % (f))
            os.unlink(f)


def set_repo_checksum_type(repo, sync_conduit, config):
    """
      At this point we have downloaded the source metadata from a remote or local feed
      lets lookup the checksum type for primary xml in repomd.xml and use that for createrepo

      @param repo: metadata describing the repository
      @type  repo: L{pulp.server.content.plugins.data.Repository}

      @param sync_conduit
      @type sync_conduit pulp.server.content.conduits.repo_sync.RepoSyncConduit

      @param config: plugin configuration
      @type  config: L{pulp.server.content.plugins.config.PluginCallConfiguration}
    """
    _LOG.debug('Determining checksum type for repo %s' % repo.id)
    checksum_type = config.get('checksum_type')
    if checksum_type:
        if not util.is_valid_checksum_type(checksum_type):
            _LOG.error("Invalid checksum type [%s]" % checksum_type)
            raise
    else:
        repo_metadata = os.path.join(repo.working_dir, repo.id, "repodata/repomd.xml")
        if os.path.exists(repo_metadata):
            checksum_type = util.get_repomd_filetype_dump(repo_metadata)['primary']['checksum'][0]
            _LOG.debug("got checksum type from repo %s " % checksum_type)
        else:
            # default to sha256 if nothing is found
            checksum_type = "sha256"
            _LOG.debug("got checksum type default %s " % checksum_type)

    # set repo checksum type on the scratchpad for distributor to lookup
    sync_conduit.set_repo_scratchpad(dict(checksum_type=checksum_type))
    _LOG.info("checksum type info [%s] set to repo scratchpad" % sync_conduit.get_repo_scratchpad())

def _sync(repo, sync_conduit, config, importer_progress_callback=None):
    """
      Invokes RPM sync sequence

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
    """

    def set_progress(type_id, status):
        if importer_progress_callback:
            importer_progress_callback(type_id, status)

    def progress_callback(report):
        """
        @param report progress report from Grinder
        @type report: grinder.GrinderCallback.ProgressReport 
        """
        status = {}
        if ProgressReport.DownloadItems in report.step:
            status = {}
            if report.status == "FINISHED":
                status["state"] = "FINISHED"
            else:
                status["state"] = "IN_PROGRESS"
            status["num_success"] = report.num_success 
            status["num_error"] = report.num_error
            status["size_left"] = report.size_left
            status["size_total"] = report.size_total
            status["items_left"] = report.items_left
            status["items_total"] = report.items_total
            status["error_details"] = report.error_details
            status["details"] = {}
            if report.details:
                for key in report.details.keys():
                    status["details"][key] = {}
                    status["details"][key]["num_success"] = report.details[key]["num_success"]
                    status["details"][key]["num_error"] = report.details[key]["num_error"]
                    status["details"][key]["size_left"] = report.details[key]["size_left"]
                    status["details"][key]["size_total"] = report.details[key]["total_size_bytes"]
                    status["details"][key]["items_left"] = report.details[key]["items_left"]
                    status["details"][key]["items_total"] = report.details[key]["total_count"]
            expected_details = (BaseFetch.RPM, BaseFetch.DELTA_RPM, BaseFetch.TREE_FILE, BaseFetch.FILE)
            for key in expected_details:
                if key not in status["details"].keys():
                    status["details"][key] = {}
                    status["details"][key]["num_success"] = 0
                    status["details"][key]["num_error"] = 0
                    status["details"][key]["size_left"] = 0
                    status["details"][key]["size_total"] = 0
                    status["details"][key]["items_left"] = 0
                    status["details"][key]["items_total"] = 0

            set_progress("content", status)

    ####
        # Syncs operate on 2 types of data structures
        # 1) RPM info, each 'rpm' is a single dictionary of key/value pairs created in grinder.YumInfo.__getRPMs()
        # 2) Pulp's Unit model, pulp.server.content.plugins.model.Unit
        #
        # Grinder talks in rpms
        # Pulp talks in Units
    ####
    start = time.time()
    feed_url = config.get("feed_url")
    _LOG.info("Begin sync of repo <%s> from feed_url <%s>" % (repo.id, feed_url))
    start_metadata = time.time()
    yumRepoGrinder = get_yumRepoGrinder(repo.id, repo.working_dir, config)
    set_progress("metadata", {"state": "IN_PROGRESS"})
    try:
        yumRepoGrinder.setup(basepath=repo.working_dir, callback=progress_callback)
    except Exception, e:
        set_progress("metadata", {"state": "FAILED"})
        _LOG.error("Failed to fetch metadata on: %s" % (feed_url))
        raise
    set_progress("metadata", {"state": "FINISHED"})

    rpm_items = yumRepoGrinder.getRPMItems()
    available_rpms = get_available_rpms(rpm_items)
    end_metadata = time.time()
    _LOG.info("%s rpms are available in the source repo <%s> for %s, calculated in %s seconds" % \
                (len(available_rpms), feed_url, repo.id, (end_metadata-start_metadata)))

    # Determine what exists and what has been orphaned, or exists in Pulp but has been removed from the source repo
    criteria = Criteria(type_ids=[RPM_TYPE_ID, SRPM_TYPE_ID, drpm.DRPM_TYPE_ID])
    existing_units = get_existing_units(sync_conduit, criteria)
    orphaned_units = get_orphaned_units(available_rpms, existing_units)

    # Determine new and missing items
    new_rpms, new_units = get_new_rpms_and_units(available_rpms, existing_units, sync_conduit)
    missing_rpms, missing_units = get_missing_rpms_and_units(available_rpms, existing_units)
    _LOG.info("Repo <%s> %s existing units, %s have been orphaned, %s new rpms, %s missing rpms." % \
                (repo.id, len(existing_units), len(orphaned_units), len(new_rpms), len(missing_rpms)))

    # process deltarpms
    drpm_items = yumRepoGrinder.getDeltaRPMItems()
    _LOG.info("Delta RPMs to sync %s" % len(drpm_items))
    available_drpms =  drpm.get_available_drpms(drpm_items)
    existing_drpm_units = filter(lambda u: u.type_id == 'drpm', existing_units.values())
    orphaned_drpm_units = get_orphaned_units(available_drpms, existing_drpm_units)
    end_metadata = time.time()
    _LOG.info("%s drpms are available in the source repo <%s> for %s, calculated in %s seconds" % \
                (len(available_drpms), feed_url, repo.id, (end_metadata-start_metadata)))

    # Determine new and missing items
    new_drpms, new_drpm_units = drpm.get_new_drpms_and_units(available_drpms, existing_units, sync_conduit)
    missing_drpms, missing_drpm_units = get_missing_rpms_and_units(available_drpms, existing_units)
    _LOG.info("Repo <%s> %s existing units, %s have been orphaned, %s new drpms, %s missing drpms." % \
                (repo.id, len(existing_units), len(orphaned_drpm_units), len(new_drpms), len(missing_drpms)))
    # include new drpm units 
    new_units.update(new_drpm_units)
    # include any orphaned drpm units
    orphaned_units.update(orphaned_drpm_units)
    # Sync the new and missing rpms, drpms
    yumRepoGrinder.addItems(new_rpms.values())
    yumRepoGrinder.addItems(missing_rpms.values())
    yumRepoGrinder.addItems(new_drpms.values())
    yumRepoGrinder.addItems(missing_drpms.values())
    start_download = time.time()
    report = yumRepoGrinder.download()
    end_download = time.time()
    _LOG.info("Finished download of %s in % seconds.  %s" % (repo.id, end_download-start_download, report))
    # determine the checksum type from downloaded metadata
    set_repo_checksum_type(repo, sync_conduit, config)
    # store the importer working dir on scratchpad to lookup downloaded data
    importer_working_repo_dir = os.path.join(repo.working_dir, repo.id)
    if os.path.exists(importer_working_repo_dir):
        existing_scratch_pad = sync_conduit.get_repo_scratchpad() or {}
        existing_scratch_pad.update({'importer_working_dir' : importer_working_repo_dir})
        sync_conduit.set_repo_scratchpad(existing_scratch_pad)
    rpms_with_errors = search_for_errors(new_rpms, missing_rpms)
    drpms_with_errors = search_for_errors(new_drpms, missing_drpms)
    rpms_with_errors.update(drpms_with_errors)
    # TODO: Re-examine verify_download(), most likely remove and keep this functionality in grinder
    # Verify we synced what we expected, update the passed in dicts to remove non-downloaded items
    not_synced = verify_download(missing_rpms, new_rpms, new_units)
    if not_synced:
        _LOG.warning("%s rpms were not downloaded" % (len(not_synced)))

    # Save the new units and remove the orphaned units
    saved_new_unit_keys = []
    for key in new_units:
        if key not in rpms_with_errors:
            u = new_units[key]
            sync_conduit.save_unit(u)
            saved_new_unit_keys.append(key)

    removal_errors = []
    for u in orphaned_units.values():
        try:
            remove_unit(sync_conduit, repo, u)
        except Exception, e:
            unit_info = str(u.unit_key)
            _LOG.exception("Unable to remove: %s" % (unit_info))
            removal_errors.append((unit_info, str(e)))
    end = time.time()

    # filter out rpm specific data if any
    new_rpms = filter(lambda u: u.type_id == 'rpm', new_units.values())
    missing_rpms = filter(lambda u: u.type_id == 'rpm', missing_units.values())
    orphaned_rpms = filter(lambda u: u.type_id == 'rpm', orphaned_units.values())
    not_synced_rpms = filter(lambda r: r["arch"] != 'srpm', not_synced.values())

    # TODO: Need to revisit what we report in Summary and Details
    summary = {}
    summary["num_rpms"] = len(available_rpms)
    summary["num_synced_new_rpms"] = len(new_rpms)
    summary["num_resynced_rpms"] = len(missing_rpms)
    summary["num_not_synced_rpms"] = len(not_synced_rpms)
    summary["num_orphaned_rpms"] = len(orphaned_rpms)
    summary["rpm_removal_errors"] = removal_errors

    # filter out srpm specific data if any
    new_srpms = filter(lambda u: u.type_id == 'srpm', new_units.values())
    missing_srpms = filter(lambda u: u.type_id == 'srpm', missing_units.values())
    orphaned_srpms = filter(lambda u: u.type_id == 'srpm', orphaned_units.values())
    not_synced_srpms = filter(lambda r: r["arch"] == 'srpm', not_synced.values())

    summary["num_synced_new_srpms"] = len(new_srpms)
    summary["num_resynced_srpms"] = len(missing_srpms)
    summary["num_not_synced_srpms"] = len(not_synced_srpms)
    summary["num_orphaned_srpms"] = len(orphaned_srpms)

    # filter out drpm specific data if any
    new_drpms = filter(lambda u: u.type_id == 'drpm', new_units.values())
    missing_drpms = filter(lambda u: u.type_id == 'drpm', missing_units.values())
    orphaned_drpms = filter(lambda u: u.type_id == 'drpm', orphaned_units.values())

    summary["num_synced_new_drpms"] = len(new_drpms)
    summary["num_resynced_drpms"] = len(missing_drpms)
    summary["num_orphaned_drpms"] = len(orphaned_drpms)

    summary["time_total_sec"] = end - start

    details = {}
    details["size_total"] = report.last_progress.size_total
    details["time_metadata_sec"] = end_metadata - start_metadata
    details["time_download_sec"] = end_download - start_download
    details["not_synced"] = not_synced
    details["sync_report"] = form_report(report)

    status = True
    if removal_errors or details["sync_report"]["errors"]:
        status = False
    _LOG.info("STATUS: %s; SUMMARY: %s; DETAILS: %s" % (status, summary, details))
    return status, summary, details
