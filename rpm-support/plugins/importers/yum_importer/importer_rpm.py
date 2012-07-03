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
import itertools
from grinder.BaseFetch import BaseFetch
from grinder.GrinderCallback import ProgressReport
from grinder.RepoFetch import YumRepoGrinder
from pulp.server.managers.repo.unit_association_query import Criteria
from pulp_rpm.yum_plugin import util
from yum_importer import distribution, drpm

_LOG = logging.getLogger(__name__)
#_LOG.addHandler(logging.FileHandler('/var/log/pulp/yum-importer.log'))

RPM_TYPE_ID="rpm"
SRPM_TYPE_ID="srpm"
RPM_UNIT_KEY = ("name", "epoch", "version", "release", "arch", "checksum", "checksumtype")


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
            pkgpath = os.path.join(rpm["pkgpath"], metadata["filename"])
            if rpm['arch'] == 'src':
                # initialize unit as a src rpm
                new_units[key] = sync_conduit.init_unit(SRPM_TYPE_ID, unit_key, metadata, pkgpath)
            else:
                new_units[key] = sync_conduit.init_unit(RPM_TYPE_ID, unit_key, metadata, pkgpath)
            # We need to determine where the unit should be stored and update
            # rpm["pkgpath"] so Grinder will store the rpm to the correct location
            rpm["pkgpath"] = os.path.dirname(new_units[key].storage_path)
    return new_rpms, new_units

def get_missing_rpms_and_units(available_rpms, existing_units, verify_options={}):
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
            if not util.verify_exists(rpm_path, existing_units[key].unit_key.get('checksum'),
                existing_units[key].unit_key.get('checksumtype'), verify_options):
                _LOG.info("Missing an existing unit: %s.  Will add to resync." % (rpm_path))
                missing_rpms[key] = available_rpms[key]
                missing_units[key] = existing_units[key]
                # Adjust storage path to match intended location
                # Grinder will use this 'pkgpath' to write the file
                missing_rpms[key]["pkgpath"] = os.path.dirname(missing_units[key].storage_path)
    return missing_rpms, missing_units

def form_rpm_unit_key(rpm):
    unit_key = {}
    for key in RPM_UNIT_KEY:
        unit_key[key] = rpm[key]
    return unit_key

def form_rpm_metadata(rpm):
    metadata = {}
    for key in ("filename", "vendor", "description", "buildhost", "license", "vendor", "requires", "provides", "relativepath"):
        metadata[key] = rpm[key]
    return metadata

def form_lookup_key(rpm):
    rpm_key = (rpm["name"], rpm["epoch"], rpm["version"], rpm['release'], rpm["arch"], rpm["checksumtype"], rpm["checksum"])
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

def verify_download(missing_rpms, new_rpms, new_units, verify_options={}):
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
        _LOG.info("RPM object %s ; KEY : %s" % (rpm, key))
        if not util.verify_exists(rpm_path, rpm['checksum'], rpm['checksumtype'], rpm['size'], verify_options):
            not_synced[key] = rpm
            del new_rpms[key]
    for key in missing_rpms.keys():
        rpm = missing_rpms[key]
        rpm_path = os.path.join(rpm["pkgpath"], rpm["filename"])
        if not util.verify_exists(rpm_path, rpm['checksum'], rpm['checksumtype'], rpm['size'], verify_options):
            not_synced[key] = rpm
            del missing_rpms[key]
    for key in not_synced:
        del new_units[key]
    return not_synced

def force_ascii(value):
    retval = value
    if isinstance(value, unicode):
        retval = value.encode('ascii', 'ignore')
    return retval

def get_yumRepoGrinder(repo_id, repo_working_dir, config):
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
    proxy_url = force_ascii(config.get("proxy_url"))
    proxy_port = force_ascii(config.get("proxy_port"))
    proxy_user = force_ascii(config.get("proxy_user"))
    proxy_pass = force_ascii(config.get("proxy_pass"))
    sslverify = config.get("ssl_verify") or 0
    # Note ssl_ca_cert, ssl_client_cert, and ssl_client_key are all written in the main importer
    # int the validate_config method
    cacert = None
    if config.get("ssl_ca_cert"):
        cacert = os.path.join(repo_working_dir, "ssl_ca_cert").encode('utf-8')
    clicert = None
    if config.get("ssl_client_cert"):
        clicert = os.path.join(repo_working_dir, "ssl_client_cert").encode('utf-8')
    clikey = None
    if config.get("ssl_client_key"):
        clikey = os.path.join(repo_working_dir, "ssl_client_key").encode('utf-8')
    max_speed = config.get("max_speed")
    newest = config.get("newest") or False
    remove_old = config.get("remove_old") or False
    purge_orphaned = config.get("purge_orphaned") or True
    num_old_packages = config.get("num_old_packages") or 0
    skip = config.get("skip_content_types") or []
    yumRepoGrinder = YumRepoGrinder(repo_label=repo_label, repo_url=repo_url, parallel=num_threads,\
        mirrors=None, newest=newest, cacert=cacert, clicert=clicert, clikey=clikey,\
        proxy_url=proxy_url, proxy_port=proxy_port, proxy_user=proxy_user,\
        proxy_pass=proxy_pass, sslverify=sslverify, packages_location="./",\
        remove_old=remove_old, numOldPackages=num_old_packages, skip=skip, max_speed=max_speed,\
        purge_orphaned=purge_orphaned, distro_location=None, tmp_path=repo_working_dir)
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
    sym_link = os.path.join(repo.working_dir, repo.id, unit.metadata["filename"])
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

class ImporterRPM(object):
    def __init__(self):
        self.canceled = False
        self.yumRepoGrinder = None

    def sync(self, repo, sync_conduit, config, importer_progress_callback=None):
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

        def cleanup_error_details(error_details):
            for error in error_details:
                if error.has_key("exception"):
                    error["exception"] = str(error["exception"])
            return error_details

        def progress_callback(report):
            """
            @param report progress report from Grinder
            @type report: grinder.GrinderCallback.ProgressReport
            """
            status = {}
            if ProgressReport.DownloadItems in report.step:
                status = {}
                if report.status == "FINISHED":
                    if self.canceled:
                        status["state"] = "CANCELED"
                    else:
                        status["state"] = "FINISHED"
                else:
                    status["state"] = "IN_PROGRESS"
                status["num_success"] = report.num_success
                status["num_error"] = report.num_error
                status["size_left"] = report.size_left
                status["size_total"] = report.size_total
                status["items_left"] = report.items_left
                status["items_total"] = report.items_total
                status["error_details"] = cleanup_error_details(report.error_details)
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
        num_retries = config.get("num_retries")
        retry_delay = config.get("retry_delay")
        skip_content_types = config.get("skip") or []
        verify_checksum = config.get("verify_checksum") or False
        verify_size = config.get("verify_size") or False
        verify_options = {"checksum":verify_checksum, "size":verify_size}
        _LOG.info("Begin sync of repo <%s> from feed_url <%s>" % (repo.id, feed_url))
        start_metadata = time.time()
        self.yumRepoGrinder = get_yumRepoGrinder(repo.id, repo.working_dir, config)
        set_progress("metadata", {"state": "IN_PROGRESS"})
        try:
            self.yumRepoGrinder.setup(basepath=repo.working_dir, callback=progress_callback,
                num_retries=num_retries, retry_delay=retry_delay)
        except Exception, e:
            set_progress("metadata", {"state": "FAILED"})
            _LOG.error("Failed to fetch metadata on: %s" % (feed_url))
            raise
        set_progress("metadata", {"state": "FINISHED"})
        end_metadata = time.time()
        new_units = {}

        # ----------------- setup items to download and add to grinder ---------------
        # setup rpm items
        rpm_info = self._setup_rpms(repo, sync_conduit, verify_options, skip_content_types)
        new_units.update(rpm_info['new_rpm_units'])
        # Sync the new and missing rpms
        self.yumRepoGrinder.addItems(rpm_info['new_rpms'].values())
        self.yumRepoGrinder.addItems(rpm_info['missing_rpms'].values())

        # setup drpm items
        drpm_info = self._setup_drpms(repo, sync_conduit, verify_options, skip_content_types)
        new_units.update(drpm_info['new_drpm_units'])
        # Sync the new and missing drpms
        self.yumRepoGrinder.addItems(drpm_info['new_drpms'].values())
        self.yumRepoGrinder.addItems(drpm_info['missing_drpms'].values())

        # setup distribution items
        distro_info = self._setup_distros(repo, sync_conduit, verify_options, skip_content_types)
        new_units.update(distro_info['new_distro_units'])
        all_new_distro_files = list(itertools.chain(*distro_info['new_distro_files'].values()))
        # Sync the new and missing distro
        self.yumRepoGrinder.addItems(all_new_distro_files)
        all_missing_distro_files = list(itertools.chain(*distro_info['missing_distro_files'].values()))
        self.yumRepoGrinder.addItems(all_missing_distro_files)

        #----------- start the item download via grinder ---------------
        start_download = time.time()
        report = self.yumRepoGrinder.download()
        if self.canceled:
            _LOG.info("Sync of %s has been canceled." % repo.id)
            return False, {}, {}
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

        # -------------- process the download results to a report ---------------
        errors = {}
        not_synced = {}
        removal_errors = []
        summary = {}
        if 'rpm' not in skip_content_types:
            rpms_with_errors = search_for_errors(rpm_info['new_rpms'], rpm_info['missing_rpms'])
            errors.update(rpms_with_errors)
            # Verify we synced what we expected, update the passed in dicts to remove non-downloaded items
            not_synced = verify_download(rpm_info['missing_rpms'], rpm_info['new_rpms'], new_units, verify_options)
            # Save the new units and remove the orphaned units
            saved_new_unit_keys = []
            for key in new_units:
                if key not in rpms_with_errors:
                    u = new_units[key]
                    sync_conduit.save_unit(u)
                    saved_new_unit_keys.append(key)

            for u in rpm_info['orphaned_rpm_units'].values():
                try:
                    remove_unit(sync_conduit, repo, u)
                except Exception, e:
                    unit_info = str(u.unit_key)
                    _LOG.exception("Unable to remove: %s" % (unit_info))
                    removal_errors.append((unit_info, str(e)))
            # filter out rpm specific data if any
            new_rpms = filter(lambda u: u.type_id == 'rpm', rpm_info['new_rpm_units'].values())
            missing_rpms = filter(lambda u: u.type_id == 'rpm', rpm_info['missing_rpm_units'].values())
            orphaned_rpms = filter(lambda u: u.type_id == 'rpm', rpm_info['orphaned_rpm_units'].values())
            not_synced_rpms = filter(lambda r: r["arch"] != 'srpm', not_synced.values())

            summary["num_rpms"] = len(rpm_info['available_rpms'])
            summary["num_synced_new_rpms"] = len(new_rpms)
            summary["num_resynced_rpms"] = len(missing_rpms)
            summary["num_not_synced_rpms"] = len(not_synced_rpms)
            summary["num_orphaned_rpms"] = len(orphaned_rpms)
            summary["rpm_removal_errors"] = removal_errors

            # filter out srpm specific data if any
            new_srpms = filter(lambda u: u.type_id == 'srpm', rpm_info['new_rpm_units'].values())
            missing_srpms = filter(lambda u: u.type_id == 'srpm', rpm_info['missing_rpm_units'].values())
            orphaned_srpms = filter(lambda u: u.type_id == 'srpm', rpm_info['orphaned_rpm_units'].values())
            not_synced_srpms = filter(lambda r: r["arch"] == 'srpm', not_synced.values())

            summary["num_synced_new_srpms"] = len(new_srpms)
            summary["num_resynced_srpms"] = len(missing_srpms)
            summary["num_not_synced_srpms"] = len(not_synced_srpms)
            summary["num_orphaned_srpms"] = len(orphaned_srpms)
        else:
            _LOG.info("skipping rpm summary report")

        if not_synced:
            _LOG.warning("%s rpms were not downloaded" % (len(not_synced)))

        if 'drpm' not in skip_content_types:
            drpms_with_errors = search_for_errors(drpm_info['new_drpms'], drpm_info['missing_drpms'])
            errors.update(drpms_with_errors)
            # purge any orphaned drpms
            drpm.purge_orphaned_drpm_units(sync_conduit, repo, drpm_info['orphaned_drpm_units'].values())
            # filter out drpm specific data if any
            new_drpms = filter(lambda u: u.type_id == 'drpm', drpm_info['new_drpm_units'].values())
            missing_drpms = filter(lambda u: u.type_id == 'drpm', drpm_info['missing_drpm_units'].values())
            orphaned_drpms = filter(lambda u: u.type_id == 'drpm', drpm_info['orphaned_drpm_units'].values())

            summary["num_synced_new_drpms"] = len(new_drpms)
            summary["num_resynced_drpms"] = len(missing_drpms)
            summary["num_orphaned_drpms"] = len(orphaned_drpms)
        else:
            _LOG.info("skipping drpm summary report")

        if 'distribution' not in skip_content_types:
            # filter out distribution specific data if any
            summary["num_synced_new_distributions"] = len(distro_info['new_distro_units'])
            summary["num_synced_new_distributions_files"] = len(all_new_distro_files)
            summary["num_resynced_distributions"] = len(distro_info['missing_distro_units'])
            summary["num_resynced_distribution_files"] = len(all_missing_distro_files)
        else:
            _LOG.info("skipping distro summary report")
        end = time.time()
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

    def _setup_rpms(self, repo, sync_conduit, verify_options, skip_content_types):
        rpm_info = {'available_rpms' : {}, 'existing_rpm_units' : {}, 'orphaned_rpm_units' : {}, 'new_rpms' : {}, 'new_rpm_units' : {},'missing_rpms' : {}, 'missing_rpm_units' : {}}
        if 'rpm' in skip_content_types:
            _LOG.info("skipping rpm item setup")
            return rpm_info
        start_metadata = time.time()
        rpm_items = self.yumRepoGrinder.getRPMItems()
        rpm_info['available_rpms'] = get_available_rpms(rpm_items)
        end_metadata = time.time()
        _LOG.info("%s rpms are available in the source repo %s, calculated in %s seconds" % \
                    (len(rpm_info['available_rpms']), repo.id, (end_metadata-start_metadata)))

        # Determine what exists and what has been orphaned, or exists in Pulp but has been removed from the source repo
        criteria = Criteria(type_ids=[RPM_TYPE_ID, SRPM_TYPE_ID])
        rpm_info['existing_rpm_units'] = get_existing_units(sync_conduit, criteria)
        rpm_info['orphaned_rpm_units'] = get_orphaned_units(rpm_info['available_rpms'], rpm_info['existing_rpm_units'])

        # Determine new and missing items
        rpm_info['new_rpms'], rpm_info['new_rpm_units'] = get_new_rpms_and_units(rpm_info['available_rpms'], rpm_info['existing_rpm_units'], sync_conduit)
        rpm_info['missing_rpms'], rpm_info['missing_rpm_units'] = get_missing_rpms_and_units(rpm_info['available_rpms'], rpm_info['existing_rpm_units'], verify_options)
        _LOG.info("Repo <%s> %s existing units, %s have been orphaned, %s new rpms, %s missing rpms." % \
                    (repo.id, len(rpm_info['existing_rpm_units']), len(rpm_info['orphaned_rpm_units']), len(rpm_info['new_rpms']), len(rpm_info['missing_rpms'])))

        return rpm_info

    def _setup_drpms(self, repo, sync_conduit, verify_options, skip_content_types):
        # process deltarpms
        drpm_info = {'available_drpms' : {}, 'existing_drpm_units' : {}, 'orphaned_drpm_units' : {}, 'new_drpms' : {}, 'new_drpm_units' : {}, 'missing_drpms' : {}, 'missing_drpm_units' : {}}
        if 'drpm' in skip_content_types:
            _LOG.info("skipping drpm item setup")
            return drpm_info
        start_metadata = time.time()
        drpm_items = self.yumRepoGrinder.getDeltaRPMItems()
        _LOG.info("Delta RPMs to sync %s" % len(drpm_items))
        drpm_info['available_drpms'] =  drpm.get_available_drpms(drpm_items)
        drpm_info['existing_drpm_units'] = drpm.get_existing_drpm_units(sync_conduit)
        drpm_info['orphaned_drpm_units'] = get_orphaned_units(drpm_info['available_drpms'], drpm_info['existing_drpm_units'])
        end_metadata = time.time()
        _LOG.info("%s drpms are available in the source repo %s, calculated in %s seconds" %\
                  (len(drpm_info['available_drpms']), repo.id, (end_metadata-start_metadata)))

        # Determine new and missing items
        drpm_info['new_drpms'], drpm_info['new_drpm_units'] = drpm.get_new_drpms_and_units(drpm_info['available_drpms'], drpm_info['existing_drpm_units'], sync_conduit)
        drpm_info['missing_drpms'], drpm_info['missing_drpm_units'] = get_missing_rpms_and_units(drpm_info['available_drpms'], drpm_info['existing_drpm_units'], verify_options)
        _LOG.info("Repo <%s> %s existing units, %s have been orphaned, %s new drpms, %s missing drpms." %\
                  (repo.id, len(drpm_info['existing_drpm_units']), len(drpm_info['orphaned_drpm_units']), len(drpm_info['new_drpms']), len(drpm_info['missing_drpms'])))

        return drpm_info

    def _setup_distros(self, repo, sync_conduit, verify_options, skip_content_types):
        distro_info = {'available_distros' : {}, 'existing_distro_units' : {}, 'orphaned_distro_units' : {}, 'new_distro_files' : {}, 'new_distro_units' : {}, 'missing_distro_files' : {}, 'missing_distro_units' : []}
        if 'distribution' in skip_content_types:
            _LOG.info("skipping distribution item setup")
            return distro_info
        start_metadata = time.time()
        self.yumRepoGrinder.setupDistroInfo()
        distro_items = self.yumRepoGrinder.getDistroItems()
        distro_info['available_distros'] = distribution.get_available_distributions(distro_items)
        distro_info['existing_distro_units'] = distribution.get_existing_distro_units(sync_conduit)
        distro_info['orphaned_distro_units'] = []
        end_metadata = time.time()
        _LOG.info("%s distributions are available in the source repo %s, calculated in %s seconds" %\
                  (len(distro_info['available_distros']), repo.id, (end_metadata-start_metadata)))
        distro_info['new_distro_files'], distro_info['new_distro_units'] = distribution.get_new_distros_and_units(distro_info['available_distros'], distro_info['existing_distro_units'], sync_conduit)
        distro_info['missing_distro_files'], distro_info['missing_distro_units'] = distribution.get_missing_distros_and_units(distro_info['available_distros'], distro_info['existing_distro_units'], verify_options)
        _LOG.info("Repo <%s> %s existing units, %s have been orphaned, %s new distro files, %s missing distro." %\
                  (repo.id, len(distro_info['existing_distro_units']), len(distro_info['orphaned_distro_units']), len(distro_info['new_distro_files']), len(distro_info['missing_distro_files'])))
        return distro_info

    def cancel_sync(self):
        _LOG.info("cancel_sync invoked")
        self.canceled = True
        if self.yumRepoGrinder:
            _LOG.info("Telling grinder to stop syncing")
            self.yumRepoGrinder.stop()

