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
from pulp.server.managers.repo.unit_association_query import Criteria

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

    def publish_repo(self, repo, publish_conduit, config):
        publish_start_time = time.time()
        _LOG.info("Start publish time %s" % publish_start_time)
        summary = {}
        details = {}
        progress_status = {
            "rpms":               {"state": "NOT_STARTED"},
            "errata":             {"state": "NOT_STARTED"},
            "distribution":       {"state": "NOT_STARTED"},
            "metadata":           {"state": "NOT_STARTED"},
            "packagegroups":      {"state": "NOT_STARTED"},
            "isos":               {"state": "NOT_STARTED"},
            "publish_http":       {"state": "NOT_STARTED"},
            "publish_https":      {"state": "NOT_STARTED"},
            }

        def progress_callback(type_id, status):
            progress_status[type_id] = status
            publish_conduit.set_progress(progress_status)

        repo_working_dir = os.path.join(repo.working_dir, repo.id)

        # rpm units
        progress_status["rpms"]["state"] = "STARTED"
        criteria = Criteria(type_ids=[RPM_TYPE_ID, SRPM_TYPE_ID])
        rpm_units = publish_conduit.get_units(criteria)
        self._export_rpms(rpm_units, repo_working_dir, progress_callback=progress_callback)
        progress_status["rpms"]["state"] = "FINISHED"

        # errata units
        progress_status["errata"]["state"] = "STARTED"
        criteria = Criteria(type_ids=[ERRATA_TYPE_ID])
        errata_units = publish_conduit.get_units(criteria)
        rpm_units = self._get_errata_rpms(errata_units, rpm_units)
        self._export_rpms(rpm_units, repo_working_dir, progress_callback=progress_callback)
        self._export_errata(errata_units, repo_working_dir, progress_callback=progress_callback)
        progress_status["errata"]["state"] = "FINISHED"

        # build iso
#        repo_iso_working_dir = "%s/%s" % (repo.working_dir, "isos")
#        try:
#            isogen = GenerateIsos(repo_working_dir, repo_iso_working_dir , progress=progress_status)
#            progress_status = isogen.run()
#        except Exception,e:
#            progress_status["isos"]["state"] = "ERROR"
#            progress_status["error_details"].append(str(e))
#            return progress_status
#        progress_status["isos"]["state"] = "FINISHED"
        return progress_status

    def _export_rpms(self, rpm_units, symlink_dir, progress_callback=None):
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
        # generate metadata
        try:
            metadata.create_repo(symlink_dir)
            _LOG.info("metadata generation complete at target location %s" % symlink_dir)
        except metadata.CreateRepoError, cre:
            msg = "Unable to generate metadata for exported packages in target directory %s; Error: %s" % (symlink_dir, str(cre))
            errors.append(msg)
            _LOG.error(msg)
            return False, errors
        return True, []

    def _export_errata(self, errata_units, repo_working_dir, progress_callback=None):
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

def form_lookup_key(rpm):
    rpm_key = (rpm["name"], rpm["epoch"], rpm["version"], rpm['release'], rpm["arch"], rpm["checksumtype"], rpm["checksum"])
    return rpm_key

def form_unit_key_map(units):
   existing_units = {}
   for u in units:
       key = form_lookup_key(u.unit_key)
       existing_units[key] = u
   return existing_units