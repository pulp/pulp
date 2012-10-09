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
import os
import shutil
import time
import itertools

from yum_importer.comps import ImporterComps
from yum_importer.errata import ImporterErrata, link_errata_rpm_units
from yum_importer.importer_rpm import ImporterRPM, get_existing_units, form_lookup_key
from pulp.server.db.model.criteria import UnitAssociationCriteria
from pulp.plugins.importer import Importer
from pulp.plugins.model import Unit, SyncReport
from pulp_rpm.common.ids import TYPE_ID_IMPORTER_YUM, TYPE_ID_PKG_GROUP, TYPE_ID_PKG_CATEGORY, TYPE_ID_DISTRO,\
        TYPE_ID_DRPM, TYPE_ID_ERRATA, TYPE_ID_RPM, TYPE_ID_SRPM
from pulp_rpm.yum_plugin import util, depsolver
from pulp_rpm.yum_plugin.metadata import get_package_xml

_ = gettext.gettext
_LOG = util.getLogger(__name__)


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
            'id'           : TYPE_ID_IMPORTER_YUM,
            'display_name' : 'Yum Importer',
            'types'        : [TYPE_ID_DISTRO, TYPE_ID_DRPM, TYPE_ID_ERRATA, TYPE_ID_PKG_GROUP, TYPE_ID_PKG_CATEGORY, TYPE_ID_RPM, TYPE_ID_SRPM]
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

            if key == 'resolve_dependencies':
                value = config.get(key)
                if value is not None and not isinstance(value, bool) :
                    msg = _("%(k)s should be a bool; got '%(v)s' instead") % {'k' : key, 'v' : value}
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
        existing_rpm_units_dict = get_existing_units(import_conduit, criteria=UnitAssociationCriteria(type_ids=[TYPE_ID_RPM, TYPE_ID_SRPM]))
        for u in units:
            import_conduit.associate_unit(u)
            # do any additional work associated with the unit
            if u.type_id == TYPE_ID_RPM:
                # if its an rpm unit process dependencies and import them as well
                self._import_unit_dependencies(source_repo, [u], import_conduit, config, existing_rpm_units=existing_rpm_units_dict)
            if u.type_id == TYPE_ID_ERRATA:
                # if erratum, lookup deps and process associated units
                self._import_errata_unit_rpms(source_repo, u, import_conduit, config, existing_rpm_units_dict)
            if u.type_id in [TYPE_ID_PKG_CATEGORY, TYPE_ID_PKG_GROUP]:
                #TODO
                pass
        _LOG.debug("%s units from %s have been associated to %s" % (len(units), source_repo.id, dest_repo.id))

    def _import_errata_unit_rpms(self, source_repo, erratum_unit, import_conduit, config, existing_rpm_units=None):
        """
        lookup rpms units associated with an erratum; resolve deps and import rpm units
        """
        pkglist = erratum_unit.metadata['pkglist']
        existing_rpm_units = existing_rpm_units or {}
        for pkg in pkglist:
            for pinfo in pkg['packages']:
                if not pinfo.has_key('sum'):
                    _LOG.debug("Missing checksum info on package <%s> for linking a rpm to an erratum." % (pinfo))
                    continue
                pinfo['checksumtype'], pinfo['checksum'] = pinfo['sum']
                rpm_key = form_lookup_key(pinfo)
                if rpm_key in existing_rpm_units.keys():
                    rpm_unit = existing_rpm_units[rpm_key]
                    import_conduit.associate_unit(rpm_unit)
                    # process any deps
                    self._import_unit_dependencies(source_repo, [rpm_unit], import_conduit, config, existing_rpm_units=existing_rpm_units)
                    _LOG.debug("Found matching rpm unit %s" % rpm_unit)
                else:
                    _LOG.debug("rpm unit %s not found; skipping" % pinfo)

    def _import_unit_dependencies(self, source_repo, units, import_conduit, config, existing_rpm_units=None):
        """
        Lookup any dependencies associated with the units and associate them through the import conduit
        """
        if not config.get('resolve_dependencies'):
            # config option turned off, nothing to do
            _LOG.debug("resolve dependencies option is not enabled; skip dependency solving")
            return
        _LOG.debug("resolving dependencies associated with rpm units %s" % units)
        missing_deps =\
            self.find_missing_dependencies(source_repo, units, import_conduit, config, existing_rpm_units=existing_rpm_units)
        _LOG.debug("missing deps found %s" % missing_deps)
        for dep in missing_deps:
            import_conduit.associate_unit(dep)

    def remove_units(self, repo, units, config):
        """
        @param repo: metadata describing the repository
        @type  repo: L{pulp.plugins.data.Repository}

        @param units: list of objects describing the units to import in this call
        @type  units: list of L{pulp.plugins.data.Unit}

        @param remove_conduit: provides access to relevant Pulp functionality
        @type  remove_conduit: ?
        """
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
            num_units_saved = 0
            status, summary, details = self._upload_unit(repo, type_id, unit_key, metadata, file_path, conduit, config)
            if summary.has_key("num_units_saved"):
                num_units_saved = int(summary["num_units_saved"])
            if status:
                report = SyncReport(True, num_units_saved, 0, 0, summary, details)
            else:
                report = SyncReport(False, num_units_saved, 0, 0, summary, details)
        except Exception, e:
            _LOG.exception("Caught Exception: %s" % (e))
            summary = {}
            summary["error"] = str(e)
            report = SyncReport(False, 0, 0, 0, summary, None)
        return report

    def _upload_unit(self, repo, type_id, unit_key, metadata, file_path, conduit, config):
        if type_id == TYPE_ID_RPM:
            return self._upload_unit_rpm(repo, unit_key, metadata, file_path, conduit, config)
        elif type_id == TYPE_ID_ERRATA:
            return self._upload_unit_erratum(repo, unit_key, metadata, conduit, config)
        elif type_id in (TYPE_ID_PKG_GROUP, TYPE_ID_PKG_CATEGORY):
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
        # get the xml dumps for the pkg
        metadata["repodata"] = get_package_xml(file_path)
        u = conduit.init_unit(TYPE_ID_RPM, unit_key, metadata, relative_path)
        new_path = u.storage_path
        try:
            if os.path.exists(new_path):
                existing_checksum = util.get_file_checksum(filename=new_path, hashtype=unit_key['checksumtype'])
                if existing_checksum != unit_key['checksum']:
                    # checksums dont match, remove existing file
                    os.remove(new_path)
                else:
                    _LOG.debug("Existing file is the same ")
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
        _LOG.debug("unit %s successfully saved" % u)
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
            u = conduit.init_unit(TYPE_ID_ERRATA, unit_key, metadata, None)
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
        summary['num_units_saved'] = 1
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
        result_dict = {}
        pkglist =  self.pkglist(units)
        dsolve = depsolver.DepSolver([repo], pkgs=pkglist)
        if config.get('recursive'):
            results = dsolve.getRecursiveDepList()
        else:
            results = dsolve.getDependencylist()
        solved, unsolved = dsolve.processResults(results)
        dep_pkgs_map = {}
        _LOG.debug(" results from depsolver %s" % results)
        criteria = UnitAssociationCriteria(type_ids=[TYPE_ID_RPM])
        existing_units = get_existing_units(dependency_conduit, criteria)
        for dep, pkgs in solved.items():
            dep_pkgs_map[dep] = []
            for pkg in pkgs:
                if not existing_units.has_key(pkg):
                    continue
                epkg = existing_units[pkg]
                dep_pkgs_map[dep].append(epkg.unit_key)
        _LOG.debug("deps packages suggested %s" % solved)
        result_dict['resolved'] = dep_pkgs_map
        result_dict['unresolved'] = unsolved
        result_dict['printable_dependency_result'] = dsolve.printable_result(results)
        dsolve.cleanup()
        _LOG.debug("result dict %s" % result_dict)
        return result_dict

    def cancel_sync_repo(self, call_request, call_report):
        self.canceled = True
        self.comps.cancel_sync()
        self.errata.cancel_sync()
        self.importer_rpm.cancel_sync()

    def pkglist(self, units):
        """
        Convert model units to NEVRA package names.
        @param units: A list of content units.
            Each unit is: L{pulp.server.plugins.model.Unit}
        @type units: list
        @return: A list of fully qualified package names: NEVRA.
        @rtype: list
        """
        pkglist = []
        for unit in units:
            if unit.type_id != TYPE_ID_RPM:
                continue
            pkglist.append("%s-%s-%s.%s" % \
                (unit.unit_key['name'],
                 unit.unit_key['version'],
                 unit.unit_key['release'],
                 unit.unit_key['arch']))
        return pkglist

    def keylist(self, unit_keys):
        """
        Convert a list of unit key (dict) into a list of unit key (tuple)
        that can be used to index into the dict of existing units.
        @param unit_keys: A list of unit keys.
            Each key is an NEVRA dict.
        @type unit_keys: list
        @return: A list of key (tuples).
        @rtype: list
        """
        keylist = []
        for key in unit_keys:
            keylist.append(
                (key['name'],
                 key['epoch'],
                 key['version'],
                 key['release'],
                 key['arch'],
                 key['checksumtype'],
                 key['checksum']))
        return keylist

    def find_missing_dependencies(self, repo, units, conduit, config, existing_rpm_units=None):
        """
        Find dependencies within the specified repository that are not
        included in the specified I{units} list.  This method is intended to
        be used by import_units() to ensure that all dependencies of imported
        units are satisfied.
        @param repo: A plugin repo model object.
        @type repo: L{pulp.plugins.model.Repository}
        @param units: A list of content units.
            Unit is: L{pulp.plugins.model.Unit}
        @type units: list
        @param conduit: An import conduit.
        @type conduit: L{pulp.plugins.conduits.unit_import.ImportConduit}
        @param config: plugin configuration
        @type  config: L{pulp.server.plugins.config.PluginCallConfiguration}
        @param existing_rpm_units: a dict of existing rpm unit key and unit
        @type existing_rpm_units: {}
        @return: The list of missing dependencies (units).
            Unit is: L{pulp.plugins.model.Unit}
        @rtype: list
        """
        missing_deps = []
        units = [u for u in units if u.type_id == TYPE_ID_RPM]
        deps = self.resolve_dependencies(repo, units, conduit, config)
        resolved = itertools.chain(*deps['resolved'].values())
        if resolved:
            keylist = self.keylist(resolved)
            inventory = existing_rpm_units
            for key in keylist:
                unit = inventory.get(key)
                if unit is None:
                    continue
                missing_deps.append(unit)
        return missing_deps