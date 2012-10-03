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

import os
import gettext
import shutil
import time

from pulp_rpm.yum_plugin import util, metadata, updateinfo
from pulp.plugins.distributor import GroupDistributor
from iso_distributor.generate_iso import GenerateIsos
from iso_distributor.exporter import RepoExporter
from iso_distributor import iso_util
from pulp.server.db.model.criteria import UnitAssociationCriteria
from pulp_rpm.common.ids import TYPE_ID_DISTRIBUTOR_ISO, TYPE_ID_DISTRO, TYPE_ID_DRPM, \
    TYPE_ID_ERRATA, TYPE_ID_PKG_GROUP, TYPE_ID_PKG_CATEGORY, TYPE_ID_RPM, TYPE_ID_SRPM
from pulp_rpm.yum_plugin import comps_util

_LOG = util.getLogger(__name__)
_ = gettext.gettext

REQUIRED_CONFIG_KEYS = ["http", "https"]
OPTIONAL_CONFIG_KEYS = ["https_ca", "https_publish_dir","http_publish_dir", "start_date", "end_date", "iso_prefix", "skip"]


###
# Config Options Explained
###
# http                  - True/False:  Publish through http
# https                 - True/False:  Publish through https
# https_ca              - CA to verify https communication
# start_date            - errata start date format eg: "2009-03-30 00:00:00"
# end_date              - errata end date format eg: "2009-03-30 00:00:00"
# http_publish_dir      - Optional parameter to override the HTTP_PUBLISH_DIR
# https_publish_dir     - Optional parameter to override the HTTPS_PUBLISH_DIR
# skip                  - List of what content types to skip during export, options:
#                         ["rpm", "errata", "distribution", "packagegroup"]
# iso_prefix            - prefix to use in the generated iso naming, default: <repoid>-<current_date>.iso

# -- plugins ------------------------------------------------------------------

class GroupISODistributor(GroupDistributor):

    def __init__(self):
        super(GroupISODistributor, self).__init__()
        self.canceled = False
        self.group_summary = {}
        self.group_details = {}
        self.group_progress_status = {}

    @classmethod
    def metadata(cls):
        return {
            'id'           : TYPE_ID_DISTRIBUTOR_ISO,
            'display_name' : _('Iso Distributor'),
            'types'        : [TYPE_ID_RPM, TYPE_ID_SRPM, TYPE_ID_DRPM, TYPE_ID_ERRATA,
                              TYPE_ID_DISTRO, TYPE_ID_PKG_CATEGORY, TYPE_ID_PKG_GROUP]
        }

    def init_progress(self):
        return  {
            "state": "IN_PROGRESS",
            "num_success" : 0,
            "num_error" : 0,
            "items_left" : 0,
            "items_total" : 0,
            "error_details" : [],
            }

    def validate_config(self, repo, config, related_repos):
        """
        see parent class for the doc string
        """
        _LOG.info("validate_config invoked, config values are: %s" % (config.repo_plugin_config))
        for key in REQUIRED_CONFIG_KEYS:
            value = config.get(key)
            if value is None:
                msg = _("Missing required configuration key: %(key)s" % {"key":key})
                _LOG.error(msg)
                return False, msg
            if key == 'http':
                config_http = config.get('http')
                if config_http is not None and not isinstance(config_http, bool):
                    msg = _("http should be a boolean; got %s instead" % config_http)
                    _LOG.error(msg)
                    return False, msg
            if key == 'https':
                config_https = config.get('https')
                if config_https is not None and not isinstance(config_https, bool):
                    msg = _("https should be a boolean; got %s instead" % config_https)
                    _LOG.error(msg)
                    return False, msg
        for key in config.keys():
            if key not in REQUIRED_CONFIG_KEYS and key not in OPTIONAL_CONFIG_KEYS:
                msg = _("Configuration key '%(key)s' is not supported" % {"key":key})
                _LOG.error(msg)
                return False, msg
            if key == 'skip':
                metadata_types = config.get('skip')
                if metadata_types is not None and not isinstance(metadata_types, list):
                    msg = _("skip should be a dictionary; got %s instead" % metadata_types)
                    _LOG.error(msg)
                    return False, msg
            if key == 'https_ca':
                https_ca = config.get('https_ca').encode('utf-8')
                if https_ca is not None and not util.validate_cert(https_ca):
                    msg = _("https_ca is not a valid certificate")
                    _LOG.error(msg)
                    return False, msg
            if key == 'iso_prefix':
                iso_prefix = config.get('iso_prefix')
                if iso_prefix is not None and (not isinstance(iso_prefix, str) or not iso_util.is_valid_prefix(iso_prefix)):
                    msg = _("iso_prefix is not a valid string; valid supported characters include %s" % iso_util.ISO_NAME_REGEX.pattern)
                    _LOG.error(msg)
                    return False, msg
        publish_dir = config.get("https_publish_dir")
        if publish_dir:
            if not os.path.exists(publish_dir) or not os.path.isdir(publish_dir):
                msg = _("Value for 'https_publish_dir' is not an existing directory: %(publish_dir)s" % {"publish_dir":publish_dir})
                return False, msg
            if not os.access(publish_dir, os.R_OK) or not os.access(publish_dir, os.W_OK):
                msg = _("Unable to read & write to specified 'https_publish_dir': %(publish_dir)s" % {"publish_dir":publish_dir})
                return False, msg
        publish_dir = config.get("http_publish_dir")
        if publish_dir:
            if not os.path.exists(publish_dir) or not os.path.isdir(publish_dir):
                msg = _("Value for 'http_publish_dir' is not an existing directory: %(publish_dir)s" % {"publish_dir":publish_dir})
                return False, msg
            if not os.access(publish_dir, os.R_OK) or not os.access(publish_dir, os.W_OK):
                msg = _("Unable to read & write to specified 'http_publish_dir': %(publish_dir)s" % {"publish_dir":publish_dir})
                return False, msg
        return True, None

    def set_progress(self, type_id, status, progress_callback=None):
        if progress_callback:
            progress_callback(type_id, status)


    def cancel_publish_group(self, call_request, call_report):
        """
        see parent class for the doc string
        """
        self.canceled = True

    def init_group_progress(self):
        """
        Initialize the group progress status
        """
        self.group_progress_status = {"isos":               {"state": "NOT_STARTED"},
                                     "publish_http":       {"state": "NOT_STARTED"},
                                     "publish_https":      {"state": "NOT_STARTED"},
                                     "repositories":       {},}

    def publish_group(self, repo_group, publish_conduit, config):
        """
        see parent class for doc string
        """
        self.group_working_dir = group_working_dir = repo_group.working_dir
        skip_types = config.get("skip") or []
        self.init_group_progress()
        self.group_progress_status["group-id"] = repo_group.id

        # progress callback for group status
        def group_progress_callback(type_id, status):
            self.group_progress_status[type_id] = status
            publish_conduit.set_progress(self.group_progress_status)

        # loop through each repo in the group and perform exports
        for repoid in repo_group.repo_ids:
            _LOG.info("Exporting repo %s " % repoid)
            summary = {}
            details = {}
            progress_status = {
                                    "rpms":               {"state": "NOT_STARTED"},
                                    "errata":             {"state": "NOT_STARTED"},
                                    "distribution":       {"state": "NOT_STARTED"},
                                    "packagegroups":      {"state": "NOT_STARTED"},}
            def progress_callback(type_id, status):
                progress_status[type_id] = status
                publish_conduit.set_progress(progress_status)
            repo_working_dir = "%s/%s" % (group_working_dir, repoid)
            repo_exporter = RepoExporter(repo_working_dir, skip=skip_types)
            # check if any datefilter is set on the distributor
            date_filter = repo_exporter.create_date_range_filter(config)
            _LOG.debug("repo working dir %s" % repo_working_dir)
            groups_xml_path = None
            updateinfo_xml_path = None
            if date_filter:
                # If a date range is specified, we only export the errata within that range
                # and associated rpm units. This might change once we have dates associated
                # to other units.
                criteria = UnitAssociationCriteria(type_ids=[TYPE_ID_ERRATA], unit_filters=date_filter)
                errata_units = publish_conduit.get_units(repoid, criteria=criteria)
                # we only include binary and source; drpms are not associated to errata
                criteria = UnitAssociationCriteria(type_ids=[TYPE_ID_RPM, TYPE_ID_SRPM])
                rpm_units = publish_conduit.get_units(repoid, criteria=criteria)
                rpm_units = repo_exporter.get_errata_rpms(errata_units, rpm_units)
                rpm_status, rpm_errors = repo_exporter.export_rpms(rpm_units, progress_callback=progress_callback)
                if self.canceled:
                    return publish_conduit.build_failure_report(summary, details)
                # export errata and generate updateinfo xml
                updateinfo_xml_path = updateinfo.updateinfo(errata_units, repo_working_dir)
                progress_status["errata"]["num_success"] = len(errata_units)
                progress_status["errata"]["state"] = "FINISHED"
                summary["num_package_units_attempted"] = len(rpm_units)
                summary["num_package_units_exported"] = len(rpm_units) - len(rpm_errors)
                summary["num_package_units_errors"] = len(rpm_errors)
                summary["num_errata_units_exported"] = len(errata_units)
                details["errors"] = rpm_errors
            else:

                # export rpm units(this includes binary, source and delta)
                criteria = UnitAssociationCriteria(type_ids=[TYPE_ID_RPM, TYPE_ID_SRPM, TYPE_ID_DRPM])
                rpm_units = publish_conduit.get_units(repoid, criteria)
                rpm_status, rpm_errors = repo_exporter.export_rpms(rpm_units, progress_callback=progress_callback)
                summary["num_package_units_attempted"] = len(rpm_units)
                summary["num_package_units_exported"] = len(rpm_units) - len(rpm_errors)
                summary["num_package_units_errors"] = len(rpm_errors)

                # export package groups information and generate comps.xml
                groups_xml_path = None
                if "packagegroup" not in skip_types:
                    progress_status["packagegroups"]["state"] = "STARTED"
                    criteria = UnitAssociationCriteria(type_ids=[TYPE_ID_PKG_GROUP, TYPE_ID_PKG_CATEGORY])
                    existing_units = publish_conduit.get_units(repoid, criteria)
                    existing_groups = filter(lambda u : u.type_id in [TYPE_ID_PKG_GROUP], existing_units)
                    existing_cats = filter(lambda u : u.type_id in [TYPE_ID_PKG_CATEGORY], existing_units)
                    groups_xml_path = comps_util.write_comps_xml(repo_working_dir, existing_groups, existing_cats)
                    summary["num_package_groups_exported"] = len(existing_groups)
                    summary["num_package_categories_exported"] = len(existing_cats)
                    progress_status["packagegroups"]["state"] = "FINISHED"
                else:
                    progress_status["packagegroups"]["state"] = "SKIPPED"
                    _LOG.info("packagegroup unit type in skip list [%s]; skipping export" % skip_types)

                if self.canceled:
                    return publish_conduit.build_failure_report(summary, details)

                # export errata units and associated rpms
                progress_status["errata"]["state"] = "STARTED"
                criteria = UnitAssociationCriteria(type_ids=[TYPE_ID_ERRATA])
                errata_units = publish_conduit.get_units(repoid, criteria=criteria)
                progress_status["errata"]["state"] = "IN_PROGRESS"
                updateinfo_xml_path = updateinfo.updateinfo(errata_units, repo_working_dir)
                progress_status["errata"]["num_success"] = len(errata_units)
                progress_status["errata"]["state"] = "FINISHED"
                summary["num_errata_units_exported"] = len(errata_units)

                # export distributions
                criteria = UnitAssociationCriteria(type_ids=[TYPE_ID_DISTRO])
                distro_units = publish_conduit.get_units(repoid, criteria)
                distro_status, distro_errors = repo_exporter.export_distributions(distro_units, progress_callback=progress_callback)
                summary["num_distribution_units_attempted"] = len(distro_units)
                summary["num_distribution_units_exported"] = len(distro_units) - len(distro_errors)
                summary["num_distribution_units_errors"] = len(distro_errors)

                self.group_progress_status["repositories"][repoid] = progress_status
                self.set_progress("repositories", self.group_progress_status["repositories"], group_progress_callback)

                details["errors"] = rpm_errors + distro_errors
                self.group_summary[repoid] = summary
                self.group_details[repoid] = details

            # generate metadata for the exported repo
            repo_scratchpad = publish_conduit.get_repo_scratchpad(repoid)
            metadata_status, metadata_errors = metadata.generate_yum_metadata(
                repo_working_dir, rpm_units, config, progress_callback, is_cancelled=self.canceled,
                group_xml_path=groups_xml_path, updateinfo_xml_path=updateinfo_xml_path, repo_scratchpad=repo_scratchpad)
            details["errors"] += metadata_errors
        # generate and publish isos
        self._publish_isos(repo_group, config, progress_callback=group_progress_callback)
        _LOG.info("Publish complete:  summary = <%s>, details = <%s>" % (self.group_summary, self.group_details))

        # remove exported content from working dirctory
        iso_util.cleanup_working_dir(self.group_working_dir)

        # check for any errors
        if not len([self.group_details[repoid]["errors"] for repoid in self.group_details.keys()]):
            return publish_conduit.build_failure_report(self.group_summary, self.group_details)

        return publish_conduit.build_success_report(self.group_summary, self.group_details)

    def _publish_isos(self, repo_group, config, progress_callback=None):
        """
        Generate the iso images on the exported directory of repos and publish
        them to the publish directory. Supports http/https publish. This does not
        support repo_auth.
        @param repo_group: metadata describing the repository group to which the
                     configuration applies
        @type  repo_group: pulp.plugins.model.RepositoryGroup

        @param config: plugin configuration instance; the proposed repo
                       configuration is found within
        @type  config: pulp.plugins.config.PluginCallConfiguration

        @param progress_callback: callback to report progress info to publish_conduit
        @type  progress_callback: function
        """
        # build iso and publish via HTTPS
        https_publish_dir = iso_util.get_https_publish_iso_dir(config)
        https_repo_publish_dir = os.path.join(https_publish_dir, repo_group.id).rstrip('/')
        prefix = config.get('iso_prefix') or repo_group.id
        if config.get("https"):
            # Publish for HTTPS
            self.set_progress("publish_https", {"state" : "IN_PROGRESS"}, progress_callback)
            try:
                _LOG.info("HTTPS Publishing repo <%s> to <%s>" % (repo_group.id, https_repo_publish_dir))
                # generate iso images and write them to the publish directory
                isogen = GenerateIsos(self.group_working_dir, https_repo_publish_dir, prefix=prefix, progress=self.init_progress(), is_cancelled=self.canceled)
                isogen.run(progress_callback=progress_callback)
                self.group_summary["https_publish_dir"] = https_repo_publish_dir
                self.set_progress("publish_https", {"state" : "FINISHED"}, progress_callback)
            except Exception,e:
                _LOG.debug(" publish operaation failed due to exception: %s" % e)
                self.set_progress("publish_https", {"state" : "FAILED"}, progress_callback)
        else:
            self.set_progress("publish_https", {"state" : "SKIPPED"}, progress_callback)
            if os.path.lexists(https_repo_publish_dir):
                _LOG.debug("Removing link for %s since https is not set" % https_repo_publish_dir)
                shutil.rmtree(https_repo_publish_dir)

        # build iso and publish via HTTP
        http_publish_dir = iso_util.get_http_publish_iso_dir(config)
        http_repo_publish_dir = os.path.join(http_publish_dir, repo_group.id).rstrip('/')
        if config.get("http"):
            # Publish for HTTP
            self.set_progress("publish_http", {"state" : "IN_PROGRESS"}, progress_callback)
            try:
                _LOG.info("HTTP Publishing repo <%s> to <%s>" % (repo_group.id, http_repo_publish_dir))
                # generate iso images and write them to the publish directory
                isogen = GenerateIsos(self.group_working_dir, http_repo_publish_dir, prefix=prefix, progress=self.init_progress(), is_cancelled=self.canceled)
                isogen.run(progress_callback=progress_callback)
                self.group_summary["http_publish_dir"] = http_repo_publish_dir
                self.set_progress("publish_http", {"state" : "FINISHED"}, progress_callback)
            except Exception,e:
                _LOG.debug(" publish operaation failed due to exception: %s" % e)
                self.set_progress("publish_http", {"state" : "FAILED"}, progress_callback)
        else:
            self.set_progress("publish_http", {"state" : "SKIPPED"}, progress_callback)
            if os.path.lexists(http_repo_publish_dir):
                _LOG.debug("Removing link for %s since http is not set" % http_repo_publish_dir)
                shutil.rmtree(http_repo_publish_dir)
