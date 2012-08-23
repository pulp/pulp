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
import traceback
from pulp_rpm.yum_plugin import util
from pulp_rpm.yum_plugin import util, updateinfo, metadata
from iso_distributor import iso_util
_LOG = util.getLogger(__name__)
_ = gettext.gettext

class RepoExporter(object):

    def __init__(self, repo_working_dir, skip=None):
        self.repo_working_dir = repo_working_dir
        self.skip = skip or []

    def init_progress(self):
        return  {
            "state": "IN_PROGRESS",
            "num_success" : 0,
            "num_error" : 0,
            "items_left" : 0,
            "items_total" : 0,
            "error_details" : [],
            }

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

    def export_rpms(self, rpm_units, progress_callback=None):
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
        summary = {}
        symlink_dir = self.repo_working_dir
        packages_progress_status = self.init_progress()
        if 'rpm' in self.skip:
            packages_progress_status["state"] = "SKIPPED"
            self.set_progress("rpms", packages_progress_status, progress_callback)
            _LOG.info("rpm unit type in skip list [%s]; skipping export" % self.skip)
            return summary, []
        packages_progress_status["num_success"] = 0
        packages_progress_status["items_left"] = len(rpm_units)
        packages_progress_status["items_total"] = len(rpm_units)
        errors = []
        for u in rpm_units:
            self.set_progress("rpms", packages_progress_status, progress_callback)
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
        summary["num_package_units_attempted"] = len(rpm_units)
        summary["num_package_units_exported"] = len(rpm_units) - len(errors)
        summary["num_package_units_errors"] = len(errors)
        if errors:
            packages_progress_status["error_details"] = errors
            return summary, errors
        packages_progress_status["state"] = "FINISHED"
        self.set_progress("rpms", packages_progress_status, progress_callback)
        return summary, errors

    def export_errata(self, errata_units, progress_callback=None):
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
        summary = {}
        repo_working_dir = self.repo_working_dir
        errors = []
        errata_progress_status = self.init_progress()
        if not errata_units:
            errata_progress_status["state"] = "FINISHED"
            self.set_progress("errata", errata_progress_status, progress_callback)
            return summary, errors
        if 'errata' in self.skip:
            errata_progress_status["state"] = "SKIPPED"
            self.set_progress("errata", errata_progress_status, progress_callback)
            _LOG.info("errata unit type in skip list [%s]; skipping export" % self.skip)
            return summary, errors
        errata_progress_status["num_success"] = 0
        errata_progress_status["items_left"] = len(errata_units)
        errata_progress_status["items_total"] = len(errata_units)
        summary["num_errata_units_exported"] = 0
        try:
            errata_progress_status['state'] = "IN_PROGRESS"
            self.set_progress("errata", errata_progress_status, progress_callback)

            updateinfo_path = updateinfo.updateinfo(errata_units, repo_working_dir)
            if updateinfo_path:
                repodata_dir = os.path.join(repo_working_dir, "repodata")
                if not os.path.exists(repodata_dir):
                    _LOG.error("Missing repodata; cannot run modifyrepo")
                    return summary, errors
                _LOG.debug("Modifying repo for updateinfo")
                metadata.modify_repo(repodata_dir,  updateinfo_path)
            errata_progress_status["num_success"] = len(errata_units)
            errata_progress_status["items_left"] = 0
        except metadata.ModifyRepoError, mre:
            details["errors"] = errors
            msg = "Unable to run modifyrepo to include updateinfo at target location %s; Error: %s" % (repo_working_dir, str(mre))
            errors.append(msg)
            _LOG.error(msg)
            errata_progress_status['state'] = "FAILED"
            errata_progress_status["num_success"] = 0
            errata_progress_status["items_left"] = len(errata_units)
            return summary, errors
        except Exception, e:
            details["errors"] = errors
            errors.append(str(e))
            errata_progress_status['state'] = "FAILED"
            errata_progress_status["num_success"] = 0
            errata_progress_status["items_left"] = len(errata_units)
            return summary, errors
        errata_progress_status['state'] = "FINISHED"
        self.set_progress("errata", errata_progress_status, progress_callback)
        summary["num_errata_units_exported"] = len(errata_units)
        return summary, errors

    def get_errata_rpms(self, errata_units, rpm_units):
        existing_rpm_units = iso_util.form_unit_key_map(rpm_units)
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
                    rpm_key = iso_util.form_lookup_key(pinfo)
                    if rpm_key in existing_rpm_units.keys():
                        rpm_unit = existing_rpm_units[rpm_key]
                        _LOG.info("Found matching rpm unit %s" % rpm_unit)
                        rpm_units.append(rpm_unit)
        return rpm_units

    def export_distributions(self, units, progress_callback=None):
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
        summary = {}
        symlink_dir = self.repo_working_dir
        distro_progress_status = self.init_progress()
        self.set_progress("distribution", distro_progress_status, progress_callback)
        if 'distribution' in self.skip:
            distro_progress_status["state"] = "SKIPPED"
            self.set_progress("distribution", distro_progress_status, progress_callback)
            _LOG.info("distribution unit type in skip list [%s]; skipping export" % self.skip)
            return summary, []
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
            return summary, errors
        distro_progress_status["state"] = "FINISHED"
        summary["num_distribution_units_attempted"] = len(units)
        summary["num_distribution_units_exported"] = len(units) - len(errors)
        summary["num_distribution_units_errors"] = len(errors)
        self.set_progress("distribution", distro_progress_status, progress_callback)
        return summary, errors

