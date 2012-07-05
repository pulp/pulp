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
import os
import shutil
import time

from yum_importer.comps import ImporterComps, PKG_GROUP_TYPE_ID, PKG_CATEGORY_TYPE_ID
from yum_importer.distribution import DISTRO_TYPE_ID
from yum_importer.drpm import DRPM_TYPE_ID
from yum_importer.errata import ImporterErrata, ERRATA_TYPE_ID, link_errata_rpm_units
from yum_importer.importer_rpm import ImporterRPM, RPM_TYPE_ID, SRPM_TYPE_ID, get_existing_units
from pulp.server.managers.repo.unit_association_query import Criteria
from pulp.plugins.importer import Importer
from pulp.plugins.model import SyncReport
from pulp_rpm.yum_plugin import util, depsolver

_ = gettext.gettext
_LOG = logging.getLogger(__name__)

YUM_IMPORTER_TYPE_ID="yum_importer"

REQUIRED_CONFIG_KEYS = []
OPTIONAL_CONFIG_KEYS = ['feed_url', 'ssl_verify', 'ssl_ca_cert', 'ssl_client_cert', 'ssl_client_key',
                        'proxy_url', 'proxy_port', 'proxy_pass', 'proxy_user',
                        'max_speed', 'verify_size', 'verify_checksum', 'num_threads',
                        'newest', 'remove_old', 'num_old_packages', 'purge_orphaned', 'skip', 'checksum_type',
                        'num_retries', 'retry_delay']
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
# skip: List of what content types to skip during sync, options:
#                     ["rpm", "drpm", "errata", "distribution", "packagegroup"]
# checksum_type: checksum type to use for repodata; defaults to source checksum type or sha256
# num_retries: Number of times to retry before declaring an error
# retry_delay: Minimal number of seconds to wait before each retry

class YumImporter(Importer):
    def __init__(self):
        super(YumImporter, self).__init__()
        self.canceled = False
        self.comps = ImporterComps()
        self.errata = ImporterErrata()
        self.importer_rpm = ImporterRPM()

    @classmethod
    def metadata(cls):
        return {
            'id'           : YUM_IMPORTER_TYPE_ID,
            'display_name' : 'Yum Importer',
            'types'        : [DISTRO_TYPE_ID, DRPM_TYPE_ID, ERRATA_TYPE_ID, PKG_GROUP_TYPE_ID, PKG_CATEGORY_TYPE_ID, RPM_TYPE_ID, SRPM_TYPE_ID]
        }

    def validate_config(self, repo, config, related_repos):
        _LOG.info("validate_config invoked, config values are: %s" % (config.repo_plugin_config))
        for key in REQUIRED_CONFIG_KEYS:
            if key not in config.keys():
                msg = _("Missing required configuration key: %(key)s" % {"key":key})
                _LOG.error(msg)
                return False, msg

        for key in config.keys():
            if key not in REQUIRED_CONFIG_KEYS and key not in OPTIONAL_CONFIG_KEYS:
                msg = _("Configuration key '%(key)s' is not supported" % {"key":key})
                _LOG.error(msg)
                return False, msg
            if key == 'feed_url':
                feed_url = config.get('feed_url')
                if not util.validate_feed(feed_url):
                    msg = _("feed_url [%s] does not start with a valid protocol" % feed_url)
                    _LOG.error(msg)
                    return False, msg
            if key == 'ssl_verify':
                ssl_verify = config.get('ssl_verify')
                if ssl_verify is not None and not isinstance(ssl_verify, bool) :
                    msg = _("ssl_verify should be a boolean; got %s instead" % ssl_verify)
                    _LOG.error(msg)
                    return False, msg

            if key == 'ssl_ca_cert':
                ssl_ca_cert = config.get('ssl_ca_cert').encode('utf-8')
                if ssl_ca_cert is not None:
                    if not util.validate_cert(ssl_ca_cert) :
                        msg = _("ssl_ca_cert is not a valid certificate")
                        _LOG.error(msg)
                        return False, msg
                    # ssl_ca_cert is valid, proceed to store it in our repo.working_dir
                    ssl_ca_cert_filename = os.path.join(repo.working_dir, "ssl_ca_cert")
                    try:
                        try:
                            ssl_ca_cert_file = open(ssl_ca_cert_filename, "w")
                            ssl_ca_cert_file.write(ssl_ca_cert)
                        finally:
                            if ssl_ca_cert_file:
                                ssl_ca_cert_file.close()
                    except Exception, e:
                        msg = _("Unable to write ssl_ca_cert to %s" % ssl_ca_cert_filename)
                        _LOG.error(e)
                        _LOG.error(msg)
                        return False, msg

            if key == 'ssl_client_cert':
                ssl_client_cert = config.get('ssl_client_cert').encode('utf-8')
                if ssl_client_cert is not None:
                    if not util.validate_cert(ssl_client_cert) :
                        msg = _("ssl_client_cert is not a valid certificate")
                        _LOG.error(msg)
                        return False, msg
                    # ssl_client_cert is valid, proceed to store it in our repo.working_dir
                    ssl_client_cert_filename = os.path.join(repo.working_dir, "ssl_client_cert")
                    try:
                        try:
                            ssl_client_cert_file = open(ssl_client_cert_filename, "w")
                            ssl_client_cert_file.write(ssl_client_cert)
                        finally:
                            if ssl_client_cert_file:
                                ssl_client_cert_file.close()
                    except Exception, e:
                        msg = _("Unable to write ssl_client_cert to %s" % ssl_client_cert_filename)
                        _LOG.error(e)
                        _LOG.error(msg)
                        return False, msg

            if key == 'ssl_client_key':
                ssl_client_key = config.get('ssl_client_key').encode('utf-8')
                ssl_client_key_filename = os.path.join(repo.working_dir, "ssl_client_key")
                try:
                    try:
                        ssl_client_key_file = open(ssl_client_key_filename, "w")
                        ssl_client_key_file.write(ssl_client_key)
                    finally:
                        if ssl_client_key_file:
                            ssl_client_key_file.close()
                except Exception, e:
                    msg = _("Unable to write ssl_client_cert to %s" % ssl_client_cert_filename)
                    _LOG.error(e)
                    _LOG.error(msg)
                    return False, msg

            if key == 'proxy_url':
                proxy_url = config.get('proxy_url')
                if proxy_url is not None and not util.validate_feed(proxy_url):
                    msg = _("Invalid proxy url: %s" % proxy_url)
                    _LOG.error(msg)
                    return False, msg

            if key == 'proxy_port':
                proxy_port = config.get('proxy_port')
                if proxy_port is not None and isinstance(proxy_port, int):
                    msg = _("Invalid proxy port: %s" % proxy_port)
                    _LOG.error(msg)
                    return False, msg

            if key == 'verify_checksum':
                verify_checksum = config.get('verify_checksum')
                if verify_checksum is not None and not isinstance(verify_checksum, bool) :
                    msg = _("verify_checksum should be a boolean; got %s instead" % verify_checksum)
                    _LOG.error(msg)
                    return False, msg

            if key == 'verify_size':
                verify_size = config.get('verify_size')
                if verify_size is not None and not isinstance(verify_size, bool) :
                    msg = _("verify_size should be a boolean; got %s instead" % verify_size)
                    _LOG.error(msg)
                    return False, msg

            if key == 'max_speed':
                max_speed = config.get('max_speed')
                if max_speed is not None and not isinstance(max_speed, int) :
                    msg = _("max_speed should be an integer; got %s instead" % max_speed)
                    _LOG.error(msg)
                    return False, msg

            if key == 'num_threads':
                num_threads = config.get('num_threads')
                if num_threads is not None and not isinstance(num_threads, int) :
                    msg = _("num_threads should be an integer; got %s instead" % num_threads)
                    _LOG.error(msg)
                    return False, msg

            if key == 'newest':
                newest = config.get('newest')
                if newest is not None and not isinstance(newest, bool) :
                    msg = _("newest should be a boolean; got %s instead" % newest)
                    _LOG.error(msg)
                    return False, msg
            if key == 'remove_old':
                remove_old = config.get('remove_old')
                if remove_old is not None and not isinstance(remove_old, bool) :
                    msg = _("remove_old should be a boolean; got %s instead" % remove_old)
                    _LOG.error(msg)
                    return False, msg

            if key == 'num_old_packages':
                num_old_packages = config.get('num_old_packages')
                if num_old_packages is not None and not isinstance(num_old_packages, int) :
                    msg = _("num_old_packages should be an integer; got %s instead" % num_old_packages)
                    _LOG.error(msg)
                    return False, msg

            if key == 'purge_orphaned':
                purge_orphaned = config.get('purge_orphaned')
                if purge_orphaned is not None and not isinstance(purge_orphaned, bool) :
                    msg = _("purge_orphaned should be a boolean; got %s instead" % purge_orphaned)
                    _LOG.error(msg)
                    return False, msg

            if key == 'skip':
                skip = config.get('skip')
                if skip is not None and not isinstance(skip, list):
                    msg = _("skip should be a list; got %s instead" % skip)
                    _LOG.error(msg)
                    return False, msg

            if key == 'checksum_type':
                checksum_type = config.get('checksum_type')
                if checksum_type is not None and not util.is_valid_checksum_type(checksum_type):
                    msg = _("%s is not a valid checksum type" % checksum_type)
                    _LOG.error(msg)
                    return False, msg
        return True, None

    def importer_added(self, repo, config):
        _LOG.info("importer_added invoked")

    def importer_removed(self, repo, config):
        _LOG.info("importer_removed invoked")

    def import_units(self, source_repo, dest_repo, import_conduit, config, units=None):
        """
        @param source_repo: metadata describing the repository containing the
               units to import
        @type  source_repo: L{pulp.plugins.data.Repository}

        @param dest_repo: metadata describing the repository to import units
               into
        @type  dest_repo: L{pulp.plugins.data.Repository}

        @param import_conduit: provides access to relevant Pulp functionality
        @type  import_conduit: L{pulp.plugins.conduits.unit_import.ImportUnitConduit}

        @param config: plugin configuration
        @type  config: L{pulp.plugins.plugins.config.PluginCallConfiguration}

        @param units: optional list of pre-filtered units to import
        @type  units: list of L{pulp.plugins.data.Unit}
        """
        if not units:
            # If no units are passed in, assume we will use all units from source repo
            units = import_conduit.get_source_units()
        _LOG.info("Importing %s units from %s to %s" % (len(units), source_repo.id, dest_repo.id))
        for u in units:
            # We are assuming that Pulp is telling us about units which already exist in Pulp
            # therefore they have already been downloaded and written to the correct location on the filesystem
            # i.e. we are assuming unit.storage_path is correct and points to the actual unit if appropriate (non-errata, etc).
            #
            if u.unit_key.has_key("filename") and u.storage_path:
                sym_link = os.path.join(dest_repo.working_dir, dest_repo.id, u.unit_key["filename"])
                if os.path.lexists(sym_link):
                    remove_link = True
                    if os.path.islink(sym_link):
                        existing_link_target = os.readlink(sym_link)
                        if os.path.samefile(existing_link_target, u.storage_path):
                            remove_link = False
                    if remove_link:
                        # existing symlink is wrong, remove it
                        os.unlink(sym_link)
                dirpath = os.path.dirname(sym_link)
                if not os.path.exists(dirpath):
                    os.makedirs(dirpath)
                os.symlink(u.storage_path, sym_link)
            import_conduit.associate_unit(u)
        _LOG.info("%s units from %s have been associated to %s" % (len(units), source_repo.id, dest_repo.id))


    def remove_units(self, repo, units, remove_conduit):
        """
        @param repo: metadata describing the repository
        @type  repo: L{pulp.plugins.data.Repository}

        @param units: list of objects describing the units to import in this call
        @type  units: list of L{pulp.plugins.data.Unit}

        @param remove_conduit: provides access to relevant Pulp functionality
        @type  remove_conduit: ?
        """
        _LOG.info("remove_units invoked for %s units" % (len(units)))
        for u in units:
            # Assuming Pulp will delete u.storage_path from filesystem
            sym_link = os.path.join(repo.working_dir, repo.id, u.unit_key["filename"])
            if os.path.lexists(sym_link):
                os.unlink(sym_link)
    # -- actions --------------------------------------------------------------

    def sync_repo(self, repo, sync_conduit, config):
        try:
            status, summary, details = self._sync_repo(repo, sync_conduit, config)
            if status:
                report = sync_conduit.build_success_report(summary, details)
            else:
                report = sync_conduit.build_failure_report(summary, details)
        except Exception, e:
            _LOG.exception("Caught Exception: %s" % (e))
            summary = {}
            summary["error"] = str(e)
            report = sync_conduit.build_failure_report(summary, None)
        return report

    def _sync_repo(self, repo, sync_conduit, config):
        progress_status = {
                "metadata": {"state": "NOT_STARTED"},
                "content": {"state": "NOT_STARTED"},
                "errata": {"state": "NOT_STARTED"},
                "comps": {"state": "NOT_STARTED"},
                }
        def progress_callback(type_id, status):
            if type_id == "content":
                progress_status["metadata"]["state"] = "FINISHED"
            progress_status[type_id] = status
            sync_conduit.set_progress(progress_status)

        sync_conduit.set_progress(progress_status)
        summary = {}
        details = {}
        # sync rpms
        rpm_status, summary["packages"], details["packages"] = self.importer_rpm.sync(repo, sync_conduit, config, progress_callback)

        # sync errata
        errata_status, summary["errata"], details["errata"] = self.errata.sync(repo, sync_conduit, config, progress_callback)

        # sync groups (comps.xml) info
        comps_status, summary["comps"], details["comps"] = self.comps.sync(repo, sync_conduit, config, progress_callback)

        return (rpm_status and errata_status and comps_status), summary, details

    def upload_unit(self, repo, type_id, unit_key, metadata, file_path, conduit, config):
        _LOG.info("Upload Unit Invoked: repo.id <%s> type_id <%s>, unit_key <%s>" % (repo.id, type_id, unit_key))
        try:
            status, summary, details = self._upload_unit(repo, type_id, unit_key, metadata, file_path, conduit, config)
            if status:
                report = SyncReport(True, int(summary['num_units_saved']), 0, 0, summary, details)
            else:
                report = SyncReport(False, int(summary['num_units_saved']), 0, 0, summary, details)
        except Exception, e:
            _LOG.exception("Caught Exception: %s" % (e))
            summary = {}
            summary["error"] = str(e)
            report = SyncReport(False, 0, 0, 0, summary, None)
        return report

    def _upload_unit(self, repo, type_id, unit_key, metadata, file_path, conduit, config):
        _LOG.info("Invoking upload_unit with file_path: %s; metadata: %s; unit_key: %s; type_id: %s" % (file_path, metadata, unit_key, type_id))
        if type_id == RPM_TYPE_ID:
            return self._upload_unit_rpm(repo, unit_key, metadata, file_path, conduit, config)
        elif type_id == ERRATA_TYPE_ID:
            return self._upload_unit_erratum(repo, unit_key, metadata, conduit, config)
        elif type_id in (PKG_GROUP_TYPE_ID, PKG_CATEGORY_TYPE_ID):
            return self._upload_unit_pkg_group_or_category(repo, type_id, unit_key, metadata, conduit, config)
        else:
            return False, {}, {}

    def _upload_unit_rpm(self, repo, unit_key, metadata, file_path, conduit, config):
        summary = {}
        details = {'errors' : []}
        summary['filename'] = metadata['filename']
        summary['num_units_processed'] = len([file_path])
        summary['num_units_saved'] = 0
        if not os.path.exists(file_path):
            msg = "File path [%s] missing" % file_path
            _LOG.error(msg)
            details['errors'].append(msg)
            return False, summary, details
        relative_path = "%s/%s/%s/%s/%s/%s" % (unit_key['name'], unit_key['version'],
                                                        unit_key['release'], unit_key['arch'], unit_key['checksum'], metadata['filename'])
        u = conduit.init_unit(RPM_TYPE_ID, unit_key, metadata, relative_path)
        new_path = u.storage_path
        try:
            if os.path.exists(new_path):
                existing_checksum = util.get_file_checksum(filename=new_path, hashtype=unit_key['checksumtype'])
                if existing_checksum != unit_key['checksum']:
                    # checksums dont match, remove existing file
                    os.remove(new_path)
                else:
                    _LOG.info("Existing file is the same ")
            if not os.path.isdir(os.path.dirname(new_path)):
                os.makedirs(os.path.dirname(new_path))
            # copy the unit to the final path
            shutil.copy(file_path, new_path)
        except (IOError, OSError), e:
            msg = "Error copying upload file to final location [%s]; Error %s" % (new_path, e)
            details['errors'].append(msg)
            _LOG.error(msg)
            return False, summary, details
        conduit.save_unit(u)
        summary['num_units_processed'] = len([file_path])
        summary['num_units_saved'] = len([file_path])
        _LOG.info("unit %s successfully saved" % u)
        # symlink content to repo working directory
        symlink_path = "%s/%s/%s" % (repo.working_dir, repo.id, metadata['filename'])
        try:
            if os.path.islink(symlink_path):
                os.unlink(symlink_path)
            if not os.path.isdir(os.path.dirname(symlink_path)):
                os.makedirs(os.path.dirname(symlink_path))
            os.symlink(new_path, symlink_path)
            _LOG.info("Successfully symlinked to final location %s" % symlink_path)
        except (IOError, OSError), e:
            msg = "Error creating a symlink to repo working directory; Error %s" % e
            _LOG.error(msg)
            details['errors'].append(msg)
        summary["state"] = "FINISHED"
        if len(details['errors']):
            summary['num_errors'] = len(details['errors'])
            summary["state"] = "FAILED"
            return False, summary, details
        _LOG.info("Upload complete with summary: %s; Details: %s" % (summary, details))
        return True, summary, details
            
    def _upload_unit_erratum(self, repo, unit_key, metadata, conduit, config):
        summary = {'num_units_saved' : 0}
        details = {'errors' : []}
        try:
            u = conduit.init_unit(ERRATA_TYPE_ID, unit_key, metadata, None)
            conduit.save_unit(u)
            summary['num_units_saved'] += 1
            link_errata_rpm_units(conduit, {unit_key['id']: u})
        except Exception, e:
            msg = "Error uploading errata unit %s; Error %s" % (unit_key['id'], e)
            _LOG.error(msg)
            details['errors'].append(msg)
            summary['state'] = 'FAILED'
            return False, summary, details
        summary['state'] = 'FINISHED'
        return True, summary, details

    def _upload_unit_pkg_group_or_category(self, repo, type_id, unit_key, metadata, conduit, config):
        summary = {}
        details = {'errors' : []}
        try:
            u = conduit.init_unit(type_id, unit_key, metadata, None)
            conduit.save_unit(u)
        except Exception, e:
            msg = "Error uploading %s unit %s; Error %s" % (type_id, unit_key['id'], e)
            _LOG.error(msg)
            details['errors'].append(msg)
            summary['state'] = 'FAILED'
            return False, summary, details
        summary['state'] = 'FINISHED'
        return True, summary, details

    def resolve_dependencies(self, repo, units, dependency_conduit, config):
        _LOG.info("Resolve Dependencies Invoked")
        try:
            status, summary, details = self._resolve_dependencies(repo, units, dependency_conduit, config)
            if status:
                report = SyncReport(True, 0, 0, 0, summary, details)
            else:
                report = SyncReport(False, 0, 0, 0, summary, details)
        except Exception, e:
            _LOG.error("Caught Exception: %s" % (e))
            summary = {}
            summary["error"] = str(e)
            report = SyncReport(False, 0, 0, 0, summary, None)
        return report

    def _resolve_dependencies(self, repo, units, dependency_conduit, config):
        summary = {}
        details = {'errors' : []}
        pkglist =  []
        for unit in units:
            if unit.type_id == 'rpm':
                print "%s-%s-%s.%s" % (unit.unit_key['name'], unit.unit_key['version'], unit.unit_key['release'], unit.unit_key['arch'])
                pkglist.append("%s-%s-%s.%s" % (unit.unit_key['name'], unit.unit_key['version'], unit.unit_key['release'], unit.unit_key['arch']))
        dsolve = depsolver.DepSolver([repo], pkgs=pkglist)
        if config.get('recursive'):
            results = dsolve.getRecursiveDepList()
        else:
            results = dsolve.getDependencylist()
        solved, unsolved = dsolve.processResults(results)
        dep_pkgs_map = {}
        _LOG.info(" results from depsolver %s" % results)
        criteria = Criteria(type_ids=[RPM_TYPE_ID])
        existing_units = get_existing_units(dependency_conduit, criteria)
        for dep, pkgs in solved.items():
            dep_pkgs_map[dep] = []
            for pkg in pkgs:
                if not existing_units.has_key(pkg):
                    continue
                epkg = existing_units[pkg]
                dep_pkgs_map[dep].append(epkg)
        _LOG.debug("deps packages suggested %s" % solved)
        summary['resolved'] = dep_pkgs_map
        summary['unresolved'] = unsolved
        details['printable_dependency_result'] = dsolve.printable_result(results)
        dsolve.cleanup()
        summary['state'] = 'FINISHED'
        return True, summary, details

    def cancel_sync_repo(self):
        self.canceled = True
        self.comps.cancel_sync()
        self.errata.cancel_sync()
        self.importer_rpm.cancel_sync()

