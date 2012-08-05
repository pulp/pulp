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
import shutil
import time
import traceback
from pulp_rpm.yum_plugin import util, updateinfo, metadata
from pulp.plugins.distributor import Distributor
from iso_distributor.generate_iso import GenerateIsos
from pulp.server.db.model.criteria import UnitAssociationCriteria

from pulp_rpm.common.ids import TYPE_ID_DISTRIBUTOR_ISO, TYPE_ID_DISTRO, TYPE_ID_DRPM, TYPE_ID_ERRATA, TYPE_ID_PKG_GROUP,\
        TYPE_ID_PKG_CATEGORY, TYPE_ID_RPM, TYPE_ID_SRPM
from pulp_rpm.yum_plugin import comps_util
_LOG = util.getLogger(__name__)
_ = gettext.gettext

REQUIRED_CONFIG_KEYS = ["http", "https"]
OPTIONAL_CONFIG_KEYS = ["generate_metadata", "https_publish_dir","http_publish_dir", "start_date", "end_date"]

HTTP_PUBLISH_DIR="/var/lib/pulp/published/http/isos"
HTTPS_PUBLISH_DIR="/var/lib/pulp/published/https/isos"

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
#                         ["rpm", "drpm", "errata", "distribution", "packagegroup"]
# -- plugins ------------------------------------------------------------------

# TODO:
# - export metadata from db (blocked on metadata snippet approach); includes prestodelta, custom metadata
# - implement ability to skip content types from exports
# - ability to cancel exports
# - iso naming is standardized; provide optional override

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

        date_filter = self.create_date_range_filter(config)
        if date_filter:
            # export errata by date and associated rpm units
            progress_status["errata"]["state"] = "STARTED"
            criteria = UnitAssociationCriteria(type_ids=[TYPE_ID_ERRATA], unit_filters=date_filter)
            errata_units = publish_conduit.get_units(criteria)
            criteria = UnitAssociationCriteria(type_ids=[TYPE_ID_RPM, TYPE_ID_SRPM, TYPE_ID_DRPM])
            rpm_units = publish_conduit.get_units(criteria)
            rpm_units = self._get_errata_rpms(errata_units, rpm_units)
            rpm_status, rpm_errors = self._export_rpms(rpm_units, repo_working_dir, progress_callback=progress_callback)
            progress_status["rpms"]["state"] = "FINISHED"
            if self.canceled:
                return publish_conduit.build_failure_report(summary, details)
            # generate metadata
            metadata_status, metadata_errors = metadata.generate_metadata(
                    repo, publish_conduit, config, progress_callback)
            _LOG.info("metadata generation complete at target location %s" % repo_working_dir)
            errata_status, errata_errors = self._export_errata(errata_units, repo_working_dir, progress_callback=progress_callback)
            progress_status["errata"]["state"] = "FINISHED"

            summary["num_package_units_attempted"] = len(rpm_units)
            summary["num_package_units_exported"] = len(rpm_units) - len(rpm_errors)
            summary["num_package_units_errors"] = len(rpm_errors)
            details["errors"] = rpm_errors +  errata_errors
        else:
            # export everything
            progress_status["rpms"]["state"] = "STARTED"
            criteria = UnitAssociationCriteria(type_ids=[TYPE_ID_RPM, TYPE_ID_SRPM, TYPE_ID_DRPM])
            rpm_units = publish_conduit.get_units(criteria)
            rpm_status, rpm_errors = self._export_rpms(rpm_units, repo_working_dir, progress_callback=progress_callback)
            progress_status["rpms"]["state"] = "FINISHED"

            # package groups
            progress_status["packagegroups"]["state"] = "STARTED"
            criteria = UnitAssociationCriteria(type_ids=[TYPE_ID_PKG_GROUP, TYPE_ID_PKG_CATEGORY])
            existing_units = publish_conduit.get_units(criteria)
            existing_groups = filter(lambda u : u.type_id in [TYPE_ID_PKG_GROUP], existing_units)
            existing_cats = filter(lambda u : u.type_id in [TYPE_ID_PKG_CATEGORY], existing_units)
            groups_xml_path = comps_util.write_comps_xml(repo, existing_groups, existing_cats)
            if self.canceled:
                return publish_conduit.build_failure_report(summary, details)
            # generate metadata
            metadata_status, metadata_errors = metadata.generate_metadata(
                    repo, publish_conduit, config, progress_callback, groups_xml_path)
            _LOG.info("metadata generation complete at target location %s" % repo_working_dir)
            progress_status["packagegroups"]["state"] = "FINISHED"

            progress_status["errata"]["state"] = "STARTED"
            criteria = UnitAssociationCriteria(type_ids=[TYPE_ID_ERRATA])
            errata_units = publish_conduit.get_units(criteria)
            rpm_units = self._get_errata_rpms(errata_units, rpm_units)
            self._export_rpms(rpm_units, repo_working_dir, progress_callback=progress_callback)
            errata_status, errata_errors = self._export_errata(errata_units, repo_working_dir, progress_callback=progress_callback)
            progress_status["errata"]["state"] = "FINISHED"

            # distro units
            progress_status["distribution"]["state"] = "STARTED"
            criteria = UnitAssociationCriteria(type_ids=[TYPE_ID_DISTRO])
            distro_units = publish_conduit.get_units(criteria)
            distro_status, distro_errors = self._export_distributions(distro_units, repo_working_dir, progress_callback=progress_callback)
            progress_status["distribution"]["state"] = "FINISHED"

            summary["num_distribution_units_attempted"] = len(distro_units)
            summary["num_distribution_units_exported"] = len(distro_units) - len(distro_errors)
            summary["num_distribution_units_errors"] = len(distro_errors)
            summary["num_package_groups_exported"] = len(existing_groups)
            summary["num_package_categories_exported"] = len(existing_cats)

            summary["num_package_units_attempted"] = len(rpm_units)
            summary["num_package_units_exported"] = len(rpm_units) - len(rpm_errors)
            summary["num_package_units_errors"] = len(rpm_errors)
            details["errors"] = rpm_errors + distro_errors + errata_errors
        # build iso and publish via HTTPS
        https_publish_dir = self.get_https_publish_iso_dir(config)
        https_repo_publish_dir = os.path.join(https_publish_dir, repo.id).rstrip('/')
        if config.get("https"):
            # Publish for HTTPS
            self.set_progress("publish_https", {"state" : "IN_PROGRESS"}, progress_callback)
            try:
                _LOG.info("HTTPS Publishing repo <%s> to <%s>" % (repo.id, https_repo_publish_dir))
                isogen = GenerateIsos(repo_working_dir, https_repo_publish_dir, prefix=repo.id, progress=progress_status)
                progress_status = isogen.run()
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
                isogen = GenerateIsos(repo_working_dir, http_repo_publish_dir, prefix=repo.id, progress=progress_status)
                progress_status = isogen.run()
                summary["http_publish_dir"] = http_repo_publish_dir
                self.set_progress("publish_http", {"state" : "FINISHED"}, progress_callback)
            except:
                self.set_progress("publish_http", {"state" : "FAILED"}, progress_callback)
        else:
            self.set_progress("publish_http", {"state" : "SKIPPED"}, progress_callback)
            if os.path.lexists(http_repo_publish_dir):
                _LOG.debug("Removing link for %s since http is not set" % http_repo_publish_dir)
                shutil.rmtree(http_repo_publish_dir)
        details["errors"] += metadata_errors
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

    def _export_rpms(self, rpm_units, symlink_dir, progress_callback=None):
        """
         This call looksup each rpm units and exports to the working directory.

        @param rpm_units
        @type errata_units list of AssociatedUnit to be exported

        @param symlink_dir: path of where we want the symlink and repodata to reside
        @type symlink_dir str

        @param progress_callback: callback to report progress info to publish_conduit
        @type  progress_callback: function

        @return tuple of status and list of error messages if any occurred
        @rtype (bool, [str])
        """
        # get rpm units
        packages_progress_status = self.init_progress()
        packages_progress_status["num_success"] = 0
        packages_progress_status["items_left"] = len(rpm_units)
        packages_progress_status["items_total"] = len(rpm_units)
        errors = []
        for u in rpm_units:
            self.set_progress("packages", packages_progress_status, progress_callback)
            relpath = util.get_relpath_from_unit(u)
            source_path = u.storage_path
            symlink_path = os.path.join(symlink_dir, relpath)
            if not os.path.exists(source_path):
                msg = "Source path: %s is missing" % (source_path)
                errors.append((source_path, symlink_path, msg))
                packages_progress_status["num_error"] += 1
                packages_progress_status["items_left"] -= 1
                continue
            _LOG.info("Unit exists at: %s we need to copy to: %s" % (source_path, symlink_path))
            try:
                if not util.create_copy(source_path, symlink_path):
                    msg = "Unable to create copy for: %s pointing to %s" % (symlink_path, source_path)
                    _LOG.error(msg)
                    errors.append((source_path, symlink_path, msg))
                    packages_progress_status["num_error"] += 1
                    packages_progress_status["items_left"] -= 1
                    continue
                packages_progress_status["num_success"] += 1
            except Exception, e:
                tb_info = traceback.format_exc()
                _LOG.error("%s" % (tb_info))
                _LOG.critical(e)
                errors.append((source_path, symlink_path, str(e)))
                packages_progress_status["num_error"] += 1
                packages_progress_status["items_left"] -= 1
                continue
            packages_progress_status["items_left"] -= 1
        if errors:
            packages_progress_status["error_details"] = errors
            return False, errors
        packages_progress_status["state"] = "FINISHED"
        self.set_progress("packages", packages_progress_status, progress_callback)
        return True, []

    def _export_errata(self, errata_units, repo_working_dir, progress_callback=None):
        """
         This call looksup each errata unit and its associated rpms and exports
         the rpms units to the working directory and generates updateinfo xml for
         exported errata metadata.

        @param errata_units
        @type errata_units list of AssociatedUnit

        @param repo_working_dir: path of where we want the symlink and repodata to reside
        @type repo_working_dir str

        @param progress_callback: callback to report progress info to publish_conduit
        @type  progress_callback: function

        @return tuple of status and list of error messages if any occurred
        @rtype (bool, [str])
        """
        errors = []
        errata_progress_status = self.init_progress()
        if not errata_units:
            return True, []
        errata_progress_status["num_success"] = 0
        errata_progress_status["items_left"] = len(errata_units)
        errata_progress_status["items_total"] = len(errata_units)
        try:
            errata_progress_status['state'] = "IN_PROGRESS"
            self.set_progress("errata", errata_progress_status, progress_callback)

            updateinfo_path = updateinfo.updateinfo(errata_units, repo_working_dir)
            if updateinfo_path:
                repodata_dir = os.path.join(repo_working_dir, "repodata")
                if not os.path.exists(repodata_dir):
                    _LOG.error("Missing repodata; cannot run modifyrepo")
                    return False, []
                _LOG.debug("Modifying repo for updateinfo")
                metadata.modify_repo(repodata_dir,  updateinfo_path)
            errata_progress_status["num_success"] = len(errata_units)
            errata_progress_status["items_left"] = 0
        except metadata.ModifyRepoError, mre:
            msg = "Unable to run modifyrepo to include updateinfo at target location %s; Error: %s" % (repo_working_dir, str(mre))
            errors.append(msg)
            _LOG.error(msg)
            errata_progress_status['state'] = "FAILED"
            errata_progress_status["num_success"] = 0
            errata_progress_status["items_left"] = len(errata_units)
            return False, errors
        except Exception, e:
            errors.append(str(e))
            errata_progress_status['state'] = "FAILED"
            errata_progress_status["num_success"] = 0
            errata_progress_status["items_left"] = len(errata_units)
            return False, errors
        errata_progress_status['state'] = "FINISHED"
        return True, []

    def _get_errata_rpms(self, errata_units, rpm_units):
        existing_rpm_units = form_unit_key_map(rpm_units)
        print "existing",existing_rpm_units
        # get pkglist associaed to the errata
        rpm_units = []
        for u in errata_units:
            pkglist = u.metadata['pkglist']
            for pkg in pkglist:
                for pinfo in pkg['packages']:
                    if not pinfo.has_key('sum'):
                        _LOG.debug("Missing checksum info on package <%s> for linking a rpm to an erratum." % (pinfo))
                        continue
                    pinfo['checksumtype'], pinfo['checksum'] = pinfo['sum']
                    rpm_key = form_lookup_key(pinfo)
                    if rpm_key in existing_rpm_units.keys():
                        rpm_unit = existing_rpm_units[rpm_key]
                        _LOG.info("Found matching rpm unit %s" % rpm_unit)
                        rpm_units.append(rpm_unit)
        return rpm_units

    def _export_distributions(self, units, symlink_dir, progress_callback=None):
        """
        Export distriubution unit involves including files within the unit.
        Distribution is an aggregate unit with distribution files. This call
        looksup each distribution unit and symlinks the files from the storage location
        to working directory.

        @param units
        @type AssociatedUnit

        @param symlink_dir: path of where we want the symlink to reside
        @type symlink_dir str

        @param progress_callback: callback to report progress info to publish_conduit
        @type  progress_callback: function

        @return tuple of status and list of error messages if any occurred
        @rtype (bool, [str])
        """
        distro_progress_status = self.init_progress()
        self.set_progress("distribution", distro_progress_status, progress_callback)
        _LOG.info("Process symlinking distribution files with %s units to %s dir" % (len(units), symlink_dir))
        errors = []
        for u in units:
            source_path_dir  = u.storage_path
            if not u.metadata.has_key('files'):
                msg = "No distribution files found for unit %s" % u
                _LOG.error(msg)
            distro_files =  u.metadata['files']
            _LOG.info("Found %s distribution files to symlink" % len(distro_files))
            distro_progress_status['items_total'] = len(distro_files)
            distro_progress_status['items_left'] = len(distro_files)
            for dfile in distro_files:
                self.set_progress("distribution", distro_progress_status, progress_callback)
                source_path = os.path.join(source_path_dir, dfile['relativepath'])
                symlink_path = os.path.join(symlink_dir, dfile['relativepath'])
                if not os.path.exists(source_path):
                    msg = "Source path: %s is missing" % source_path
                    errors.append((source_path, symlink_path, msg))
                    distro_progress_status['num_error'] += 1
                    distro_progress_status["items_left"] -= 1
                    continue
                try:
                    if not util.create_copy(source_path, symlink_path): #util.create_symlink(source_path, symlink_path):
                        msg = "Unable to create copy for: %s pointing to %s" % (symlink_path, source_path)
                        _LOG.error(msg)
                        errors.append((source_path, symlink_path, msg))
                        distro_progress_status['num_error'] += 1
                        distro_progress_status["items_left"] -= 1
                        continue
                    distro_progress_status['num_success'] += 1
                except Exception, e:
                    tb_info = traceback.format_exc()
                    _LOG.error("%s" % tb_info)
                    _LOG.critical(e)
                    errors.append((source_path, symlink_path, str(e)))
                    distro_progress_status['num_error'] += 1
                    distro_progress_status["items_left"] -= 1
                    continue
                distro_progress_status["items_left"] -= 1
        if errors:
            distro_progress_status["error_details"] = errors
            distro_progress_status["state"] = "FAILED"
            self.set_progress("distribution", distro_progress_status, progress_callback)
            return False, errors
        distro_progress_status["state"] = "FINISHED"
        self.set_progress("distribution", distro_progress_status, progress_callback)
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

