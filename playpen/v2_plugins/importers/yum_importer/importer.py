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
_LOG.addHandler(logging.FileHandler('/var/log/pulp/yum-importer.log'))

RPM_TYPE_ID="rpm"
YUM_IMPORTER_TYPE_ID="yum_importer"

REQUIRED_CONFIG_KEYS = ['feed_url']
OPTIONAL_CONFIG_KEYS = ['sslcacert', 'sslclientcert', 'sslclientkey', 'sslverify', 
                        'proxy_url', 'proxy_port', 'proxy_pass', 'proxy_user',
                        'max_speed', 'verify_options', 'num_threads']

RPM_UNIT_KEY = ("name", "epoch", "version", "release", "arch", "fileName", "checksum", "checksumtype")

class YumImporter(Importer):

    @classmethod
    def metadata(cls):
        return {
            'id'           : YUM_IMPORTER_TYPE_ID,
            'display_name' : 'Yum Importer',
            'types'        : [RPM_TYPE_ID]
        }

    def validate_config(self, repo, config):
        _LOG.info("validate_config invoked")
        _LOG.info("Config values are: %s" % (config.repo_plugin_config))
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
        start = time.time()
        _LOG.info("Sync repo <%s> from feed_url <%s>, with working_dir = <%s>" % (repo, config.get("feed_url"), repo.working_dir))
        repo_label = config.get("repo_label") or repo.id
        repo_url = config.get("feed_url")
        tmp_path = repo.working_dir
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
        ###
        # Determine existing units in repo
        ###
        existing_units = {}
        for u in sync_conduit.get_units():
            key = self.form_lookup_key(u.unit_key)
            existing_units[key] = u
        ###
        # Prepare repo and determine what rpms to sync
        ###
        _LOG.info("Determing what content to sync.")
        yumRepoGrinder = YumRepoGrinder(repo_label=repo_label, repo_url=repo_url, parallel=num_threads, \
            mirrors=None, newest=newest, cacert=cacert, clicert=clicert, clikey=clikey, \
            proxy_url=proxy_url, proxy_port=proxy_port, proxy_user=proxy_user, \
            proxy_pass=proxy_pass, sslverify=sslverify, packages_location="./", \
            remove_old=remove_old, numOldPackages=num_old_packages, skip=skip, max_speed=max_speed, \
            purge_orphaned=purge_orphaned, distro_location=None, tmp_path=tmp_path)
        yumRepoGrinder.setup(basepath=tmp_path)
        rpm_items = yumRepoGrinder.getRPMItems()
        ###
        # TODO: add support for delta rpms and distro files
        #  delta_rpm_items = yumRepoGrinder.getDeltaRPMItems()
        #  distro_items = yumRepoGrinder.getDistroItems()
        ###
        ###
        # Determine what is available
        ###
        available_rpms = {}
        for rpm in rpm_items:
            key = self.form_lookup_key(rpm)
            available_rpms[key] = rpm
        ###
        # What has been orphaned, or exists in Pulp but has been removed from the source repo
        ###
        orphaned_units = {}
        for key in existing_units:
            if key not in available_rpms:
                orphaned_units[key] = existing_units[key]
        ###
        # What are the new rpms we should sync
        # ..Verify existing rpms are present, resync if not
        ###
        new_rpms = {}
        missing_rpms = {}
        missing_units = {}
        for key in available_rpms:
            if key in existing_units:
                rpm_path = existing_units[key].storage_path
                if not self.verify_exists(rpm_path):
                    _LOG.info("Missing an existing unit: %s.  Will add to resync." % (rpm_path))
                    missing_rpms[key] = available_rpms[key]
                    missing_units[key] = existing_units[key]
            elif key not in existing_units:
                new_rpms[key] = available_rpms[key]
        proposed_units = {}
        ###
        # Adjust the download path
        ###
        for rpm in new_rpms.values():
            unit_key = self.form_rpm_unit_key(rpm)
            metadata = self.form_rpm_metadata(rpm)
            unit = sync_conduit.init_unit(RPM_TYPE_ID, unit_key, metadata, rpm["pkgpath"])
            rpm["pkgpath"] = unit.storage_path
            proposed_units[self.form_lookup_key(unit.unit_key)] = unit
        for key in missing_rpms:
            rpm = missing_rpms[key]
            unit = missing_units[key]
            rpm["pkgpath"] = unit.storage_path
        ###
        # Sync the new rpms
        ###
        _LOG.info("Plan to sync %s new rpms and resync %s missing rpms." % (len(new_rpms), len(missing_rpms)))
        yumRepoGrinder.addItems(new_rpms.values())
        yumRepoGrinder.addItems(missing_rpms.values())
        report = yumRepoGrinder.download()
        _LOG.info("Finished download of %s.  Report = %s" % (repo.id, report))
        # Verify we synced what we expected
        not_synced = {}
        for key in missing_rpms.keys():
            rpm = missing_rpms[key]
            if not self.verify_exists(rpm["pkgpath"]):
                not_synced[key] = rpm
                del missing_rpms[key]
        for key in new_rpms.keys():
            rpm = new_rpms[key]
            if not self.verify_exists(rpm["pkgpath"]):
                not_synced[key] = rpm
                del new_rpms[key]
        # Remove items not synced from proposed_units
        for key in not_synced:
            del proposed_units[key]
        ###
        # Save the new units
        ###
        for key in proposed_units:
            sync_conduit.save_unit(proposed_units[key])
        if not_synced:
            _LOG.info("%s packages have not been synced" % (len(not_synced)))
        ###
        # Remove the orphaned units
        ###
        for key, unit in orphaned_units.items():
            _LOG.info("Removing Orphaned Package: %s, %s" % (key, unit))
            sync_conduit.remove_unit(unit)
        end = time.time()
        summary =  "Synchronization Successful"
        details =  "Import Details\n"
        details += "Ellapsed time in seconds: %d\n" % (end - start)
        details += "%s new rpms imported" % (len(new_rpms))
        details += "%s existing rpms re-synchronized" % (len(missing_rpms))
        details += "%s rpms showed a problem and weren't downloaded" % (len(not_synced))
        details += "%s rpms were orphaned from the feed repository and removed" % (len(orphaned_units))
        return sync_conduit.build_report(summary, details)

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

    def verify_exists(self, file_path):
        return os.path.exists(file_path)
