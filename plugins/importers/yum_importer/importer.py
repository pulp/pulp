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
import gettext
import logging
import time

import drpm
import errata
import importer_rpm
from pulp.server.content.plugins.importer import Importer

_ = gettext.gettext
_LOG = logging.getLogger(__name__)
#TODO Fix up logging so we log to a separate file to aid debugging
#_LOG.addHandler(logging.FileHandler('/var/log/pulp/yum-importer.log'))

YUM_IMPORTER_TYPE_ID="yum_importer"

REQUIRED_CONFIG_KEYS = ['feed_url']
OPTIONAL_CONFIG_KEYS = ['ssl_verify', 'ssl_ca_cert', 'ssl_client_cert', 'ssl_client_key',
                        'proxy_url', 'proxy_port', 'proxy_pass', 'proxy_user',
                        'max_speed', 'verify_size', 'verify_checksum', 'num_threads',
                        'newest', 'remove_old', 'num_old_packages', 'purge_orphaned', 'skip', 'checksum_type']
###
# Config Options Explained
###
# feed_url: Repository URL
# ssl_verify: True/False to control if yum/curl should perform SSL verification of the host
# ssl_ca_cert: Path to SSL CA certificate used for ssl verification
# ssl_client_cert: Path to SSL Client certificate, used for protected repository access
# ssl_client_key: Path to SSL Client key, used for protected repository access
# proxy_url: Proxy URL 
# proxy_port: Port Port
# proxy_user: Username for Proxy
# proxy_pass: Password for Proxy
# max_speed: Limit the Max speed in KB/sec per thread during package downloads
# verify_checksum: if True will verify the checksum for each existing package repo metadata
# verify_size: if True will verify the size for each existing package against repo metadata
# num_threads: Controls number of threads to use for package download (technically number of processes spawned)
# newest: Boolean option, if True only download the latest packages
# remove_old: Boolean option, if True remove old packages
# num_old_packages: Defaults to 0, controls how many old packages to keep if remove_old is True
# purge_orphaned: Defaults to True, when True will delete packages no longer available from the source repository
# skip: Dictionary of what content types to skip during sync, options: {"packages", "distribution"}

class YumImporter(Importer):
    @classmethod
    def metadata(cls):
        return {
            'id'           : YUM_IMPORTER_TYPE_ID,
            'display_name' : 'Yum Importer',
            'types'        : [importer_rpm.RPM_TYPE_ID, importer_rpm.SRPM_TYPE_ID, errata.ERRATA_TYPE_ID, drpm.DRPM_TYPE_ID]
        }

    def validate_config(self, repo, config):
        _LOG.info("validate_config invoked, config values are: %s" % (config.repo_plugin_config))
        for key in REQUIRED_CONFIG_KEYS:
            if key not in config.repo_plugin_config:
                msg = _("Missing required configuration key: %(key)s" % {"key":key})
                _LOG.error(msg)
                return False, msg
        for key in config.repo_plugin_config:
            if key not in REQUIRED_CONFIG_KEYS and key not in OPTIONAL_CONFIG_KEYS:
                msg = _("Configuration key '%(key)s' is not supported" % {"key":key})
                _LOG.error(msg)
                return False, msg
        return True, None

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
        try:
            status, summary, details = self._sync_repo(repo, sync_conduit, config)
            if status:
                report = sync_conduit.build_success_report(summary, details)
            else:
                report = sync_conduit.build_failure_report(summary, details)
        except Exception, e:
            _LOG.error("Caught Exception: %s" % (e))
            summary = {}
            summary["error"] = str(e)
            report = sync_conduit.build_failure_report(summary, None)
        return report

    def _sync_repo(self, repo, sync_conduit, config):
        progress_status = {
                "metadata": {"state": "NOT_STARTED"},
                "content": {"state": "NOT_STARTED"},
                "errata": {"state": "NOT_STARTED", "num_errata":0}
                }
        def progress_callback(type_id, status):
            if type_id == "content":
                progress_status["metadata"]["state"] = "FINISHED"
                
            progress_status[type_id] = status
            sync_conduit.set_progress(progress_status)

        # sync rpms
        rpm_status, rpm_summary, rpm_details = importer_rpm._sync(repo, sync_conduit, config, progress_callback)
        progress_status["content"]["state"] = "FINISHED"
        sync_conduit.set_progress(progress_status)

        # sync errata
        errata_status, errata_summary, errata_details = errata._sync(repo, sync_conduit, config, progress_callback)
        progress_status["errata"]["state"] = "FINISHED"
        sync_conduit.set_progress(progress_status)

        summary = dict(rpm_summary.items() + errata_summary.items())
        details = dict(rpm_details.items() + errata_details.items())
        return (rpm_status and errata_status), summary, details

