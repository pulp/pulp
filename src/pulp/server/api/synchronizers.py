# -*- coding: utf-8 -*-
#
# Copyright © 2010-2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

import gzip
import logging
import os
import random
import re

import shutil
import sys
import time
import traceback
from threading import Lock
from urlparse import urlparse

import yum
from grinder.BaseFetch import BaseFetch
from grinder.GrinderCallback import ProgressReport
from grinder.RepoFetch import YumRepoGrinder

import pulp.server.comps_util
import pulp.server.util
from pulp.server import config, constants, updateinfo
from pulp.server.api.distribution import DistributionApi
from pulp.server.api.errata import ErrataApi, ErrataHasReferences
from pulp.server.api.filter import FilterApi
from pulp.server.api.package import PackageApi
from pulp.server.api.repo import RepoApi
from pulp.server.db.model import Delta, DuplicateKeyError
from pulp.server.tasking.exception import CancelException


log = logging.getLogger(__name__)
# synchronization classes -----------------------------------------------------

class InvalidPathError(Exception):
    pass

def yum_rhn_progress_callback(info):
    """
    This method will take in a GrinderCallback.ProgressReport object and
    transform it to a dictionary.
    """
    if type(info) == type({}):
        # if this is already a dictionary than just return it
        return info

    fields = ('status',
              'item_name',
              'item_type',
              'items_left',
              'items_total',
              'size_left',
              'size_total',
              'num_error',
              'num_success',
              'num_download',
              'details',
              'error_details',
              'step',)
    values = tuple(getattr(info, f) for f in fields)
    return dict(zip(fields, values))


def local_progress_callback(progress):
    # Pass through, we don't need to convert anything
    return progress

class BaseSynchronizer(object):

    def __init__(self):
        self.repo_api = RepoApi()
        self.package_api = PackageApi()
        self.errata_api = ErrataApi()
        self.distro_api = DistributionApi()
        self.filter_api = FilterApi()
        self.progress = {
            'status': 'running',
            'item_name': None,
            'item_type': None,
            'items_total': 0,
            'items_remaining': 0,
            'size_total': 0,
            'size_left': 0,
            'num_error': 0,
            'num_success': 0,
            'num_download': 0,
            'details':{},
            'error_details':[],
            'step': "STARTING",
        }
        self.stopped = False
        self.callback = None

    def stop(self):
        self.stopped = True

    def set_callback(self, callback):
        self.callback = callback

    def progress_callback(self, **kwargs):
        """
        Callback called to update the pulp task's progress
        """
        if not self.callback:
            return
        for key in kwargs:
            self.progress[key] = kwargs[key]
        self.callback(self.progress)

    # Point of this method is to return what packages exist in the repo after being syncd
    def add_packages_from_dir(self, dir, repo_id, skip=None):
        repo = self.repo_api._get_existing_repo(repo_id)
        if not skip:
            skip = {}
        added_packages = {}
        if not skip.has_key('packages') or skip['packages'] != 1:
            startTime = time.time()
            log.debug("Begin to add packages from %s into %s" % (dir, repo['id']))
            package_list = pulp.server.util.get_repo_packages(dir)
            log.debug("Processing %s potential packages" % (len(package_list)))
            for package in package_list:
                package = self.import_package(package, repo_id, repo_defined=True)
                if (package is not None):
                    added_packages[package["id"]] = package
            endTime = time.time()
            log.debug("Repo: %s read [%s] packages took %s seconds" %
                    (repo['id'], len(added_packages), endTime - startTime))
        else:
            log.info("Skipping package imports from sync process")
        self.repo_api.collection.save(repo, safe=True)
        return added_packages

    def add_distribution_from_dir(self, dir, repo_id, skip=None):
        repo = self.repo_api.repository(repo_id)
        if not skip.has_key('distribution') or skip['distribution'] != 1:
            # process kickstart files/images part of the repo
            self._process_repo_images(dir, repo)
        else:
            log.info("skipping distribution imports from sync process")
        self.repo_api.collection.save(repo, safe=True)

    def import_metadata(self, dir, repo_id, skip=None):
        added_errataids = []
        repo = self.repo_api.repository(repo_id)
        repomd_xml_path = os.path.join(dir.encode("ascii", "ignore"), 'repodata/repomd.xml')
        if os.path.isfile(repomd_xml_path):
            repo["repomd_xml_path"] = repomd_xml_path
            ftypes = pulp.server.util.get_repomd_filetypes(repomd_xml_path)
            log.debug("repodata has filetypes of %s" % (ftypes))
            if "group" in ftypes:
                group_xml_path = pulp.server.util.get_repomd_filetype_path(repomd_xml_path, "group")
                group_xml_path = os.path.join(dir.encode("ascii", "ignore"), group_xml_path)
                if os.path.isfile(group_xml_path):
                    groupfile = open(group_xml_path, "r")
                    repo['group_xml_path'] = group_xml_path
                    self.sync_groups_data(groupfile, repo)
                    log.info("Loaded group info from %s" % (group_xml_path))
                else:
                    log.info("Group info not found at file: %s" % (group_xml_path))
            if "group_gz" in ftypes:
                group_gz_xml_path = pulp.server.util.get_repomd_filetype_path(
                        repomd_xml_path, "group_gz")
                group_gz_xml_path = os.path.join(dir.encode("ascii", "ignore"),
                        group_gz_xml_path)
                repo['group_gz_xml_path'] = group_gz_xml_path
            if "updateinfo" in ftypes and (not skip.has_key('errata') or skip['errata'] != 1):
                updateinfo_xml_path = pulp.server.util.get_repomd_filetype_path(
                        repomd_xml_path, "updateinfo")
                updateinfo_xml_path = os.path.join(dir.encode("ascii", "ignore"),
                        updateinfo_xml_path)
                log.info("updateinfo is found in repomd.xml, it's path is %s" % \
                        (updateinfo_xml_path))
                added_errataids = self.sync_updateinfo_data(updateinfo_xml_path, repo)
                log.debug("Loaded updateinfo from %s for %s" % \
                        (updateinfo_xml_path, repo["id"]))
            else:
                log.info("Skipping errata imports from sync process")
        self.repo_api.collection.save(repo, safe=True)
        return added_errataids

    def _process_repo_images(self, repodir, repo):
        log.debug("Processing any images synced as part of the repo")
        images_dir = os.path.join(repodir, "images")
        if not os.path.exists(images_dir):
            log.info("No image files to import to repo..")
            return
        # Handle distributions that are part of repo syncs
        files = pulp.server.util.listdir(images_dir) or []
        id = description = "ks-" + repo['id'] + "-" + repo['arch']
        distro = self.distro_api.create(id, description, repo["relative_path"], files)
        if distro['id'] not in repo['distributionid']:
            repo['distributionid'].append(distro['id'])
            log.info("Created a distributionID %s" % distro['id'])
        if not repo['publish']:
            # the repo is not published, dont expose the repo yet
            return
        distro_path = os.path.join(constants.LOCAL_STORAGE, "published", "ks")
        if not os.path.isdir(distro_path):
            os.mkdir(distro_path)
        source_path = os.path.join(pulp.server.util.top_repos_location(),
                repo["relative_path"])
        link_path = os.path.join(distro_path, repo["relative_path"])
        pulp.server.util.create_rel_symlink(source_path, link_path)
        log.debug("Associated distribution %s to repo %s" % (distro['id'], repo['id']))

    def __import_package_with_retry(self, package, repo_defined=False, num_retries=5):
        file_name = os.path.basename(package.relativepath)
        hashtype = "sha256"
        checksum = package.checksum
        try:
            newpkg = self.package_api.create(
                package.name,
                package.epoch,
                package.version,
                package.release,
                package.arch,
                package.description,
                hashtype,
                checksum,
                file_name,
                repo_defined=repo_defined)
        except DuplicateKeyError, e:
            found = self.package_api.packages(
                name=package.name,
                epoch=package.epoch,
                version=package.version,
                release=package.release,
                arch=package.arch,
                filename=file_name,
                checksum_type=hashtype,
                checksum=checksum)
            if not found and num_retries > 0:
                # https://bugzilla.redhat.com/show_bug.cgi?id=734782
                # retry for infrequent scenario of getting a DuplicateKeyError
                # yet the document isn't available yet for a find()
                time.sleep(random.randrange(1, 10, 1))
                return self.__safe_import(package, repo_defined, num_retries=num_retries-1)
            if not found:
                log.error(e)
                log.error("Caught DuplicateKeyError yet we didn't find a matching package in database")
                log.error("Originally tried to create: name=%s, epoch=%s, version=%s, arch=%s, hashtype=%s, checksum=%s, file_name=%s" \
                    % (package.name, package.epoch, package.version, package.arch, hashtype, checksum, file_name))
                raise
            newpkg = found[0]
        return newpkg

    def import_package(self, package, repo_id=None, repo_defined=False):
        """
        @param package - package to add to repo
        @param repo_id - repo_id to hold package
        @param repo_defined -  flag to mark if this package is part of the
                        repo source definition, or if it's
                        something manually added later
        """
        try:
            file_name = os.path.basename(package.relativepath)
            newpkg = self.__import_package_with_retry(package, repo_defined)
            # update dependencies
            for dep in package.requires:
                if not newpkg.has_key("requires"):
                    newpkg["requires"] = []
                newpkg["requires"].append(dep[0])
            for prov in package.provides:
                if not newpkg.has_key("provides"):
                    newpkg["provides"] = []
                newpkg["provides"].append(prov[0])
            newpkg["buildhost"] = package.buildhost
            newpkg["size"] = package.size
            newpkg["group"] = package.group
            newpkg["license"] = package.license
            newpkg["vendor"]  = package.vendor
            # update filter
            filter = ['requires', 'provides', 'buildhost',
                      'size' , 'group', 'license', 'vendor']
            # set the download URL
            if repo_id:
                filter.append('download_url')
                newpkg["download_url"] = \
                    constants.SERVER_SCHEME \
                    + config.config.get('server', 'server_name') \
                    + "/" \
                    + config.config.get('server', 'relative_url') \
                    + "/" \
                    + repo_id \
                    + "/" \
                    + file_name
            newpkg = pulp.server.util.translate_to_utf8(newpkg)
            delta = Delta(newpkg, filter)
            self.package_api.update(newpkg["id"], delta)
            return newpkg
        except Exception, e:
            log.error('Package "%s", import failed', package, exc_info=True)
            raise

    def sync_groups_data(self, compsfile, repo):
        """
        Synchronizes package group/category info from a repo's group metadata
        Caller is responsible for saving repo to db.
        """
        try:
            comps = yum.comps.Comps()
            comps.add(compsfile)
            # Remove all "repo_defined" groups/categories
            for grp_id in repo["packagegroups"]:
                if repo["packagegroups"][grp_id]["repo_defined"]:
                    del repo["packagegroups"][grp_id]
            for cat_id in repo["packagegroupcategories"]:
                if repo["packagegroupcategories"][cat_id]["repo_defined"]:
                    del repo["packagegroupcategories"][cat_id]
            # Add all groups/categories from repo
            for c in comps.categories:
                ctg = pulp.server.comps_util.yum_category_to_model_category(c)
                ctg["immutable"] = True
                ctg["repo_defined"] = True
                repo['packagegroupcategories'][ctg['id']] = ctg
            for g in comps.groups:
                grp = pulp.server.comps_util.yum_group_to_model_group(g)
                grp["immutable"] = True
                grp["repo_defined"] = True
                repo['packagegroups'][grp['id']] = grp
        except yum.Errors.CompsException:
            log.error("Unable to parse group info for %s" % (compsfile))
            return False
        return True

    def sync_updateinfo_data(self, updateinfo_xml_path, repo):
        """
        @param updateinfo_xml_path: path to updateinfo metadata xml file
        @param repo:    model.Repo object we want to sync
        """
        from pulp.server.api.repo import RepoApi
        repo_api = RepoApi()
        eids = []
        try:
            start = time.time()
            errata = updateinfo.get_errata(updateinfo_xml_path)
            log.debug("Parsed %s, %s UpdateNotices were returned." %
                      (updateinfo_xml_path, len(errata)))
            for e in errata:
                eids.append(e['id'])
                # Replace existing errata if the update date is newer
                found = self.errata_api.erratum(e['id'])
                if found:
                    if e['updated'] <= found['updated']:
                        continue
                    log.debug("Updating errata %s, it's updated date %s is newer than %s." % \
                            (e['id'], e["updated"], found["updated"]))
                    try:
                        repo_api.delete_erratum(repo['id'], e['id'])
                        self.errata_api.delete(e['id'])
                    except ErrataHasReferences:
                        log.info(
                            'errata "%s" has references, not deleted',e['id'])
                    except Exception, ex:
                        log.exception(ex)
                pkglist = e['pkglist']
                try:
                    self.errata_api.create(id=e['id'], title=e['title'],
                            description=e['description'], version=e['version'],
                            release=e['release'], type=e['type'],
                            status=e['status'], updated=e['updated'],
                            issued=e['issued'], pushcount=e['pushcount'],
                            from_str=e['from_str'], reboot_suggested=e['reboot_suggested'],
                            references=e['references'], pkglist=pkglist,
                            repo_defined=True, immutable=True)
                except DuplicateKeyError:
                    log.info('errata [%s] already exists' % e['id'])
            end = time.time()
            log.debug("%s new/updated errata imported in %s seconds" % (len(eids), (end - start)))
        except yum.Errors.YumBaseError, e:
            log.error("Unable to parse updateinfo file %s for %s" % (updateinfo_xml_path, repo["id"]))
            return []
        return eids


class YumSynchronizer(BaseSynchronizer):

    def __init__(self):
        super(YumSynchronizer, self).__init__()
        self.yum_repo_grinder = None
        self.yum_repo_grinder_lock = Lock()

    def sync(self, repo_id, repo_source, skip_dict={}, progress_callback=None,
            max_speed=None, threads=None):
        repo = self.repo_api._get_existing_repo(repo_id)
        cacert = clicert = None
        if repo['feed_ca']:
            cacert = repo['feed_ca'].encode('utf8')
        if repo['feed_cert']:
            clicert = repo['feed_cert'].encode('utf8')
        log.info("cacert = <%s>, cert = <%s>" % (cacert, clicert))
        remove_old = config.config.getboolean('yum', 'remove_old_packages')
        num_old_pkgs_keep = config.config.getint('yum', 'num_old_pkgs_keep')
        # check for proxy settings
        proxy_url = proxy_port = proxy_user = proxy_pass = None
        for proxy_cfg in ['proxy_url', 'proxy_port', 'proxy_user', 'proxy_pass']:
            if (config.config.has_option('yum', proxy_cfg)):
                vars(self)[proxy_cfg] = config.config.get('yum', proxy_cfg)
            else:
                vars(self)[proxy_cfg] = None

        num_threads = threads
        if threads is None and config.config.getint('yum', 'threads'):
            num_threads = config.config.getint('yum', 'threads')
        if num_threads < 1:
            log.error("Invalid number of threads specified [%s].  Will default to 1" % (num_threads))
            num_threads = 1
        limit_in_KB = max_speed
        # limit_in_KB can be 0, that is a valid value representing unlimited bandwidth
        if limit_in_KB is None and config.config.has_option('yum', 'limit_in_KB'):
            limit_in_KB = config.config.getint('yum', 'limit_in_KB')
        if limit_in_KB < 0:
            log.error("Invalid value [%s] for bandwidth limit in KB.  Negative values not allowed." % (limit_in_KB))
            limit_in_KB = 0
        if limit_in_KB:
            log.info("Limiting download speed to %s KB/sec per thread. [%s] threads will be used" % \
                    (limit_in_KB, num_threads))
        if self.stopped:
            raise CancelException()

        try:
            self.yum_repo_grinder = YumRepoGrinder('', repo_source['url'].encode('ascii', 'ignore'),
                                num_threads, cacert=cacert, clicert=clicert,
                                packages_location=pulp.server.util.top_package_location(),
                                remove_old=remove_old, numOldPackages=num_old_pkgs_keep, skip=skip_dict,
                                proxy_url=self.proxy_url, proxy_port=self.proxy_port,
                                proxy_user=self.proxy_user or None, proxy_pass=self.proxy_pass or None,
                                max_speed=limit_in_KB)
            relative_path = repo['relative_path']
            if relative_path:
                store_path = "%s/%s" % (pulp.server.util.top_repos_location(), relative_path)
            else:
                store_path = "%s/%s" % (pulp.server.util.top_repos_location(), repo['id'])
            self.repo_dir = store_path

            verify_options = {}
            verify_options["size"] = config.config.getboolean('yum', "verify_size")
            verify_options["checksum"] = config.config.getboolean('yum', "verify_checksum")
            log.info("Fetching repo to <%s> with verify_options <%s>" % (store_path, verify_options))
            report = self.yum_repo_grinder.fetchYumRepo(store_path,
                                                    callback=progress_callback,
                                                    verify_options=verify_options)
            if self.stopped:
                raise CancelException()
            self.progress = yum_rhn_progress_callback(report.last_progress)
            start = time.time()
            groups_xml_path = None
            repomd_xml = os.path.join(store_path, "repodata/repomd.xml")
            if os.path.isfile(repomd_xml):
                ftypes = pulp.server.util.get_repomd_filetypes(repomd_xml)
                log.debug("repodata has filetypes of %s" % (ftypes))
                if "group" in ftypes:
                    g = pulp.server.util.get_repomd_filetype_path(repomd_xml, "group")
                    groups_xml_path = os.path.join(store_path, g)
            if self.stopped:
                raise CancelException()
            if not repo['preserve_metadata']:
                # re-generate metadata for the repository
                log.info("Running createrepo, this may take a few minutes to complete.")
                if progress_callback is not None:
                    self.progress["step"] = "Running Createrepo"
                    progress_callback(self.progress)
                pulp.server.util.create_repo(store_path, groups=groups_xml_path, checksum_type=repo['checksum_type'])
                end = time.time()
                log.info("Createrepo finished in %s seconds" % (end - start))
        finally:
            self.yum_repo_grinder_lock.acquire()
            try:
                del self.yum_repo_grinder
                self.yum_repo_grinder = None
            finally:
                self.yum_repo_grinder_lock.release()

        log.info("YumSynchronizer reported %s successes, %s downloads, %s errors" \
                    % (report.successes, report.downloads, report.errors))
        return store_path

    def stop(self):
        super(YumSynchronizer, self).stop()
        self.yum_repo_grinder_lock.acquire()
        try:
            if self.yum_repo_grinder:
                log.info("Stop sync is being issued")
                self.yum_repo_grinder.stop(block=False)
        finally:
            self.yum_repo_grinder_lock.release()


class LocalSynchronizer(BaseSynchronizer):
    """
    Sync class to synchronize a directory of rpms from a local filer
    """
    def __init__(self):
        super(LocalSynchronizer, self).__init__()

    def _calculate_bytes(self, dir, pkglist):
        bytes = 0
        for pkg in pkglist:
            bytes += os.stat(os.path.join(dir, pkg))[6]
        return bytes

    def list_rpms(self, src_repo_dir):
        pkglist = pulp.server.util.listdir(src_repo_dir)
        pkglist = filter(lambda x: x.endswith(".rpm"), pkglist)
        log.info("Found %s packages in %s" % (len(pkglist), src_repo_dir))
        return pkglist

    def list_tree_files(self, src_repo_dir):
        src_images_dir = os.path.join(src_repo_dir, "images")
        if not os.path.exists(src_images_dir):
            return []
        return pulp.server.util.listdir(src_images_dir)

    def list_drpms(self, src_repo_dir):
        dpkglist = pulp.server.util.listdir(src_repo_dir)
        dpkglist = filter(lambda x: x.endswith(".drpm"), dpkglist)
        log.info("Found %s delta rpm packages in %s" % (len(dpkglist), src_repo_dir))
        return dpkglist

    def __init_progress_details(self, item_type, item_list, src_repo_dir):
        if not item_list:
            # Only create a details entry if there is data to report progress on
            return
        size_bytes = self._calculate_bytes(src_repo_dir, item_list)
        num_items = len(item_list)
        if not self.progress["details"].has_key(item_type):
            self.progress["details"][item_type] = {}
        self.progress['size_left'] += size_bytes
        self.progress['size_total'] += size_bytes
        self.progress['items_total'] += num_items
        self.progress['items_left'] += num_items
        self.progress['details'][item_type]["items_left"] = num_items
        self.progress['details'][item_type]["total_count"] = num_items
        self.progress['details'][item_type]["num_success"] = 0
        self.progress['details'][item_type]["num_error"] = 0
        self.progress['details'][item_type]["total_size_bytes"] = size_bytes
        self.progress['details'][item_type]["size_left"] = size_bytes

    def init_progress_details(self, src_repo_dir, skip_dict):
        if not self.progress.has_key('size_total'):
            self.progress['size_total'] = 0
        if not self.progress.has_key('items_total'):
            self.progress['items_total'] = 0
        if not self.progress.has_key('size_left'):
            self.progress['size_left'] = 0
        if not self.progress.has_key('items_left'):
            self.progress['items_left'] = 0
        if not self.progress.has_key("details"):
            self.progress["details"] = {}

        if not skip_dict.has_key('packages') or skip_dict['packages'] != 1:
            rpm_list = self.list_rpms(src_repo_dir)
            self.__init_progress_details("rpm", rpm_list, src_repo_dir)
            drpm_list = self.list_drpms(src_repo_dir)
            self.__init_progress_details("drpm", drpm_list, src_repo_dir)
        if not skip_dict.has_key('distribution') or skip_dict['distribution'] != 1:
            tree_files = self.list_tree_files(src_repo_dir)
            self.__init_progress_details("tree_file", tree_files, src_repo_dir)

    def _add_error_details(self, file_name, item_type, error_info):
        # We are adding blank fields to the error entry so it will
        # match the structure returned from yum syncs
        missing_fields = ("checksumtype", "checksum", "downloadurl", "item_type", "savepath", "pkgpath", "size")
        entry = {"fileName":file_name, "item_type":item_type}
        for key in missing_fields:
            entry[key] = ""
        for key in error_info:
            entry[key] = error_info[key]
        self.progress["error_details"].append(entry)
        self.progress['details'][item_type]["num_error"] += 1
        self.progress['num_error'] += 1

    def _process_rpm(self, pkg, dst_repo_dir):
        pkg_info = pulp.server.util.get_rpm_information(pkg)
        pkg_checksum = pulp.server.util.get_file_checksum(hashtype="sha256", filename=pkg)
        pkg_location = pulp.server.util.get_shared_package_path(pkg_info['name'],
                pkg_info['version'], pkg_info['release'], pkg_info['arch'],
                os.path.basename(pkg), pkg_checksum)
        if not pulp.server.util.check_package_exists(pkg_location, pkg_checksum):
            pkg_dirname = os.path.dirname(pkg_location)
            if not os.path.exists(pkg_dirname):
                os.makedirs(pkg_dirname)
            shutil.copy(pkg, pkg_location)

            self.progress['num_download'] += 1
        repo_pkg_path = os.path.join(dst_repo_dir, os.path.basename(pkg))
        if not os.path.islink(repo_pkg_path):
            pulp.server.util.create_rel_symlink(pkg_location, repo_pkg_path)

    def _find_combined_whitelist_packages(self, repo_filters):
        combined_whitelist_packages = []
        for filter_id in repo_filters:
            filter = self.filter_api.filter(filter_id)
            if filter['type'] == "whitelist":
                combined_whitelist_packages.extend(filter['package_list'])
        return combined_whitelist_packages

    def _find_combined_blacklist_packages(self, repo_filters):
        combined_blacklist_packages = []
        for filter_id in repo_filters:
            filter = self.filter_api.filter(filter_id)
            if filter['type'] == "blacklist":
                combined_blacklist_packages.extend(filter['package_list'])
        return combined_blacklist_packages

    def _find_filtered_package_list(self, unfiltered_pkglist, whitelist_packages, blacklist_packages):
        pkglist = []

        if whitelist_packages:
            for pkg in unfiltered_pkglist:
                for whitelist_package in whitelist_packages:
                    w = re.compile(whitelist_package)
                    if w.match(os.path.basename(pkg)):
                        pkglist.append(pkg)
                        exit
        else:
            pkglist = unfiltered_pkglist

        if blacklist_packages:
            for pkg in pkglist:
                for blacklist_package in blacklist_packages:
                    b = re.compile(blacklist_package)
                    if b.match(os.path.basename(pkg)):
                        pkglist.remove(pkg)
                        exit

        return pkglist


    def _sync_rpms(self, dst_repo_dir, src_repo_dir, whitelist_packages, blacklist_packages,
                   progress_callback=None):
        # Compute and import packages
        unfiltered_pkglist = self.list_rpms(src_repo_dir)
        pkglist = self._find_filtered_package_list(unfiltered_pkglist, whitelist_packages, blacklist_packages)

        if progress_callback is not None:
            self.progress['step'] = ProgressReport.DownloadItems
            progress_callback(self.progress)

        for count, pkg in enumerate(pkglist):
            if count % 500 == 0:
                log.info("Working on %s/%s" % (count, len(pkglist)))
            try:
                rpm_name = os.path.basename(pkg)
                log.info("Processing rpm: %s" % rpm_name)
                self._process_rpm(pkg, dst_repo_dir)
                self.progress['details']["rpm"]["num_success"] += 1
                self.progress["num_success"] += 1
                self.progress["item_type"] = BaseFetch.RPM
                self.progress["item_name"] = rpm_name
            except (IOError, OSError):
                log.error("%s" % (traceback.format_exc()))
                error_info = {}
                exctype, value = sys.exc_info()[:2]
                error_info["error_type"] = str(exctype)
                error_info["error"] = str(value)
                error_info["traceback"] = traceback.format_exc().splitlines()
                self._add_error_details(pkg, "rpm", error_info)
            self.progress["step"] = ProgressReport.DownloadItems
            item_size = self._calculate_bytes(src_repo_dir, [pkg])
            self.progress['size_left'] -= item_size
            self.progress['items_left'] -= 1
            self.progress['details']["rpm"]["items_left"] -= 1
            self.progress['details']["rpm"]["size_left"] -= item_size

            if progress_callback is not None:
                log.error("Calling progress_callback<%s>" % (self.progress))
                progress_callback(self.progress)
                self.progress["item_type"] = ""
                self.progress["item_name"] = ""
        log.info("Finished copying %s packages" % (len(pkglist)))
        # Remove rpms which are no longer in source
        # TODO: Consider removing this purge step
        # Also remove from grinder, allow repo.py to handle any purge
        # operations when needed
        existing_pkgs = pulp.server.util.listdir(dst_repo_dir)
        existing_pkgs = filter(lambda x: x.endswith(".rpm"), existing_pkgs)
        existing_pkgs = [os.path.basename(pkg) for pkg in existing_pkgs]
        source_pkgs = [os.path.basename(p) for p in pkglist]
        if progress_callback is not None:
            log.debug("Updating progress to %s" % (ProgressReport.PurgeOrphanedPackages))
            self.progress["step"] = ProgressReport.PurgeOrphanedPackages
            progress_callback(self.progress)
        for epkg in existing_pkgs:
            if epkg not in source_pkgs:
                log.info("Remove %s from repo %s because it is not in repo_source" % (epkg, dst_repo_dir))
                os.remove(os.path.join(dst_repo_dir, epkg))

    def _sync_drpms(self, dst_repo_dir, src_repo_dir, progress_callback=None):
        # Compute and import delta rpms
        dpkglist = self.list_drpms(src_repo_dir)
        if progress_callback is not None:
            self.progress['step'] = ProgressReport.DownloadItems
            progress_callback(self.progress)
        dst_drpms_dir = os.path.join(dst_repo_dir, "drpms")
        if not os.path.exists(dst_drpms_dir):
            os.makedirs(dst_drpms_dir)
        for count, pkg in enumerate(dpkglist):
            skip_copy = False
            log.debug("Processing drpm %s" % pkg)
            if count % 500 == 0:
                log.info("Working on %s/%s" % (count, len(dpkglist)))
            try:
                src_drpm_checksum = pulp.server.util.get_file_checksum(filename=pkg)
                dst_drpm_path = os.path.join(dst_drpms_dir, os.path.basename(pkg))
                if not pulp.server.util.check_package_exists(dst_drpm_path, src_drpm_checksum):
                    shutil.copy(pkg, dst_drpm_path)
                    self.progress['num_download'] += 1
                else:
                    log.info("delta rpm %s already exists with same checksum. skip import" % os.path.basename(pkg))
                    skip_copy = True
                log.debug("Imported delta rpm %s " % dst_drpm_path)
                self.progress['details']["drpm"]["num_success"] += 1
                self.progress["num_success"] += 1
            except (IOError, OSError):
                log.error("%s" % (traceback.format_exc()))
                error_info = {}
                exctype, value = sys.exc_info()[:2]
                error_info["error_type"] = str(exctype)
                error_info["error"] = str(value)
                error_info["traceback"] = traceback.format_exc().splitlines()
                self._add_error_details(pkg, "drpm", error_info)
            self.progress['step'] = ProgressReport.DownloadItems
            item_size = self._calculate_bytes(src_repo_dir, [pkg])
            self.progress['size_left'] -= item_size
            self.progress['items_left'] -= 1
            self.progress['details']["drpm"]["items_left"] -= 1
            self.progress['details']["drpm"]["size_left"] -= item_size
            if progress_callback is not None:
                progress_callback(self.progress)


    def sync(self, repo_id, repo_source, skip_dict={}, progress_callback=None,
            max_speed=None, threads=None):
        repo = self.repo_api._get_existing_repo(repo_id)
        src_repo_dir = urlparse(repo_source['url'])[2].encode('ascii', 'ignore')
        log.info("sync of %s for repo %s" % (src_repo_dir, repo['id']))
        self.init_progress_details(src_repo_dir, skip_dict)

        try:
            dst_repo_dir = "%s/%s" % (pulp.server.util.top_repos_location(), repo['id'])

            # Process repo filters if any
            if repo['filters']:
                log.info("Repo filters : %s" % repo['filters'])
                whitelist_packages = self._find_combined_whitelist_packages(repo['filters'])
                blacklist_packages = self._find_combined_blacklist_packages(repo['filters'])
                log.info("combined whitelist packages = %s" % whitelist_packages)
                log.info("combined blacklist packages = %s" % blacklist_packages)
            else:
                whitelist_packages = []
                blacklist_packages = []

            if not os.path.exists(src_repo_dir):
                raise InvalidPathError("Path %s is invalid" % src_repo_dir)
            if repo['use_symlinks']:
                log.info("create a symlink to src directory %s %s" % (src_repo_dir, dst_repo_dir))
                pulp.server.util.create_rel_symlink(src_repo_dir, dst_repo_dir)
                if progress_callback is not None:
                    self.progress['size_total'] = 0
                    self.progress['size_left'] = 0
                    self.progress['items_total'] = 0
                    self.progress['items_left'] = 0
                    self.progress['details'] = {}
                    self.progress['num_download'] = 0
                    self.progress['step'] = ProgressReport.DownloadItems
                    progress_callback(self.progress)
            else:
                if not os.path.exists(dst_repo_dir):
                    os.makedirs(dst_repo_dir)
                if not skip_dict.has_key('packages') or skip_dict['packages'] != 1:
                    log.debug("Starting _sync_rpms(%s, %s)" % (dst_repo_dir, src_repo_dir))
                    self._sync_rpms(dst_repo_dir, src_repo_dir, whitelist_packages, blacklist_packages,
                                    progress_callback)
                    log.debug("Completed _sync_rpms(%s,%s)" % (dst_repo_dir, src_repo_dir))
                    log.debug("Starting _sync_drpms(%s, %s)" % (dst_repo_dir, src_repo_dir))
                    self._sync_drpms(dst_repo_dir, src_repo_dir, progress_callback)
                    log.debug("Completed _sync_drpms(%s,%s)" % (dst_repo_dir, src_repo_dir))
                else:
                    log.info("Skipping package imports from sync process")

                # compute and import repo image files
                imlist = self.list_tree_files(src_repo_dir)
                if not imlist:
                    log.info("No image files to import")
                else:
                    if not skip_dict.has_key('distribution') or skip_dict['distribution'] != 1:
                        dst_images_dir = os.path.join(dst_repo_dir, "images")
                        for imfile in imlist:
                            try:
                                skip_copy = False
                                rel_file_path = imfile.split('/images/')[-1]
                                dst_file_path = os.path.join(dst_images_dir, rel_file_path)
                                if os.path.exists(dst_file_path):
                                    dst_file_checksum = pulp.server.util.get_file_checksum(filename=dst_file_path)
                                    src_file_checksum = pulp.server.util.get_file_checksum(filename=imfile)
                                    if src_file_checksum == dst_file_checksum:
                                        log.info("file %s already exists with same checksum. skip import" % rel_file_path)
                                        skip_copy = True
                                if not skip_copy:
                                    file_dir = os.path.dirname(dst_file_path)
                                    if not os.path.exists(file_dir):
                                        os.makedirs(file_dir)
                                    shutil.copy(imfile, dst_file_path)
                                    self.progress['num_download'] += 1
                                self.progress['details']["tree_file"]["num_success"] += 1
                                self.progress["num_success"] += 1
                            except (IOError, OSError):
                                log.error("%s" % (traceback.format_exc()))
                                error_info = {}
                                exctype, value = sys.exc_info()[:2]
                                error_info["error_type"] = str(exctype)
                                error_info["error"] = str(value)
                                error_info["traceback"] = traceback.format_exc().splitlines()
                                self._add_error_details(imfile, "tree_file", error_info)
                            log.debug("Imported file %s " % dst_file_path)
                            self.progress['step'] = ProgressReport.DownloadItems
                            item_size = self._calculate_bytes(src_repo_dir, [imfile])
                            self.progress['size_left'] -= item_size
                            self.progress['items_left'] -= 1
                            self.progress['details']["tree_file"]["items_left"] -= 1
                            self.progress['details']["tree_file"]["size_left"] -= item_size
                            if progress_callback is not None:
                                progress_callback(self.progress)
                    else:
                        log.info("Skipping distribution imports from sync process")
                groups_xml_path = None
                updateinfo_path = None
                prestodelta_path = None
                src_repomd_xml = os.path.join(src_repo_dir, "repodata/repomd.xml")
                if os.path.isfile(src_repomd_xml):
                    ftypes = pulp.server.util.get_repomd_filetypes(src_repomd_xml)
                    log.debug("repodata has filetypes of %s" % (ftypes))
                    if "group" in ftypes:
                        g = pulp.server.util.get_repomd_filetype_path(src_repomd_xml, "group")
                        src_groups = os.path.join(src_repo_dir, g)
                        if os.path.isfile(src_groups):
                            shutil.copy(src_groups,
                                os.path.join(dst_repo_dir, os.path.basename(src_groups)))
                            log.debug("Copied groups over to %s" % (dst_repo_dir))
                        groups_xml_path = os.path.join(dst_repo_dir,
                            os.path.basename(src_groups))
                    if "updateinfo" in ftypes and (not skip_dict.has_key('errata') or skip_dict['errata'] != 1):
                        f = pulp.server.util.get_repomd_filetype_path(src_repomd_xml, "updateinfo")
                        src_updateinfo_path = os.path.join(src_repo_dir, f)
                        if os.path.isfile(src_updateinfo_path):
                            # Copy the updateinfo metadata to 'updateinfo.xml'
                            # We want to ensure modifyrepo is run with updateinfo
                            # called 'updateinfo.xml', this result in correct
                            # metadata type
                            #
                            # updateinfo reported from repomd.xml may be gzipped,
                            # if it is uncompress and copy to updateinfo.xml
                            # along side of packages in repo
                            #
                            f = src_updateinfo_path.endswith('.gz') and gzip.open(src_updateinfo_path) \
                                    or open(src_updateinfo_path, 'rt')
                            shutil.copyfileobj(f, open(
                                os.path.join(dst_repo_dir, "updateinfo.xml"), "wt"))
                            log.debug("Copied %s to %s" % (src_updateinfo_path, dst_repo_dir))
                            updateinfo_path = os.path.join(dst_repo_dir, "updateinfo.xml")
                    else:
                        log.info("Skipping errata imports from sync process")
                    if "prestodelta" in ftypes and (not skip_dict.has_key('packages') or skip_dict['packages'] != 1):
                        drpm_meta = pulp.server.util.get_repomd_filetype_path(src_repomd_xml, "prestodelta")
                        src_presto_path = os.path.join(src_repo_dir, drpm_meta)
                        if os.path.isfile(src_presto_path):
                            f = src_presto_path.endswith('.gz') and gzip.open(src_presto_path) \
                                    or open(src_presto_path, 'rt')
                            shutil.copyfileobj(f, open(
                                os.path.join(dst_repo_dir, "prestodelta.xml"), "wt"))
                            log.debug("Copied %s to %s" % (src_presto_path, dst_repo_dir))
                            prestodelta_path = os.path.join(dst_repo_dir, "prestodelta.xml")
                if not repo['preserve_metadata']:
                    if progress_callback is not None:
                        self.progress["step"] = "Running Createrepo"
                        progress_callback(self.progress)
                    log.info("Running createrepo, this may take a few minutes to complete.")
                    start = time.time()
                    pulp.server.util.create_repo(dst_repo_dir, groups=groups_xml_path, checksum_type=repo['checksum_type'])
                    end = time.time()
                    log.info("Createrepo finished in %s seconds" % (end - start))
                    if prestodelta_path:
                        log.debug("Modifying repo for prestodelta")
                        if progress_callback is not None:
                            self.progress["step"] = "Running Modifyrepo for prestodelta metadata"
                            progress_callback(self.progress)
                        pulp.server.util.modify_repo(os.path.join(dst_repo_dir, "repodata"),
                                prestodelta_path)
                    if updateinfo_path:
                        log.debug("Modifying repo for updateinfo")
                        if progress_callback is not None:
                            self.progress["step"] = "Running Modifyrepo for updateinfo metadata"
                            progress_callback(self.progress)
                        pulp.server.util.modify_repo(os.path.join(dst_repo_dir, "repodata"),
                                updateinfo_path)
        except InvalidPathError:
            log.error("Sync aborted due to invalid source path %s" % (src_repo_dir))
            raise
        except IOError:
            log.error("Unable to create repo directory %s" % dst_repo_dir)
            raise
        return dst_repo_dir


