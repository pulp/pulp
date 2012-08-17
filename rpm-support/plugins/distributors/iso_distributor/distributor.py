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
import logging
import re
import shutil
import string
import time
import traceback
import math
from pulp_rpm.yum_plugin import util, updateinfo, metadata
from pulp.plugins.distributor import Distributor
from iso_distributor.generate_iso import GenerateIsos
from iso_distributor.exporter import RepoExporter
from pulp.server.db.model.criteria import UnitAssociationCriteria

from pulp_rpm.common.ids import TYPE_ID_DISTRIBUTOR_ISO, TYPE_ID_DISTRO, TYPE_ID_DRPM, TYPE_ID_ERRATA, TYPE_ID_PKG_GROUP,\
        TYPE_ID_PKG_CATEGORY, TYPE_ID_RPM, TYPE_ID_SRPM
from pulp_rpm.yum_plugin import comps_util
_LOG = util.getLogger(__name__)
_ = gettext.gettext

REQUIRED_CONFIG_KEYS = ["http", "https"]
OPTIONAL_CONFIG_KEYS = ["generate_metadata", "https_publish_dir","http_publish_dir", "start_date", "end_date", "iso_prefix", "skip"]

HTTP_PUBLISH_DIR="/var/lib/pulp/published/http/isos"
HTTPS_PUBLISH_DIR="/var/lib/pulp/published/https/isos"
ISO_NAME_REGEX = re.compile(r'^[_A-Za-z0-9-]+$')

###
# Config Options Explained
###
# http                  - True/False:  Publish through http
# https                 - True/False:  Publish through https
# https_ca              - CA to verify https communication
# generate_metadata     - True will run createrepo
# start_date            - errata start date format eg: "2009-03-30 00:00:00"
# end_date              - errata end date format eg: "2009-03-30 00:00:00"
# http_publish_dir      - Optional parameter to override the HTTP_PUBLISH_DIR, mainly used for unit tests
# skip                  - List of what content types to skip during export, options:
#                         ["rpm", "errata", "distribution", "packagegroup"]
# iso_prefix            - prefix to use in the generated iso naming, default: <repoid>-<current_date>.iso
# -- plugins ------------------------------------------------------------------

# TODO:
# - export metadata from db (blocked on metadata snippet approach); includes prestodelta, custom metadata

class ISODistributor(Distributor):

    def __init__(self):
        super(ISODistributor, self).__init__()
        self.canceled = False

    @classmethod
    def metadata(cls):
        return {
            'id'           : TYPE_ID_DISTRIBUTOR_ISO,
            'display_name' : 'Iso Distributor',
            'types'        : [TYPE_ID_RPM, TYPE_ID_SRPM, TYPE_ID_DRPM, TYPE_ID_ERRATA, TYPE_ID_DISTRO, TYPE_ID_PKG_CATEGORY, TYPE_ID_PKG_GROUP]
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
            if key == 'generate_metadata':
                generate_metadata = config.get('generate_metadata')
                if generate_metadata is not None and not isinstance(generate_metadata, bool):
                    msg = _("generate_metadata should be a boolean; got %s instead" % generate_metadata)
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
                if iso_prefix is not None and (not isinstance(iso_prefix, str) or not self._is_valid_prefix(iso_prefix)):
                    msg = _("iso_prefix is not a valid string; valid supported characters include %s" % ISO_NAME_REGEX.pattern)
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

    def cancel_publish_repo(self, call_request, call_report):
        self.canceled = True
        repo_working_dir = getattr(self, 'repo_working_dir')
        return metadata.cancel_createrepo(repo_working_dir)

    def set_progress(self, type_id, status, progress_callback=None):
        if progress_callback:
            progress_callback(type_id, status)

    def _is_valid_prefix(self, iso_prefix):
        """
        @return: True if the given iso_prefix is a valid match; False otherwise
        """
        return ISO_NAME_REGEX.match(iso_prefix) is not None

    def create_date_range_filter(self, config):
        start_date = None
        if config.get("start_date"):
            start_date = config.get("start_date") or None
        end_date = None
        if config.get("end_date"):
            end_date = config.get("end_date") or None
        date_filter = None
        if start_date and end_date:
            date_filter = {"issued" : {"$gte": start_date, "$lte": end_date}}
        elif start_date:
            date_filter = {"issued" : {"$gte": start_date}}
        elif end_date:
            date_filter = {"issued" : {"$lte": end_date}}
        return date_filter

    def publish_repo(self, repo, publish_conduit, config):
        publish_start_time = time.time()
        _LOG.info("Start publish time %s" % publish_start_time)
        summary = {}
        details = {}
        progress_status = {
            "rpms":               {"state": "NOT_STARTED"},
            "errata":             {"state": "NOT_STARTED"},
            "distribution":       {"state": "NOT_STARTED"},
            "packagegroups":      {"state": "NOT_STARTED"},
            "isos":               {"state": "NOT_STARTED"},
            "publish_http":       {"state": "NOT_STARTED"},
            }

        def progress_callback(type_id, status):
            progress_status[type_id] = status
            publish_conduit.set_progress(progress_status)

        self.repo_working_dir = repo_working_dir = repo.working_dir

        if self.canceled:
            return publish_conduit.build_failure_report(summary, details)

        repo_exporter = RepoExporter()
        skip_types = config.get("skip") or []
        date_filter = self.create_date_range_filter(config)
        if date_filter:
            # export errata by date and associated rpm units
            if "errata" not in skip_types:
                progress_status["errata"]["state"] = "STARTED"
                criteria = UnitAssociationCriteria(type_ids=[TYPE_ID_ERRATA], unit_filters=date_filter)
                errata_units = publish_conduit.get_units(criteria)
                criteria = UnitAssociationCriteria(type_ids=[TYPE_ID_RPM, TYPE_ID_SRPM, TYPE_ID_DRPM])
                rpm_units = publish_conduit.get_units(criteria)
                rpm_units = repo_exporter.get_errata_rpms(errata_units, rpm_units)
                rpm_status, rpm_errors = repo_exporter.export_rpms(rpm_units, repo_working_dir, progress_callback=progress_callback)
                progress_status["rpms"]["state"] = "FINISHED"
                if self.canceled:
                    return publish_conduit.build_failure_report(summary, details)
                # generate metadata
                metadata_status, metadata_errors = metadata.generate_metadata(
                        repo, publish_conduit, config, progress_callback)
                _LOG.info("metadata generation complete at target location %s" % repo_working_dir)
                errata_status, errata_errors = repo_exporter.export_errata(errata_units, repo_working_dir, progress_callback=progress_callback)
                progress_status["errata"]["state"] = "FINISHED"

                summary["num_package_units_attempted"] = len(rpm_units)
                summary["num_package_units_exported"] = len(rpm_units) - len(rpm_errors)
                summary["num_package_units_errors"] = len(rpm_errors)
                details["errors"] = rpm_errors +  errata_errors + metadata_errors
            else:
                progress_status["errata"]["state"] = "SKIPPED"
                _LOG.info("erratum unit type in skip list [%s]; skipping export" % skip_types)
        else:
            # export everything
            rpm_units = []
            rpm_errors = []
            if "rpm" not in skip_types:
                progress_status["rpms"]["state"] = "STARTED"
                criteria = UnitAssociationCriteria(type_ids=[TYPE_ID_RPM, TYPE_ID_SRPM, TYPE_ID_DRPM])
                rpm_units = publish_conduit.get_units(criteria)
                rpm_status, rpm_errors = repo_exporter.export_rpms(rpm_units, repo_working_dir, progress_callback=progress_callback)
                progress_status["rpms"]["state"] = "FINISHED"
                summary["num_package_units_attempted"] = len(rpm_units)
                summary["num_package_units_exported"] = len(rpm_units) - len(rpm_errors)
                summary["num_package_units_errors"] = len(rpm_errors)
            else:
                progress_status["rpms"]["state"] = "SKIPPED"
                _LOG.info("rpm unit type in skip list [%s]; skipping export" % skip_types)
            # package groups
            groups_xml_path = None
            if "packagegroup" not in skip_types:
                progress_status["packagegroups"]["state"] = "STARTED"
                criteria = UnitAssociationCriteria(type_ids=[TYPE_ID_PKG_GROUP, TYPE_ID_PKG_CATEGORY])
                existing_units = publish_conduit.get_units(criteria)
                existing_groups = filter(lambda u : u.type_id in [TYPE_ID_PKG_GROUP], existing_units)
                existing_cats = filter(lambda u : u.type_id in [TYPE_ID_PKG_CATEGORY], existing_units)
                groups_xml_path = comps_util.write_comps_xml(repo, existing_groups, existing_cats)
                summary["num_package_groups_exported"] = len(existing_groups)
                summary["num_package_categories_exported"] = len(existing_cats)
                progress_status["packagegroups"]["state"] = "FINISHED"
            else:
                progress_status["packagegroups"]["state"] = "SKIPPED"
                _LOG.info("packagegroup unit type in skip list [%s]; skipping export" % skip_types)

            if self.canceled:
                return publish_conduit.build_failure_report(summary, details)
            # generate metadata
            metadata_status, metadata_errors = metadata.generate_metadata(
                    repo, publish_conduit, config, progress_callback, groups_xml_path)
            _LOG.info("metadata generation complete at target location %s" % repo_working_dir)
            errata_errors = []
            if "errata" not in skip_types:
                progress_status["errata"]["state"] = "STARTED"
                criteria = UnitAssociationCriteria(type_ids=[TYPE_ID_ERRATA])
                errata_units = publish_conduit.get_units(criteria)
                rpm_units = repo_exporter.get_errata_rpms(errata_units, rpm_units)
                repo_exporter.export_rpms(rpm_units, repo_working_dir, progress_callback=progress_callback)
                errata_status, errata_errors = repo_exporter.export_errata(errata_units, repo_working_dir, progress_callback=progress_callback)
                summary["num_errata_units_exported"] = len(errata_units)
                progress_status["errata"]["state"] = "FINISHED"
            else:
                progress_status["errata"]["state"] = "SKIPPED"
                _LOG.info("erratum unit type in skip list [%s]; skipping export" % skip_types)

            distro_errors = []
            if "distribution" not in skip_types:
                # distro units
                progress_status["distribution"]["state"] = "STARTED"
                criteria = UnitAssociationCriteria(type_ids=[TYPE_ID_DISTRO])
                distro_units = publish_conduit.get_units(criteria)
                distro_status, distro_errors = repo_exporter.export_distributions(distro_units, repo_working_dir, progress_callback=progress_callback)
                progress_status["distribution"]["state"] = "FINISHED"

                summary["num_distribution_units_attempted"] = len(distro_units)
                summary["num_distribution_units_exported"] = len(distro_units) - len(distro_errors)
                summary["num_distribution_units_errors"] = len(distro_errors)
            else:
                progress_status["distribution"]["state"] = "SKIPPED"
                _LOG.info("distribution unit type in skip list [%s]; skipping export" % skip_types)

            details["errors"] = rpm_errors + distro_errors + errata_errors + metadata_errors
        # build iso and publish via HTTPS
        https_publish_dir = self.get_https_publish_iso_dir(config)
        https_repo_publish_dir = os.path.join(https_publish_dir, repo.id).rstrip('/')
        prefix = config.get('iso_prefix') or repo.id
        if config.get("https"):
            # Publish for HTTPS
            self.set_progress("publish_https", {"state" : "IN_PROGRESS"}, progress_callback)
            try:
                _LOG.info("HTTPS Publishing repo <%s> to <%s>" % (repo.id, https_repo_publish_dir))
                iso_status, iso_errors = self.generate_isos(repo_working_dir, https_repo_publish_dir, prefix=prefix, progress_callback=progress_callback)
                summary["https_publish_dir"] = https_repo_publish_dir
                self.set_progress("publish_https", {"state" : "FINISHED"}, progress_callback)
                progress_status["isos"]["state"] = "FINISHED"
            except:
                self.set_progress("publish_https", {"state" : "FAILED"}, progress_callback)
        else:
            self.set_progress("publish_https", {"state" : "SKIPPED"}, progress_callback)
            if os.path.lexists(https_repo_publish_dir):
                _LOG.debug("Removing link for %s since https is not set" % https_repo_publish_dir)
                shutil.rmtree(https_repo_publish_dir)

        # Handle publish link for HTTP
        # build iso and publish via HTTP
        http_publish_dir = self.get_http_publish_iso_dir(config)
        http_repo_publish_dir = os.path.join(http_publish_dir, repo.id).rstrip('/')
        if config.get("http"):
            # Publish for HTTP
            self.set_progress("publish_http", {"state" : "IN_PROGRESS"}, progress_callback)
            try:
                _LOG.info("HTTP Publishing repo <%s> to <%s>" % (repo.id, http_repo_publish_dir))
                iso_status, iso_errors = self.generate_isos(repo_working_dir, http_repo_publish_dir, prefix=prefix, progress_callback=progress_callback)
                print iso_status, iso_errors
                summary["http_publish_dir"] = http_repo_publish_dir
                self.set_progress("publish_http", {"state" : "FINISHED"}, progress_callback)
                progress_status["isos"]["state"] = "FINISHED"
            except:
                self.set_progress("publish_http", {"state" : "FAILED"}, progress_callback)
        else:
            self.set_progress("publish_http", {"state" : "SKIPPED"}, progress_callback)
            if os.path.lexists(http_repo_publish_dir):
                _LOG.debug("Removing link for %s since http is not set" % http_repo_publish_dir)
                shutil.rmtree(http_repo_publish_dir)
        # metadata generate skipped vs run
        _LOG.info("Publish complete:  summary = <%s>, details = <%s>" % (summary, details))
        # remove exported content from working dirctory
        self.cleanup()
        if details["errors"]:
            return publish_conduit.build_failure_report(summary, details)
        return publish_conduit.build_success_report(summary, details)

    def cleanup(self):
        """
        remove exported content from working dirctory
        """
        try:
            shutil.rmtree(self.repo_working_dir)
            _LOG.debug("Cleaned up repo working directory %s" % self.repo_working_dir)
        except (IOError, OSError), e:
            _LOG.error("unable to clean up working directory; Error: %s" % e)

    def get_http_publish_iso_dir(self, config=None):
        """
        @param config
        @type pulp.server.content.plugins.config.PluginCallConfiguration
        """
        if config:
            publish_dir = config.get("http_publish_dir")
            if publish_dir:
                _LOG.info("Override HTTP publish directory from passed in config value to: %s" % (publish_dir))
                return publish_dir
        return HTTP_PUBLISH_DIR

    def get_https_publish_iso_dir(self, config=None):
        """
        @param config
        @type pulp.server.content.plugins.config.PluginCallConfiguration
        """
        if config:
            publish_dir = config.get("https_publish_dir")
            if publish_dir:
                _LOG.info("Override HTTPS publish directory from passed in config value to: %s" % (publish_dir))
                return publish_dir
        return HTTPS_PUBLISH_DIR

    def generate_isos(self, repo_working_dir, publish_dir, prefix, progress_callback=None):
        """
         generate iso images for the exported directory
        """
        iso_progress_status = self.init_progress()
        iso_progress_status['state'] = "IN_PROGRESS"
        self.set_progress("isos", iso_progress_status, progress_callback)
        isogen = GenerateIsos(repo_working_dir, publish_dir, prefix=prefix, progress=progress_callback)
        # get size and filelists of the target directory
        filelist, total_dir_size = isogen.list_dir_with_size(repo_working_dir)
        _LOG.debug("Total target directory size to create isos %s" % total_dir_size)
        # media size
        img_size = isogen.get_image_type_size(total_dir_size)
        # compute no.of images it takes per media image size
        imgcount = int(math.ceil(total_dir_size/float(img_size)))
        # get the filelists per image by size
        imgs = isogen.compute_image_files(filelist, imgcount, img_size)
        iso_progress_status['items_total'] = imgcount
        iso_progress_status['items_left'] = imgcount
        iso_progress_status["size_total"] = total_dir_size
        iso_progress_status["size_left"] = total_dir_size
        for i in range(imgcount):
            self.set_progress("isos", iso_progress_status, progress_callback)
            msg = "Generating iso images for exported content (%s/%s)" % (i+1, imgcount)
            _LOG.info(msg)
            grafts = isogen.get_grafts(imgs[i])
            pathfiles_fd, pathfiles = isogen.get_pathspecs(grafts)
            filename = isogen.get_iso_filename(publish_dir, prefix, i+1)
            cmd = isogen.get_mkisofs_template() % (string.join([pathfiles]), filename)
            status, out = isogen.run_command(cmd)
            if status != 0:
                _LOG.error("Error creating iso %s" % filename)
            _LOG.info("successfully created iso %s" % filename)
            _LOG.debug("status code: %s; output: %s" % (status, out))
            os.unlink(pathfiles)
            iso_progress_status['items_left'] -= 1
            iso_progress_status['num_success'] += 1
            if iso_progress_status["size_left"] > img_size:
                iso_progress_status["size_left"] -= img_size
            else:
                iso_progress_status["size_left"] = 0
        iso_progress_status["state"] = "FINISHED"
        self.set_progress("isos", iso_progress_status, progress_callback)
        return True, []

def form_lookup_key(rpm):
    rpm_key = (rpm["name"], rpm["epoch"], rpm["version"], rpm['release'], rpm["arch"], rpm["checksumtype"], rpm["checksum"])
    return rpm_key

def form_unit_key_map(units):
   existing_units = {}
   for u in units:
       key = form_lookup_key(u.unit_key)
       existing_units[key] = u
   return existing_units

