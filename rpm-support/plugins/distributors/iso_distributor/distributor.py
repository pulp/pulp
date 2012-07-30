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
import time
import traceback
from pulp_rpm.yum_plugin import util, updateinfo, metadata
from pulp.plugins.distributor import Distributor
from iso_distributor.generate_iso import GenerateIsos
from pulp.server.db.model.criteria import UnitAssociationCriteria

from pulp_rpm.yum_plugin import comps_util
_LOG = util.getLogger(__name__)
_ = gettext.gettext

ISO_DISTRIBUTOR_TYPE_ID="iso_distributor"
DISTRO_TYPE_ID="distribution"
DRPM_TYPE_ID="drpm"
ERRATA_TYPE_ID="erratum"
PKG_GROUP_TYPE_ID="package_group"
PKG_CATEGORY_TYPE_ID="package_category"
RPM_TYPE_ID="rpm"
SRPM_TYPE_ID="srpm"

REQUIRED_CONFIG_KEYS = ["relative_url", "http", "https"]
OPTIONAL_CONFIG_KEYS = ["protected", "auth_cert", "auth_ca",
                        "https_ca", "https_publish_dir", "http_publish_dir"]

HTTP_PUBLISH_DIR="/var/lib/pulp/published/http/isos"
HTTPS_PUBLISH_DIR="/var/lib/pulp/published/https/isos"
CONFIG_REPO_AUTH="/etc/pulp/repo_auth.conf"

###
# Config Options Explained
###
# relative_url          - Relative URL to publish
#                         example: relative_url="rhel_6.2" may translate to publishing at
#                         http://localhost/pulp/repos/rhel_6.2
# start_date            - errata start date
# end_date              - errata end date
# http                  - True/False:  Publish through http
# https                 - True/False:  Publish through https
# protected             - True/False: Protect this repo with repo authentication
# auth_cert             - Certificate to use if repo authentication is required
# auth_ca               - CA to use if repo authentication is required
# https_ca              - CA to verify https communication
# https_publish_dir     - Optional parameter to override the HTTPS_PUBLISH_DIR, mainly used for unit tests
# http_publish_dir      - Optional parameter to override the HTTP_PUBLISH_DIR, mainly used for unit tests

# -- plugins ------------------------------------------------------------------

class ISODistributor(Distributor):

    def __init__(self):
        super(ISODistributor, self).__init__()

    @classmethod
    def metadata(cls):
        return {
            'id'           : ISO_DISTRIBUTOR_TYPE_ID,
            'display_name' : 'Iso Distributor',
            'types'        : [RPM_TYPE_ID, SRPM_TYPE_ID, DRPM_TYPE_ID, ERRATA_TYPE_ID, DISTRO_TYPE_ID, PKG_CATEGORY_TYPE_ID, PKG_GROUP_TYPE_ID]
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
        auth_cert_bundle = {}
        for key in REQUIRED_CONFIG_KEYS:
            value = config.get(key)
            if value is None:
                msg = _("Missing required configuration key: %(key)s" % {"key":key})
                _LOG.error(msg)
                return False, msg
            if key == 'relative_url':
                relative_path = config.get('relative_url')
                if relative_path is not None and not isinstance(relative_path, basestring):
                    msg = _("relative_url should be a basestring; got %s instead" % relative_path)
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
            if key == 'protected':
                protected = config.get('protected')
                if protected is not None and not isinstance(protected, bool):
                    msg = _("protected should be a boolean; got %s instead" % protected)
                    _LOG.error(msg)
                    return False, msg
            if key == 'auth_cert':
                auth_pem = config.get('auth_cert').encode('utf-8')
                if auth_pem is not None and not util.validate_cert(auth_pem):
                    msg = _("auth_cert is not a valid certificate")
                    _LOG.error(msg)
                    return False, msg
                auth_cert_bundle['cert'] = auth_pem
            if key == 'auth_ca':
                auth_ca = config.get('auth_ca').encode('utf-8')
                if auth_ca is not None and not util.validate_cert(auth_ca):
                    msg = _("auth_ca is not a valid certificate")
                    _LOG.error(msg)
                    return False, msg
                auth_cert_bundle['ca'] = auth_ca

        return True, None

    def cancel_publish_repo(self, repo):
        self.canceled = True
        return metadata.cancel_createrepo(repo.working_dir)

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
            "publish_https":      {"state": "NOT_STARTED"},
            }

        def progress_callback(type_id, status):
            progress_status[type_id] = status
            publish_conduit.set_progress(progress_status)

        repo_working_dir = os.path.join(repo.working_dir, repo.id)

        date_filter = self.create_date_range_filter(config)
        if date_filter:
            # export errata by date and associated rpm units
            progress_status["errata"]["state"] = "STARTED"
            criteria = UnitAssociationCriteria(type_ids=[ERRATA_TYPE_ID], unit_filters=date_filter)
            errata_units = publish_conduit.get_units(criteria)
            criteria = UnitAssociationCriteria(type_ids=[RPM_TYPE_ID, SRPM_TYPE_ID, DRPM_TYPE_ID])
            rpm_units = publish_conduit.get_units(criteria)
            rpm_units = self._get_errata_rpms(errata_units, rpm_units)
            rpm_status, rpm_errors = self._export_rpms(rpm_units, repo_working_dir, progress_callback=progress_callback)
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
            criteria = UnitAssociationCriteria(type_ids=[RPM_TYPE_ID, SRPM_TYPE_ID, DRPM_TYPE_ID])
            rpm_units = publish_conduit.get_units(criteria)
            rpm_status, rpm_errors = self._export_rpms(rpm_units, repo_working_dir, progress_callback=progress_callback)
            progress_status["rpms"]["state"] = "FINISHED"

            # package groups
            progress_status["packagegroups"]["state"] = "STARTED"
            criteria = UnitAssociationCriteria(type_ids=[PKG_GROUP_TYPE_ID, PKG_CATEGORY_TYPE_ID])
            existing_units = publish_conduit.get_units(criteria)
            existing_groups = filter(lambda u : u.type_id in [PKG_GROUP_TYPE_ID], existing_units)
            existing_cats = filter(lambda u : u.type_id in [PKG_CATEGORY_TYPE_ID], existing_units)
            groups_xml_path = comps_util.write_comps_xml(repo, existing_groups, existing_cats)

            # generate metadata
            metadata_status, metadata_errors = metadata.generate_metadata(
                    repo, publish_conduit, config, progress_callback, groups_xml_path)
            _LOG.info("metadata generation complete at target location %s" % repo_working_dir)
            progress_status["packagegroups"]["state"] = "FINISHED"

            progress_status["errata"]["state"] = "STARTED"
            criteria = UnitAssociationCriteria(type_ids=[ERRATA_TYPE_ID])
            errata_units = publish_conduit.get_units(criteria)
            rpm_units = self._get_errata_rpms(errata_units, rpm_units)
            self._export_rpms(rpm_units, repo_working_dir, progress_callback=progress_callback)
            errata_status, errata_errors = self._export_errata(errata_units, repo_working_dir, progress_callback=progress_callback)
            progress_status["errata"]["state"] = "FINISHED"

            # distro units
            progress_status["distribution"]["state"] = "STARTED"
            criteria = UnitAssociationCriteria(type_ids=[DISTRO_TYPE_ID])
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
        # build iso
        repo_iso_working_dir = "%s/%s/%s" % (repo.working_dir, "isos", repo.id)
        try:
            isogen = GenerateIsos(repo_working_dir, repo_iso_working_dir , prefix=repo.id, progress=progress_status)
            progress_status = isogen.run()
        except Exception,e:
            progress_status["isos"]["state"] = "ERROR"
            progress_status["error_details"].append(str(e))
            return progress_status
        progress_status["isos"]["state"] = "FINISHED"

        # Handle publish link for HTTPS
        https_publish_dir = self.get_https_publish_iso_dir(config)
        https_repo_publish_dir = os.path.join(https_publish_dir, repo.id).rstrip('/')
        if config.get("https"):
            # Publish for HTTPS
            self.set_progress("publish_https", {"state" : "IN_PROGRESS"}, progress_callback)
            try:
                _LOG.info("HTTPS Publishing repo <%s> to <%s>" % (repo.id, https_repo_publish_dir))
                util.create_symlink(repo_iso_working_dir, https_repo_publish_dir)
                summary["https_publish_dir"] = https_repo_publish_dir
                self.set_progress("publish_https", {"state" : "FINISHED"}, progress_callback)
            except:
                self.set_progress("publish_https", {"state" : "FAILED"}, progress_callback)
        else:
            self.set_progress("publish_https", {"state" : "SKIPPED"}, progress_callback)
            if os.path.lexists(https_repo_publish_dir):
                _LOG.debug("Removing link for %s since https is not set" % https_repo_publish_dir)
                util.remove_symlink(https_publish_dir, https_repo_publish_dir)

        # Handle publish link for HTTP
        http_publish_dir = self.get_http_publish_iso_dir(config)
        http_repo_publish_dir = os.path.join(http_publish_dir, repo.id).rstrip('/')
        if config.get("http"):
            # Publish for HTTP
            self.set_progress("publish_http", {"state" : "IN_PROGRESS"}, progress_callback)
            try:
                _LOG.info("HTTP Publishing repo <%s> to <%s>" % (repo.id, http_repo_publish_dir))
                util.create_symlink(repo_iso_working_dir, http_repo_publish_dir)
                summary["http_publish_dir"] = http_repo_publish_dir
                self.set_progress("publish_http", {"state" : "FINISHED"}, progress_callback)
            except:
                self.set_progress("publish_http", {"state" : "FAILED"}, progress_callback)
        else:
            self.set_progress("publish_http", {"state" : "SKIPPED"}, progress_callback)
            if os.path.lexists(http_repo_publish_dir):
                _LOG.debug("Removing link for %s since http is not set" % http_repo_publish_dir)
                util.remove_symlink(http_publish_dir, http_repo_publish_dir)
        details["errors"] += metadata_errors
        # metadata generate skipped vs run
        _LOG.info("Publish complete:  summary = <%s>, details = <%s>" % (summary, details))
        if details["errors"]:
            return publish_conduit.build_failure_report(summary, details)
        return publish_conduit.build_success_report(summary, details)

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
            _LOG.info("Unit exists at: %s we need to symlink to: %s" % (source_path, symlink_path))
            try:
                if not util.create_symlink(source_path, symlink_path):
                    msg = "Unable to create symlink for: %s pointing to %s" % (symlink_path, source_path)
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
        if not errata_units:
            return True, []
        try:
            updateinfo_path = updateinfo.updateinfo(errata_units, repo_working_dir)
            if updateinfo_path:
                repodata_dir = os.path.join(repo_working_dir, "repodata")
                if not os.path.exists(repodata_dir):
                    _LOG.error("Missing repodata; cannot run modifyrepo")
                    return False, []
                _LOG.debug("Modifying repo for updateinfo")
                metadata.modify_repo(repodata_dir,  updateinfo_path)
        except metadata.ModifyRepoError, mre:
            msg = "Unable to run modifyrepo to include updateinfo at target location %s; Error: %s" % (repo_working_dir, str(mre))
            errors.append(msg)
            _LOG.error(msg)
            return False, errors
        except Exception, e:
            errors.append(str(e))
            return False, errors
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
                    print "RPM KEY",rpm_key
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
                    if not util.create_symlink(source_path, symlink_path):
                        msg = "Unable to create symlink for: %s pointing to %s" % (symlink_path, source_path)
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