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
Importer plugin for Yum functionality
"""

import logging
import os
import time

import pulp.server.util 
from grinder.RepoFetch import YumRepoGrinder
from pulp.server.content.plugins.importer import Importer

_LOG = logging.getLogger(__name__)
#TODO Fix up logging so we log to a separate file to aid debugging
#_LOG.addHandler(logging.FileHandler('/var/log/pulp/yum-importer.log'))

RPM_TYPE_ID="rpm"
YUM_IMPORTER_TYPE_ID="yum_importer"

REQUIRED_CONFIG_KEYS = ['feed_url']
OPTIONAL_CONFIG_KEYS = ['sslcacert', 'sslclientcert', 'sslclientkey', 'sslverify', 
                        'proxy_url', 'proxy_port', 'proxy_pass', 'proxy_user',
                        'max_speed', 'verify_options', 'num_threads']

RPM_UNIT_KEY = ("name", "epoch", "version", "release", "arch", "fileName", "checksum", "checksumtype")


class YumImporter(Importer):
    PROGRESS_REPORT_FIELDS = ["items_total", "items_left", "size_total", "size_left", 
                        "item_name", "status", "item_type", "num_error", "num_success", 
                        "num_download", "details", "error_details", "step"]

    @classmethod
    def metadata(cls):
        return {
            'id'           : YUM_IMPORTER_TYPE_ID,
            'display_name' : 'Yum Importer',
            'types'        : [RPM_TYPE_ID]
        }

    def validate_config(self, repo, config):
        _LOG.info("validate_config invoked, config values are: %s" % (config.repo_plugin_config))
        for key in REQUIRED_CONFIG_KEYS:
            if key not in config.repo_plugin_config:
                _LOG.error("Missing required configuration key: %s" % (key))
                return False
        for key in config.repo_plugin_config:
            if key not in REQUIRED_CONFIG_KEYS and key not in OPTIONAL_CONFIG_KEYS:
                _LOG.error("Configuration key '%s' is not supported" % (key))
                return False
        return True

    def importer_added(self, repo, config):
        _LOG.info("importer_added invoked")

    def importer_removed(self, repo, config):
        _LOG.info("importer_removed invoked")

    def import_units(self, repo, units, import_conduit, config):
        """
        Import content units into the given repository. This method will be
        called in a number of different situations:
         * A user is attempting to migrate a content unit from one repository
           into the repository that uses this importer
         * A user has uploaded a content unit to the Pulp server and is
           attempting to associate it to a repository that uses this importer
         * An existing repository is being cloned into a repository that
           uses this importer

        In all cases, the expected behavior is that the importer uses this call
        as an opportunity to perform any changes it needs to its working
        files for the repository to incorporate the new units.

        The units may or may not exist in Pulp prior to this call. The call to
        add a unit to Pulp is idempotent and should be made anyway to ensure
        the case where a new unit is being uploaded to Pulp is handled.

        @param repo: metadata describing the repository
        @type  repo: L{pulp.server.content.plugins.data.Repository}

        @param units: list of objects describing the units to import in
                      this call
        @type  units: list of L{pulp.server.content.plugins.data.Unit}

        @param import_conduit: provides access to relevant Pulp functionality
        @type  import_conduit: ?

        @param config: plugin configuration
        @type  config: L{pulp.server.content.plugins.config.PluginCallConfiguration}
        """
        _LOG.info("import_units invoked")

    def remove_units(self, repo, units, remove_conduit):
        _LOG.info("remove_units invoked for %s units" % (len(units)))

    # -- actions --------------------------------------------------------------

    def sync_repo(self, repo, sync_conduit, config):
        summary, details = self._sync_repo(repo, sync_conduit, config)
        return sync_conduit.build_report(summary, details)

    def _sync_repo(self, repo, sync_conduit, config):
        def progress_callback(report):
            """
            Translates grinders progress report to a dict Pulp can use
            @param report progress report
            @type report: grinder.GrinderCallback.ProgressReport
            """
            status = {}
            for f in self.PROGRESS_REPORT_FIELDS:
                status[f] = getattr(report, f)
            sync_conduit.set_progress(status)
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
        yumRepoGrinder = self.get_yumRepoGrinder(repo.id, repo.working_dir, config)
        yumRepoGrinder.setup(basepath=repo.working_dir, callback=progress_callback)
        rpm_items = yumRepoGrinder.getRPMItems()
        available_rpms = self.get_available_rpms(rpm_items)
        end_metadata = time.time()
        _LOG.info("%s rpms are available in the source repo <%s> for %s, calculated in %s seconds" % \
                (len(available_rpms), feed_url, repo.id, (end_metadata-start_metadata)))

        # Determine what exists and what has been orphaned, or exists in Pulp but has been removed from the source repo
        existing_units = self.get_existing_units(sync_conduit)
        orphaned_units = self.get_orphaned_units(available_rpms, existing_units)

        # Determine new and missing items
        new_rpms, new_units = self.get_new_rpms_and_units(available_rpms, existing_units, sync_conduit)
        missing_rpms, missing_units = self.get_missing_rpms_and_units(available_rpms, existing_units)
        _LOG.info("Repo <%s> %s existing units, %s have been orphaned, %s new rpms, %s missing rpms." % \
                (repo.id, len(existing_units), len(orphaned_units), len(new_rpms), len(missing_rpms)))

        # Sync the new and missing rpms
        yumRepoGrinder.addItems(new_rpms.values())
        yumRepoGrinder.addItems(missing_rpms.values())
        start_download = time.time()
        report = yumRepoGrinder.download()
        end_download = time.time()
        _LOG.info("Finished download of %s in % seconds.  %s" % (repo.id, end_download-start_download, report))
        # Verify we synced what we expected, update the passed in dicts to remove non-downloaded items
        not_synced = self.verify_download(missing_rpms, new_rpms, new_units)
        if not_synced:
            _LOG.warning("%s rpms were not downloaded" % (len(not_synced)))

        # Save the new units and remove the orphaned units
        for u in new_units.values():
            sync_conduit.save_unit(u)
        for u in orphaned_units.values():
            sync_conduit.remove_unit(u)

        end = time.time()
        summary = {}
        summary["num_synced_new_rpms"] = len(new_rpms)
        summary["num_resynced_rpms"] = len(missing_rpms)
        summary["num_not_synced_rpms"] = len(not_synced)
        summary["num_orphaned_rpms"] = len(orphaned_units)
        summary["time_total_sec"] = end - start

        details = {}
        details["size_total"] = report.last_progress.size_total
        details["time_metadata_sec"] = end_metadata - start_metadata
        details["time_download_sec"] = end_download - start_download
        details["not_synced"] = not_synced
        details["report"] = self.form_report(report)
        return summary, details

    def get_yumRepoGrinder(self, repo_id, tmp_path, config):
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
        repo_label = config.get("repo_label") or repo_id
        repo_url = config.get("feed_url")
        cacert = config.get("cacert")
        num_threads = config.get("num_threads") or 5
        clicert = config.get("clicert")
        clikey = config.get("clikey")
        proxy_url = config.get("proxy_url")
        proxy_port = config.get("proxy_port")
        proxy_user = config.get("proxy_user")
        proxy_pass = config.get("proxy_pass")
        sslverify = config.get("sslverify")
        max_speed = config.get("max_speed")
        verify_options = config.get("verify_options")
        newest = False
        remove_old = False
        purge_orphaned = True
        num_old_packages = 2
        skip = None
        yumRepoGrinder = YumRepoGrinder(repo_label=repo_label, repo_url=repo_url, parallel=num_threads, \
            mirrors=None, newest=newest, cacert=cacert, clicert=clicert, clikey=clikey, \
            proxy_url=proxy_url, proxy_port=proxy_port, proxy_user=proxy_user, \
            proxy_pass=proxy_pass, sslverify=sslverify, packages_location="./", \
            remove_old=remove_old, numOldPackages=num_old_packages, skip=skip, max_speed=max_speed, \
            purge_orphaned=purge_orphaned, distro_location=None, tmp_path=tmp_path)
        return yumRepoGrinder

    def get_existing_units(self, sync_conduit):
        """
        @param sync_conduit
        @type sync_conduit pulp.server.content.conduits.repo_sync.RepoSyncConduit

        @return a dictionary of existing units, key is the rpm lookup_key and the value is the unit
        @rtype {():pulp.server.content.plugins.model.Unit}
        """
        existing_units = {}
        for u in sync_conduit.get_units():
            key = self.form_lookup_key(u.unit_key)
            existing_units[key] = u
        return existing_units

    def get_available_rpms(self, rpm_items):
        """
        @param rpm_items list of dictionaries containing info on each rpm, see grinder.YumInfo.__getRPMs() for more info
        @type rpm_items [{}]

        @return a dictionary, key is the rpm lookup_key and the value is a dictionary with rpm info 
        @rtype {():{}}
        """
        available_rpms = {}
        for rpm in rpm_items:
            key = self.form_lookup_key(rpm)
            available_rpms[key] = rpm
        return available_rpms

    def get_orphaned_units(self, available_rpms, existing_units):
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

    def get_new_rpms_and_units(self, available_rpms, existing_units, sync_conduit):
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
                unit_key = self.form_rpm_unit_key(rpm)
                metadata = self.form_rpm_metadata(rpm)
                new_units[key] = sync_conduit.init_unit(RPM_TYPE_ID, unit_key, metadata, rpm["pkgpath"])
                # We need to determine where the unit should be stored and update
                # rpm["pkgpath"] so Grinder will store the rpm to the correct location
                rpm["pkgpath"] = new_units[key].storage_path
        return new_rpms, new_units

    def get_missing_rpms_and_units(self, available_rpms, existing_units):
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
                if not self.verify_exists(rpm_path):
                    _LOG.info("Missing an existing unit: %s.  Will add to resync." % (rpm_path))
                    missing_rpms[key] = available_rpms[key]
                    missing_units[key] = existing_units[key]
                    # Adjust storage path to match intended location
                    # Grinder will use this 'pkgpath' to write the file
                    missing_rpms[key]["pkgpath"] = missing_units[key].storage_path
        return missing_rpms, missing_units

    def form_rpm_unit_key(self, rpm):
        unit_key = {}
        for key in RPM_UNIT_KEY:
            unit_key[key] = rpm[key]
        return unit_key

    def form_rpm_metadata(self, rpm):
        metadata = {}
        for key in ("vendor", "description", "buildhost", "license", "vendor", "requires", "provides"):
            metadata[key] = rpm[key]
        return metadata

    def form_lookup_key(self, rpm):
        rpm_key = (rpm["name"], rpm["epoch"], rpm["version"], rpm["arch"], 
            rpm["fileName"], rpm["checksumtype"], rpm["checksum"])
        return rpm_key

    def form_report(self, report):
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

    def verify_download(self, missing_rpms, new_rpms, new_units):
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
            if not self.verify_exists(rpm["pkgpath"]):
                not_synced[key] = rpm
                del new_rpms[key]
        for key in missing_rpms.keys():
            rpm = missing_rpms[key]
            if not self.verify_exists(rpm["pkgpath"]):
                not_synced[key] = rpm
                del missing_rpms[key]
        for key in not_synced:
            del new_units[key]
        return not_synced

    def verify_exists(self, file_path):
        return os.path.exists(file_path)
