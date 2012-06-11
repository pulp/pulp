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
import ConfigParser

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
import datetime
from bson import SON

import yum
from grinder.BaseFetch import BaseFetch
from grinder.FileFetch import FileGrinder
from grinder.GrinderUtils import parseManifest
from grinder.GrinderCallback import ProgressReport
from grinder.RepoFetch import YumRepoGrinder
from pulp.common import dateutils
from pulp.server.api.file import FileApi

import pulp.server.comps_util
import pulp.server.util
from pulp.common.util import encode_unicode, decode_unicode
from pulp.server import config, constants, updateinfo
from pulp.server.api.distribution import DistributionApi
from pulp.server.api.errata import ErrataApi, ErrataHasReferences
from pulp.server.api.filter import FilterApi
from pulp.server.api.package import PackageApi
from pulp.server.api.repo import RepoApi
from pulp.server.db.model import Delta, DuplicateKeyError
from pulp.server.tasking.exception import CancelException
from pulp.server.db import model


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
        self.file_api = FileApi()
        self.progress = {
            'status': 'running',
            'item_name': None,
            'item_type': None,
            'items_total': 0,
            'items_left': 0,
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
        self.repo_dir = None
        self.is_clone = False
        self.parent = None
        self.do_update_metadata = False

    def stop(self):
        self.stopped = True

    def set_callback(self, callback):
        self.callback = callback

    def set_clone(self, id):
        # parent repo id to be cloned
        self.is_clone = True
        self.parent = id

    def progress_callback(self, **kwargs):
        """
        Callback called to update the pulp task's progress
        """
        if not self.callback:
            return
        for key in kwargs:
            self.progress[key] = kwargs[key]
        self.callback(self.progress)

    def sync(self, repo_id, repo_source, skip_dict={}, progress_callback=None,
            max_speed=None, threads=None):
        """
        Top level sync method to invoke sync based on type
        @type repo_id: str
        @param repo_id: repository to sync
        @type repo_source: RepoSource instance
        @param repo_source: source type on the repository rg: remote, local
        @type skip_dict: dictionary
        @param skip_dict: content types to skip during sync process eg: {packages : 1, distribution : 0}
        @type progress_callback: progress callback instance
        @param progress_callback: callback method to track sync progress
        @type max_speed: int
        @param max_speed: maximum bandwidth to use
        @type threads: int
        @param threads: Number of threads to run the sync process in
        @raise RuntimeError: if the sync raises exception
        """
        repo = self.repo_api._get_existing_repo(repo_id)
        source_type = getattr(self, repo['source']['type']) # 'remote' or 'local'
        return source_type(repo_id, repo_source, skip_dict=skip_dict, progress_callback=progress_callback,
                        max_speed=max_speed, threads=threads)

    def remote(self, repo_id, repo_source, skip_dict={}, progress_callback=None,
            max_speed=None, threads=None):
        """
        remote sync method implementation
        @type repo_id: str
        @param repo_id: repository to sync
        @type repo_source: RepoSource instance
        @param repo_source: source type on the repository rg: remote, local
        @type skip_dict: dictionary
        @param skip_dict: content types to skip during sync process eg: {packages : 1, distribution : 0}
        @type progress_callback: progress callback instance
        @param progress_callback: callback method to track sync progress
        @type max_speed: int
        @param max_speed: maximum bandwidth to use
        @type threads: int
        @param threads: Number of threads to run the sync process in
        @raise RuntimeError: if the sync raises exception
        """
        raise NotImplementedError('base synchronizer class method called')

    def local(self, repo_id, repo_source, skip_dict={}, progress_callback=None,
            max_speed=None, threads=None):
        """
        local sync method implementation
        @type repo_id: str
        @param repo_id: repository to sync
        @type repo_source: RepoSource instance
        @param repo_source: source type on the repository rg: remote, local
        @type skip_dict: dictionary
        @param skip_dict: content types to skip during sync process eg: {packages : 1, distribution : 0}
        @type progress_callback: progress callback instance
        @param progress_callback: callback method to track sync progress
        @type max_speed: int
        @param max_speed: maximum bandwidth to use
        @type threads: int
        @param threads: Number of threads to run the sync process in
        @raise RuntimeError: if the sync raises exception
        """
        raise NotImplementedError('base synchronizer class method called')

    def process_packages_from_source(self, dir, repo_id, skip_dict=None, progress_callback=None):
        if self.is_clone:
            # clone or re-clone operation
            added_packages = self.clone_packages_from_source(repo_id, skip_dict)
            if self.do_update_metadata:
                # updating Metadata since the repo state has been changed by filters
                self.update_metadata(dir, repo_id, progress_callback)
        else:
            # Usual sync, Process Packages
            added_packages = self.add_packages_from_dir(dir, repo_id, skip_dict)
            # check if the repo has a parent
            if self.do_update_metadata or not self.repo_api.has_parent(repo_id):
                # updating Metadata
                self.update_metadata(dir, repo_id, progress_callback)
            else:
                log.info("The repo [%s] has a parent; skipping metadata update to reuse the source metadata" % repo_id)
        return added_packages

    # Point of this method is to return what packages exist in the repo after being syncd
    def add_packages_from_dir(self, dir, repo_id, skip=None):
        repo = self.repo_api._get_existing_repo(repo_id)
        added_packages = {}
        if "yum" not in repo['content_types']:
            return added_packages
        if not skip:
            skip = {}
        if not skip.has_key('packages') or skip['packages'] != 1:
            startTime = time.time()
            log.debug("Begin to add packages from %s into %s" % (encode_unicode(dir), encode_unicode(repo['id'])))
            unfiltered_pkglist = pulp.server.util.get_repo_packages(dir)
            # Process repo filters if any
            if repo['filters']:
                log.info("Repo filters : %s" % repo['filters'])
                whitelist_packages = self.repo_api.find_combined_whitelist_packages(repo['filters'])
                blacklist_packages = self.repo_api.find_combined_blacklist_packages(repo['filters'])
                log.info("combined whitelist packages = %s" % whitelist_packages)
                log.info("combined blacklist packages = %s" % blacklist_packages)
            else:
                whitelist_packages = []
                blacklist_packages = []

            package_list = self._find_filtered_package_list(unfiltered_pkglist, whitelist_packages, blacklist_packages, dst_repo_dir=self.repo_dir)
            log.debug("Processing %s potential packages" % (len(package_list)))
            for package in package_list:
                pkg_path = "%s/%s/%s/%s/%s/%s/%s" % (pulp.server.util.top_package_location(), package.name, package.version, \
                                                          package.release, package.arch, package.checksum, os.path.basename(package.relativepath))
                if not os.path.exists(pkg_path):
                    # skip import; package is missing from the filesystem
                    continue
                package = self.import_package(package, repo, repo_defined=True)
                if (package is not None):
                    added_packages[package["id"]] = package
            endTime = time.time()
            log.debug("Repo: %s read [%s] packages took %s seconds" %
                    (repo['id'], len(added_packages), endTime - startTime))
        else:
            log.info("Skipping package imports from sync process")
        if self.stopped:
            raise CancelException()
        self.repo_api.collection.save(repo, safe=True)
        return added_packages

    def lookup_package(self, package):
        """
         Look up package in pulp db and return the package object
        """
        file_name = os.path.basename(package.relativepath)
        hashtype = package.checksum_type
        checksum = package.checksum
        found = self.package_api.packages(
                name=package.name,
                epoch=package.epoch,
                version=package.version,
                release=package.release,
                arch=package.arch,
                filename=file_name,
                checksum_type=hashtype,
                checksum=checksum)
        newpkg = None
        if found:
            newpkg = found[0]
        return newpkg

    def clone_packages_from_source(self, repo_id, skip=None):
        if not self.is_clone:
            # parent clone not set, noting to import
            return {}
        parent_repo = self.repo_api.repository(self.parent)
        repo = self.repo_api.repository(repo_id)
        added_packages = {}
        if "yum" not in repo['content_types']:
            return added_packages
        if not skip:
            skip = {}
        if not skip.has_key('packages') or skip['packages'] != 1:
            parent_pkglist = parent_repo['packages']
            if not parent_pkglist:
                return added_packages
            unfiltered_pkglist = []
            # Convert package ids to package objects
            pkg_coll = model.Package.get_collection()
            unfiltered_pkglist = pkg_coll.find({"id":{"$in":parent_pkglist}})

            # Process repo filters if any
            whitelist_packages = []
            blacklist_packages = []
            if repo['filters']:
                log.info("Repo filters : %s" % repo['filters'])
                whitelist_packages = self.repo_api.find_combined_whitelist_packages(repo['filters'])
                blacklist_packages = self.repo_api.find_combined_blacklist_packages(repo['filters'])
                log.info("combined whitelist packages = %s" % whitelist_packages)
                log.info("combined blacklist packages = %s" % blacklist_packages)
            # apply any filters
            package_list = self._find_filtered_package_list(unfiltered_pkglist, whitelist_packages, blacklist_packages, is_clone=True)

            for package in package_list:
                pkg_path = "%s/%s/%s/%s/%s/%s/%s" % (pulp.server.util.top_package_location(), package['name'], package['version'], \
                                                          package['release'], package['arch'], package['checksum'].values()[0], package['filename'])
                if not os.path.exists(pkg_path):
                    # skip import; package is missing from the filesystem
                    continue
                if (package is not None):
                    added_packages[package["id"]] = package
                    if repo['id'] not in package['repoids']:
                        package['repoids'].append(repo['id'])
                        pkg_coll.save(package, safe=True)
        else:
            log.info("Skipping package imports from sync process")
        if self.stopped:
            raise CancelException()
        self.repo_api.collection.save(repo, safe=True)
        return added_packages

    def add_distribution_from_dir(self, dir, repo_id, skip=None):
        repo = self.repo_api.repository(repo_id)
        if not skip.has_key('distribution') or skip['distribution'] != 1:
            # process kickstart files/images part of the repo
            if self.stopped:
                raise CancelException()
            self._process_repo_images(dir, repo)
        else:
            log.info("skipping distribution imports from sync process")
        if self.stopped:
            raise CancelException()
        self.repo_api.collection.save(repo, safe=True)

    def add_files_from_dir(self, dir, repo_id, skip=None):
        repo = self.repo_api.repository(repo_id)
        if self.stopped:
            raise CancelException()
        added_files = self._process_files(dir, repo)
        if self.stopped:
            raise CancelException()
        self.repo_api.collection.save(repo, safe=True)
        return added_files

    def import_metadata(self, dir, repo_id, skip=None):
        added_errataids = []
        repo = self.repo_api.repository(repo_id)
        try:
            repomd_xml_path = os.path.join(dir.encode("ascii", "ignore"), 'repodata/repomd.xml')
        except UnicodeDecodeError:
            dir = decode_unicode(dir)
            repomd_xml_path = os.path.join(dir, 'repodata/repomd.xml')
        if os.path.isfile(encode_unicode(repomd_xml_path)):
            repo["repomd_xml_path"] = repomd_xml_path
            ftypes = pulp.server.util.get_repomd_filetypes(encode_unicode(repomd_xml_path))
            log.debug("repodata has filetypes of %s" % (ftypes))
            if "group" in ftypes:
                group_xml_path = pulp.server.util.get_repomd_filetype_path(repomd_xml_path.encode('utf-8'), "group")
                if type(dir) is unicode:
                    group_xml_path = os.path.join(dir, group_xml_path)
                else:
                    group_xml_path = os.path.join(dir.encode("ascii", "ignore"), group_xml_path)
                group_xml_path = encode_unicode(group_xml_path)
                if os.path.isfile(group_xml_path):
                    groupfile = open(group_xml_path, "r")
                    repo['group_xml_path'] = group_xml_path
                    log.info("Loading comps group info from: %s" % (group_xml_path))
                    self.sync_groups_data(groupfile, repo)
                else:
                    log.info("Group info not found at file: %s" % (group_xml_path))
            if "group_gz" in ftypes:
                group_gz_xml_path = pulp.server.util.get_repomd_filetype_path(
                        encode_unicode(repomd_xml_path), "group_gz")
                if type(dir) is unicode:
                    group_gz_xml_path = os.path.join(dir, group_gz_xml_path)
                else:
                    group_gz_xml_path = os.path.join(dir.encode("ascii", "ignore"),
                                                     group_gz_xml_path)
                repo['group_gz_xml_path'] = group_gz_xml_path
            if "updateinfo" in ftypes and (not skip.has_key('errata') or skip['errata'] != 1):
                updateinfo_xml_path = pulp.server.util.get_repomd_filetype_path(
                        encode_unicode(repomd_xml_path), "updateinfo")
                if type(dir) is unicode:
                    updateinfo_xml_path = os.path.join(dir, updateinfo_xml_path)
                else:
                    updateinfo_xml_path = os.path.join(dir.encode("ascii", "ignore"),
                                                       updateinfo_xml_path)
                log.info("updateinfo is found in repomd.xml, it's path is %s" % \
                        (updateinfo_xml_path))
                added_errataids = self.sync_updateinfo_data(updateinfo_xml_path, repo)
                log.debug("Loaded updateinfo from %s for %s" % \
                        (updateinfo_xml_path, repo["id"]))
            else:
                log.info("Skipping errata imports from sync process")
        if self.stopped:
            raise CancelException()
        self.repo_api.collection.save(repo, safe=True)
        return added_errataids

    def _process_files(self, repodir, repo):
        log.debug("Processing any files synced as part of the repo")
        file_metadata = os.path.join(repodir, "PULP_MANIFEST")
        if not os.path.exists(file_metadata):
            log.info("No metadata for 'File Sync' present; no files to import to repo..")
            return
        # Handle files that are part of repo syncs
        files = parseManifest(file_metadata) or {}
        added_files = []
        for fileinfo in files:
            checksum_type, checksum = ("sha256", fileinfo['checksum'])
            fileobj = self.file_api.create(os.path.basename(fileinfo['filename']),
                                           checksum=checksum, checksum_type=checksum_type, size=int(fileinfo['size']))
            if fileobj['id'] not in repo['files']:
                repo['files'].append(fileobj['id'])
                added_files.append(fileobj['id'])
                log.info("Created a fileID %s" % fileobj['id'])
        self.repo_api.collection.save(repo, safe=True)
        return added_files

    def _process_repo_images(self, repodir, repo):
        log.debug("Processing any images synced as part of the repo")
        images_dir = os.path.join(repodir, "images")
        if not os.path.exists(images_dir):
            log.info("No image files to import to repo..")
            return
        # compute and import repo image files
        treecfg = None
        for tree_info_name in ['treeinfo', '.treeinfo']:
            treecfg = os.path.join(repodir, tree_info_name)
            if os.path.exists(treecfg):
                break
            else:
                treecfg = None
        if not treecfg:
            log.info("No treeinfo file found; assume no distributions to import")
            return
        treeinfo = parse_treeinfo(treecfg)
        # Handle distributions that are part of repo syncs
        id = description = "ks-%s-%s-%s-%s" % (treeinfo['family'], treeinfo['variant'],
                                               treeinfo['version'], treeinfo['arch'] or "noarch")
                                               #"ks-" + repo['id'] + "-" + repo['arch']
        distro_path = "%s/%s" % (pulp.server.util.top_distribution_location(), id)
        files = pulp.server.util.listdir(distro_path) or []
        timestamp = None
        if treeinfo['timestamp']:
            timestamp = datetime.datetime.fromtimestamp(float(treeinfo['timestamp']))
        distro = self.distro_api.create(id, description, distro_path, \
                family=treeinfo['family'], variant=treeinfo['variant'], \
                version=treeinfo['version'], timestamp=timestamp, files=files,\
                arch=treeinfo['arch'], repoids=[repo['id']])
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

    def __import_package_with_retry(self, package, repo, repo_defined=False, num_retries=5):
        file_name = os.path.basename(package.relativepath)
        hashtype = package.checksum_type
        checksum = package.checksum
        repoids = []
        if repo is not None:
            repoids = [repo['id']]
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
                repo_defined=repo_defined, repoids=repoids)
        except DuplicateKeyError, e:
            found = self.lookup_package(package)
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
            newpkg = found
        return newpkg

    def import_package(self, package, repo=None, repo_defined=False):
        """
        @param package - package to add to repo
        @param repo_id - repo_id to hold package
        @param repo_defined -  flag to mark if this package is part of the
                        repo source definition, or if it's
                        something manually added later
        """
        try:
            file_name = os.path.basename(package.relativepath)
            newpkg = self.__import_package_with_retry(package, repo, repo_defined)
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
                      'size' , 'group', 'license', 'vendor', 'repoids']
            # set the download URL
            if repo:
                filter.append('download_url')
                newpkg["download_url"] = \
                    constants.SERVER_SCHEME \
                    + config.config.get('server', 'server_name') \
                    + "/" \
                    + config.config.get('server', 'relative_url') \
                    + "/" \
                    + repo['relative_path'] \
                    + "/" \
                    + file_name
                if repo['id'] not in newpkg["repoids"]:
                    newpkg["repoids"].append(repo['id'])
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
                if self.stopped:
                    raise CancelException()
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
                            references=e['references'], pkglist=pkglist, severity=e['severity'],
                            rights=e['rights'], summary=e['summary'], solution=e['solution'],
                            repo_defined=True, immutable=True)
                except DuplicateKeyError:
                    log.info('errata [%s] already exists' % e['id'])
            end = time.time()
            log.debug("%s new/updated errata imported in %s seconds" % (len(eids), (end - start)))
        except yum.Errors.YumBaseError, e:
            log.error("Unable to parse updateinfo file %s for %s" % (updateinfo_xml_path, repo["id"]))
            return []
        return eids

    def _init_progress_details(self, item_type, item_list, src_repo_dir):
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

    def _calculate_bytes(self, dir, pkglist):
        bytes = 0
        for pkg in pkglist:
            pkg_path = os.path.join(dir, pkg)
            if os.path.exists(pkg_path):
                bytes += os.stat(pkg_path)[6]
        return bytes

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
    
    def _create_clone(self, filename, src_repo_dir, dst_repo_dir):
        """
         Get real path of the file or packages from source repo and symlink to target
        """
        log.debug("clone file %s from source dir %s to target dir %s" % (filename, src_repo_dir, dst_repo_dir))
        src_file_path = "%s/%s" % (src_repo_dir, filename)
        # get the real path of this symlinked repo file
        real_src_file_path = os.path.realpath(src_file_path)
        # make sure the real path isnt missing and create a symlink
        if os.path.exists(real_src_file_path):
            repo_file_path = "%s/%s" % (dst_repo_dir, filename) #os.path.basename(pkg))
            if not os.path.islink(repo_file_path):
                pulp.server.util.create_rel_symlink(real_src_file_path, repo_file_path)
        #    self.progress['num_download'] += 1

class YumSynchronizer(BaseSynchronizer):
    """
     Yum synchronizer class to sync rpm, drpms, errata, distributions from remote or local yum feeds
    """
    def __init__(self):
        super(YumSynchronizer, self).__init__()
        self.yum_repo_grinder = None
        self.yum_repo_grinder_lock = Lock()

    def __getstate__(self):
	state = self.__dict__.copy()
	state.pop('yum_repo_grinder_lock', None)
	return state

    def remote(self, repo_id, repo_source, skip_dict={}, progress_callback=None,
            max_speed=None, threads=None):
        repo = self.repo_api._get_existing_repo(repo_id)
        cacert = clicert = None
        if repo['feed_ca']:
            cacert = repo['feed_ca'].encode('utf8')
        if repo['feed_cert']:
            clicert = repo['feed_cert'].encode('utf8')
        log.info("cacert = <%s>, cert = <%s>" % (cacert, clicert))
        remove_old = config.config.getboolean('yum', 'remove_old_versions')
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
                                max_speed=limit_in_KB, distro_location=pulp.server.util.top_distribution_location(),
                                tmp_path = pulp.server.util.tmp_cache_location())
            relative_path = encode_unicode(repo['relative_path'])
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
            log.info("YumSynchronizer reported %s successes, %s downloads, %s errors" \
                    % (report.successes, report.downloads, report.errors))
        finally:
            self.yum_repo_grinder_lock.acquire()
            try:
                del self.yum_repo_grinder
                self.yum_repo_grinder = None
            finally:
                self.yum_repo_grinder_lock.release()
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
        if self.repo_dir:
            if pulp.server.util.cancel_createrepo(self.repo_dir):
                log.info("createrepon on %s has been stopped" % (self.repo_dir))
        log.info("Synchronizer stop has completed")

    def update_metadata(self, repo_dir, repo_id, progress_callback=None):
        repo = self.repo_api._get_existing_repo(repo_id)
        # compute the repo checksum type before processing packages and metadata
        self.set_repo_checksum_type(repo)
        if repo['preserve_metadata']:
            log.info("preserve metadata flag is set; skipping metadata update")
            # no-op
            return
        groups_xml_path = None
        repomd_xml = os.path.join(repo_dir, "repodata/repomd.xml")
        if os.path.isfile(repomd_xml):
            ftypes = pulp.server.util.get_repomd_filetypes(repomd_xml)
            log.debug("repodata has filetypes of %s" % (ftypes))
            print "repodata has filetypes of %s" % (ftypes)
            if "group" in ftypes:
                g = pulp.server.util.get_repomd_filetype_path(repomd_xml, "group")
                groups_xml_path = os.path.join(repo_dir, g)
        if self.stopped:
            raise CancelException()
        if progress_callback is not None:
            self.progress["step"] = "Running Createrepo"
            progress_callback(self.progress)
        log.info("Running createrepo, this may take a few minutes to complete.")
        start = time.time()
        pulp.server.util.create_repo(repo_dir, groups=groups_xml_path, checksum_type=repo['checksum_type'])
        end = time.time()
        log.info("Createrepo finished in %s seconds" % (end - start))

    def set_repo_checksum_type(self, repo):
        # At this point we have either downloaded the source metadata from a remote or local feed
        # lets lookup the checksum type for primary xml in repomd.xml and use that for createrepo
        log.debug('Determining checksum type for repo id %s' % (repo["id"]))
        repo_metadata = "%s/%s/%s" % (pulp.server.util.top_repos_location(), repo['relative_path'], "repodata/repomd.xml")
        repo_metadata = encode_unicode(repo_metadata)
        if os.path.exists(repo_metadata):
            repo['checksum_type'] = pulp.server.util.get_repomd_filetype_dump(repo_metadata)['primary']['checksum'][0]
        elif not repo['checksum_type']:
            repo['checksum_type'] = "sha256"
            # else: just reuse whats in the db
        log.info('checksum type for repo id %s is %s' % (repo['id'], repo['checksum_type']) )
        self.repo_api.collection.save(repo, safe=True)
        
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
            self._init_progress_details("rpm", rpm_list, src_repo_dir)
            drpm_list = self.list_drpms(src_repo_dir)
            self._init_progress_details("drpm", drpm_list, src_repo_dir)
        if not skip_dict.has_key('distribution') or skip_dict['distribution'] != 1:
            tree_files = self.list_tree_files(src_repo_dir)
            self._init_progress_details("tree_file", tree_files, src_repo_dir)

    def _process_rpm(self, pkg, src_repo_dir, dst_repo_dir):
        dst_pkg_path = "%s/%s/%s/%s/%s/%s/%s" % (pulp.server.util.top_package_location(), pkg.name, pkg.version, \
                                                  pkg.release, pkg.arch, pkg.checksum, os.path.basename(pkg.relativepath))
        if not pulp.server.util.check_package_exists(dst_pkg_path, pkg.checksum, hashtype=pkg.checksum_type):
            pkg_dirname = os.path.dirname(dst_pkg_path)
            if not os.path.exists(pkg_dirname):
                os.makedirs(pkg_dirname)
            src_pkg_path = "%s/%s" % (src_repo_dir, pkg.relativepath)
 
            log.debug(" source path %s ; dst path %s" % (src_pkg_path, dst_pkg_path))
            shutil.copy(src_pkg_path, dst_pkg_path)
            self.progress['num_download'] += 1
        repo_pkg_path = os.path.join(dst_repo_dir, pkg.relativepath)
        if not os.path.islink(repo_pkg_path):
            pulp.server.util.create_rel_symlink(dst_pkg_path, repo_pkg_path)

    def _find_filtered_package_list(self, unfiltered_pkglist, whitelist_packages, blacklist_packages, dst_repo_dir=None, is_clone=False):
        pkglist = []
        if not unfiltered_pkglist:
            return pkglist

        if whitelist_packages:
            for pkg in unfiltered_pkglist:
                for whitelist_package in whitelist_packages:
                    w = re.compile(whitelist_package)
                    pkg_name = self.__get_package_name_by_instance(pkg)
                    if w.match(os.path.basename(pkg_name)):
                        pkglist.append(pkg)
                        break
        else:
            pkglist = list(unfiltered_pkglist)

        if blacklist_packages:
            to_remove = []
            for pkg in pkglist:
                for blacklist_package in blacklist_packages:
                    b = re.compile(blacklist_package)
                    pkg_name = self.__get_package_name_by_instance(pkg)
                    if b.match(os.path.basename(pkg_name)):
                        to_remove.append(pkg)
                        break
            for pkg in to_remove:
                pkglist.remove(pkg)

        # Make sure we don't filter packages that already exist in the repository
        if not is_clone:
            assert(dst_repo_dir is not None)
            dst_repo_dir = encode_unicode(dst_repo_dir)
            for pkg in unfiltered_pkglist:
                dst_pkg_path = "%s/%s/%s/%s/%s/%s/%s" % (pulp.server.util.top_package_location(), pkg.name, pkg.
                                                         version, pkg.release, pkg.arch, pkg.checksum, os.path.basename(pkg.relativepath))
                if pulp.server.util.check_package_exists(dst_pkg_path, pkg.checksum, hashtype=pkg.checksum_type):
                    repo_pkg_path = os.path.join(dst_repo_dir, os.path.basename(pkg.relativepath))
                    if os.path.islink(repo_pkg_path) and pkg not in pkglist:
                        pkglist.append(pkg)

        if len(list(unfiltered_pkglist)) and len(list(unfiltered_pkglist)) != len(pkglist):
            # filters modified the repo state, trigger metadata update
            self.do_update_metadata = True
        return pkglist

    def __get_package_name_by_instance(self, pkg):
        if isinstance(pkg, pulp.server.util.Package):
            pkg_name = pkg.relativepath
        elif isinstance(pkg, SON):
            pkg_name = pkg['filename']
        else:
            pkg_name = pkg
        return pkg_name

    def _sync_rpms(self, dst_repo_dir, src_repo_dir, whitelist_packages, blacklist_packages,
                   progress_callback=None):
        # Compute and import packages
        unfiltered_pkglist = pulp.server.util.get_repo_packages(src_repo_dir)
        pkglist = self._find_filtered_package_list(unfiltered_pkglist, whitelist_packages, blacklist_packages, dst_repo_dir)

        if progress_callback is not None:
            self.progress['step'] = ProgressReport.DownloadItems
            progress_callback(self.progress)
        log.debug("Processing %s potential packages" % (len(pkglist)))
        for count, pkg in enumerate(pkglist):
            if self.stopped:
                raise CancelException()
            if count % 500 == 0:
                log.info("Working on %s/%s" % (count, len(pkglist)))
            try:
                rpm_name = os.path.basename(pkg.relativepath)
                log.debug("Processing rpm: %s" % rpm_name)
                self._process_rpm(pkg, src_repo_dir, dst_repo_dir)
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
            item_size = self._calculate_bytes(src_repo_dir, [pkg.relativepath])
            self.progress['size_left'] -= item_size
            self.progress['items_left'] -= 1
            self.progress['details']["rpm"]["items_left"] -= 1
            self.progress['details']["rpm"]["size_left"] -= item_size

            if progress_callback is not None:
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
        source_pkgs = [os.path.basename(p.relativepath) for p in unfiltered_pkglist]

        if progress_callback is not None:
            log.debug("Updating progress to %s" % (ProgressReport.PurgeOrphanedPackages))
            self.progress["step"] = ProgressReport.PurgeOrphanedPackages
            progress_callback(self.progress)
        for epkg in existing_pkgs:
            if epkg not in source_pkgs:
                log.info("Remove %s from repo %s because it is not in repo_source" % (epkg, dst_repo_dir))
                os.remove(os.path.join(dst_repo_dir, epkg))

    def _clone_rpms(self, dst_repo_dir, src_repo_dir, whitelist_packages, blacklist_packages, progress_callback=None):
        # Compute and clone packages
        unfiltered_pkglist = self.list_rpms(src_repo_dir)
        pkglist = self._find_filtered_package_list(unfiltered_pkglist, whitelist_packages, blacklist_packages, is_clone=True)
        if progress_callback is not None:
            self.progress['step'] = ProgressReport.DownloadItems
            progress_callback(self.progress)
        log.debug("Processing %s potential packages" % (len(pkglist)))
        for count, pkg in enumerate(pkglist):
            if self.stopped:
                raise CancelException()
            pkg_relativepath = pkg.split(os.path.normpath(src_repo_dir + '/'))[-1]
            try:
                rpm_name = os.path.basename(pkg_relativepath)
                self._create_clone(pkg_relativepath, src_repo_dir, dst_repo_dir)
                self.progress['num_download'] += 1
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
            item_size = self._calculate_bytes(src_repo_dir, [pkg])#_relativepath])
            self.progress['size_left'] -= item_size
            self.progress['items_left'] -= 1
            self.progress['details']["rpm"]["items_left"] -= 1
            self.progress['details']["rpm"]["size_left"] -= item_size

            if progress_callback is not None:
                progress_callback(self.progress)
                self.progress["item_type"] = ""
                self.progress["item_name"] = ""
        log.info("Finished cloning %s packages" % (len(pkglist)))

    def _sync_drpms(self, dst_repo_dir, src_repo_dir, progress_callback=None):
        # Compute and import delta rpms
        dpkglist = self.list_drpms(src_repo_dir)
        if progress_callback is not None:
            self.progress['step'] = ProgressReport.DownloadItems
            progress_callback(self.progress)
        dst_drpms_dir = os.path.join(dst_repo_dir, "drpms")
        if not os.path.exists(dst_drpms_dir):
            os.makedirs(dst_drpms_dir)
        src_drpms_dir = os.path.join(src_repo_dir, "drpms")
        for count, pkg in enumerate(dpkglist):
            if self.stopped:
                raise CancelException()
            skip_copy = False
            log.debug("Processing drpm %s" % pkg)
            if count % 500 == 0:
                log.info("Working on %s/%s" % (count, len(dpkglist)))
            try:
                if self.is_clone:
                    self._create_clone(os.path.basename(pkg), src_drpms_dir, dst_drpms_dir)
                else:
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

    def _sync_distributions(self, dst_repo_dir, src_repo_dir, progress_callback=None):
        imlist = self.list_tree_files(src_repo_dir)
        if not imlist:
            log.info("No image files to import")
            return
        # compute and import treeinfo
        treecfg = None
        for tree_info_name in ['treeinfo', '.treeinfo']:
            treecfg = os.path.join(src_repo_dir, tree_info_name)
            if os.path.exists(treecfg):
                break
            else:
                treecfg = None
        if not treecfg:
            log.info("No treeinfo file found in the source tree; no distributions to process")
            return
        treeinfo = parse_treeinfo(treecfg)
        ks_label = "ks-%s-%s-%s-%s" % (treeinfo['family'], treeinfo['variant'],
                                               treeinfo['version'], treeinfo['arch'] or "noarch")
        distro_path = "%s/%s" % (pulp.server.util.top_distribution_location(), ks_label)
        if not os.path.exists(distro_path):
            os.makedirs(distro_path)
        dist_tree_path = os.path.join(distro_path, tree_info_name)
        log.debug("Copying treeinfo file from %s to %s" % (treecfg, dist_tree_path))
        try:
            skip_copy = False
            if os.path.exists(dist_tree_path) and not self.is_clone:
                dst_treecfg_checksum = pulp.server.util.get_file_checksum(filename=dist_tree_path)
                src_treecfg_checksum = pulp.server.util.get_file_checksum(filename=treecfg)
                if src_treecfg_checksum == dst_treecfg_checksum:
                    log.info("treecfg file %s already exists with same checksum. skip import" % dist_tree_path)
                    skip_copy = True
            if not skip_copy and not self.is_clone:
                if not os.path.isdir(os.path.dirname(dist_tree_path)):
                    os.makedirs(os.path.dirname(dist_tree_path))
                shutil.copy(treecfg, dist_tree_path)
        except:
            # probably the same file
            if os.path.exists(dist_tree_path):
                log.debug("distribution tree info file already exists at %s" % dist_tree_path)
            else:
                log.error("Error copying treeinfo file to distribution location")
        repo_treefile_path = os.path.join(dst_repo_dir, tree_info_name)
        if not os.path.islink(repo_treefile_path):
            log.info("creating a symlink for treeinfo file from %s to %s" % (dist_tree_path, repo_treefile_path))
            pulp.server.util.create_rel_symlink(dist_tree_path, repo_treefile_path)
            
        # process ks files associated to distribution
        for imfile in imlist:
            try:
                if self.stopped:
                    raise CancelException()
                skip_copy = False
                rel_file_path = imfile.split('/images/')[-1]
                dst_file_path = os.path.join(distro_path, rel_file_path)
                if self.is_clone:
                    src_repo_img_dir = "%s/%s" % (src_repo_dir, "images")
                    dst_repo_img_dir =  "%s/%s" % (dst_repo_dir, "images")
                    self._create_clone(rel_file_path, src_repo_img_dir, dst_repo_img_dir)
                    self.progress['num_download'] += 1
                    self.progress['details']["tree_file"]["num_success"] += 1
                    self.progress["num_success"] += 1
                    skip_copy = True
                elif os.path.exists(dst_file_path):
                    dst_file_checksum = pulp.server.util.get_file_checksum(filename=dst_file_path)
                    src_file_checksum = pulp.server.util.get_file_checksum(filename=imfile)
                    if src_file_checksum == dst_file_checksum:
                        log.info("file %s already exists with same checksum. skip import" % rel_file_path)
                        self.progress['details']["tree_file"]["num_success"] += 1
                        self.progress["num_success"] += 1
                        skip_copy = True
                if not skip_copy:
                    file_dir = os.path.dirname(dst_file_path)
                    if not os.path.exists(file_dir):
                        os.makedirs(file_dir)
                    shutil.copy(imfile, dst_file_path)
                    self.progress['num_download'] += 1
                    self.progress['details']["tree_file"]["num_success"] += 1
                    self.progress["num_success"] += 1
                    log.debug("Imported file %s " % dst_file_path)
                repo_dist_path = "%s/%s/%s" % (dst_repo_dir, "images", dst_file_path.split(distro_path)[-1])
                if not os.path.islink(repo_dist_path):
                    log.info("Creating a symlink to repo location from [%s] to [%s]" % (dst_file_path, repo_dist_path))
                    pulp.server.util.create_rel_symlink(dst_file_path, repo_dist_path)
            except (IOError, OSError):
                log.error("%s" % (traceback.format_exc()))
                error_info = {}
                exctype, value = sys.exc_info()[:2]
                error_info["error_type"] = str(exctype)
                error_info["error"] = str(value)
                error_info["traceback"] = traceback.format_exc().splitlines()
                self._add_error_details(imfile, "tree_file", error_info)

            self.progress['step'] = ProgressReport.DownloadItems
            item_size = self._calculate_bytes(src_repo_dir, [imfile])
            self.progress['size_left'] -= item_size
            self.progress['items_left'] -= 1
            self.progress['details']["tree_file"]["items_left"] -= 1
            self.progress['details']["tree_file"]["size_left"] -= item_size
            if progress_callback is not None:
                progress_callback(self.progress)

    def list_repodata_files(self, src_repo_dir):
        src_repodata_dir = os.path.join(src_repo_dir, "repodata")
        if not os.path.exists(src_repodata_dir):
            return []
        return pulp.server.util.listdir(src_repodata_dir)

    def list_serverdir_files(self, src_repo_dir):
        # this is for RHEL5 trees
        src_server_dir = os.path.join(src_repo_dir, "Server")
        if not os.path.exists(src_server_dir):
            return []
        return pulp.server.util.listdir(src_server_dir)

    def _sync_server_dir(self, dst_repo_dir, src_repo_dir, progress_callback=None):
        sfiles = self.list_serverdir_files(src_repo_dir)
        if not sfiles:
            return
        # process server directory
        for count, pkg in enumerate(sfiles):
            if self.stopped:
                raise CancelException()
            skip_copy = False
            pkg_relativepath = pkg.split(os.path.normpath(src_repo_dir + '/'))[-1]
            dst_file_path = "%s/%s" % (dst_repo_dir, pkg_relativepath)
            try:
                if self.is_clone:
                    self._create_clone(pkg_relativepath, src_repo_dir, dst_repo_dir)
                else:
                    if os.path.exists(dst_file_path):
                        if os.path.realpath(dst_file_path) == os.path.realpath(pkg):
                            log.debug("%s and %s are the same file; skip" % (dst_file_path, pkg))
                            skip_copy = True 
                    if not skip_copy:
                        real_pkg_path = os.path.realpath(pkg)
                        file_dir = os.path.dirname(dst_file_path)
                        if not os.path.exists(file_dir):
                            os.makedirs(file_dir)
                        if os.path.islink(dst_file_path):
                            os.unlink(dst_file_path)
                        pulp.server.util.create_rel_symlink(real_pkg_path, dst_file_path)
                        log.debug("Imported file %s " % dst_file_path)
            except (IOError, OSError):
                log.error("%s" % (traceback.format_exc()))
                error_info = {}
                exctype, value = sys.exc_info()[:2]
                error_info["error_type"] = str(exctype)
                error_info["error"] = str(value)
                error_info["traceback"] = traceback.format_exc().splitlines()

            if progress_callback is not None:
                progress_callback(self.progress)
        log.info("Finished cloning %s files in server dir" % (len(sfiles)))


    def local(self, repo_id, repo_source, skip_dict={}, progress_callback=None,
            max_speed=None, threads=None):
        repo = self.repo_api._get_existing_repo(repo_id)
        src_repo_dir = urlparse(encode_unicode(repo_source['url']))[2]
        log.info("sync of %s for repo %s" % (decode_unicode(src_repo_dir), repo['id']))
        self.init_progress_details(src_repo_dir, skip_dict)

        try:
            dst_repo_dir = "%s/%s" % (pulp.server.util.top_repos_location(), repo['relative_path'])
            self.repo_dir = dst_repo_dir
            # Process repo filters if any
            if repo['filters']:
                log.info("Repo filters : %s" % repo['filters'])
                whitelist_packages = self.repo_api.find_combined_whitelist_packages(repo['filters'])
                blacklist_packages = self.repo_api.find_combined_blacklist_packages(repo['filters'])
                log.info("combined whitelist packages = %s" % whitelist_packages)
                log.info("combined blacklist packages = %s" % blacklist_packages)
            else:
                whitelist_packages = []
                blacklist_packages = []

            src_repo_dir = encode_unicode(src_repo_dir)
            if not os.path.exists(src_repo_dir):
                raise InvalidPathError("Path %s is invalid" % src_repo_dir)

            dst_repo_dir = encode_unicode(dst_repo_dir)
            if not os.path.exists(dst_repo_dir):
                os.makedirs(dst_repo_dir)

            if not skip_dict.has_key('packages') or skip_dict['packages'] != 1:
                log.debug("Starting _sync_rpms(%s, %s)" % (dst_repo_dir, src_repo_dir))
                if self.is_clone:
                    self._clone_rpms(dst_repo_dir, src_repo_dir, whitelist_packages, 
                            blacklist_packages, progress_callback)
                    log.debug("Completed _clone_rpms(%s,%s)" %
                            (dst_repo_dir, src_repo_dir))
                else:
                    self._sync_rpms(dst_repo_dir, src_repo_dir, whitelist_packages,
                            blacklist_packages, progress_callback)
                    log.debug("Completed _sync_rpms(%s,%s)" %
                            (dst_repo_dir, src_repo_dir))
                log.debug("Starting _sync_drpms(%s, %s)" % (dst_repo_dir, src_repo_dir))
                self._sync_drpms(dst_repo_dir, src_repo_dir, progress_callback)
                log.debug("Completed _sync_drpms(%s,%s)" % (dst_repo_dir, src_repo_dir))
            else:
                log.info("Skipping package imports from sync process")
            # process distributions
            if not skip_dict.has_key('distribution') or skip_dict['distribution'] != 1:
                log.debug("Starting _sync_distributions(%s, %s)" % (dst_repo_dir, src_repo_dir))
                self._sync_distributions(dst_repo_dir, src_repo_dir, progress_callback)
                log.debug("Completed _sync_distributions(%s,%s)" % (dst_repo_dir, src_repo_dir))
            else:
                log.info("Skipping distribution imports from sync process")

            if self.is_clone or self.repo_api.has_parent(repo_id):
                # RHEL-5 repos could have Server directory in them
                log.debug("Starting _sync_server_dir(%s, %s)" % (dst_repo_dir, src_repo_dir))
                self._sync_server_dir(dst_repo_dir, src_repo_dir, progress_callback)
                log.debug("Completed _sync_server_dir(%s,%s)" % (dst_repo_dir, src_repo_dir))
            else:
                log.info("No server dir to import")
            if progress_callback is not None:
                self.progress['step'] = "Exporting repo metadata"
                progress_callback(self.progress)
            src_repodata_dir = os.path.join(src_repo_dir, "repodata")
            dst_repodata_dir = os.path.join(dst_repo_dir, "repodata")
            if self.stopped:
                raise CancelException()
            try:
                log.info("Copying repodata from %s to %s" % (src_repodata_dir, dst_repodata_dir))
                if os.path.exists(dst_repodata_dir):
                    shutil.rmtree(dst_repodata_dir)
                shutil.copytree(src_repodata_dir, dst_repodata_dir)
            except (IOError, OSError):
                log.error("%s" % (traceback.format_exc()))
                error_info = {}
                exctype, value = sys.exc_info()[:2]
                error_info["error_type"] = str(exctype)
                error_info["error"] = str(value)
                error_info["traceback"] = traceback.format_exc().splitlines()
            if progress_callback is not None:
                progress_callback(self.progress)
        except InvalidPathError:
            log.error("Sync aborted due to invalid source path %s" % (src_repo_dir))
            raise
        except IOError:
            log.error("Unable to create repo directory %s" % dst_repo_dir)
            raise
        return dst_repo_dir

class FileSynchronizer(BaseSynchronizer):
    """
     File synchronizer class to sync isos, txt,  etc from remote or local feeds
    """
    def __init__(self):
        super(FileSynchronizer, self).__init__()
        self.file_repo_grinder = None

    def remote(self, repo_id, repo_source, skip_dict={}, progress_callback=None, max_speed=None, threads=None):
        repo = self.repo_api._get_existing_repo(repo_id)
        cacert = clicert = None
        if repo['feed_ca']:
            cacert = repo['feed_ca'].encode('utf8')
        if repo['feed_cert']:
            clicert = repo['feed_cert'].encode('utf8')
        log.info("cacert = <%s>, cert = <%s>" % (cacert, clicert))
        # check for proxy settings
        proxy_url = proxy_port = proxy_user = proxy_pass = None
        for proxy_cfg in ['proxy_url', 'proxy_port', 'proxy_user', 'proxy_pass']:
            if config.config.has_option('yum', proxy_cfg):
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
        self.file_repo_grinder = FileGrinder('', repo_source['url'].encode('ascii', 'ignore'),
                                num_threads, cacert=cacert, clicert=clicert,
                                proxy_url=self.proxy_url, proxy_port=self.proxy_port,
                                proxy_user=self.proxy_user or None, proxy_pass=self.proxy_pass or None,
                                files_location=pulp.server.util.top_file_location(), max_speed=limit_in_KB)
        relative_path = repo['relative_path']
        if relative_path:
            store_path = "%s/%s" % (pulp.server.util.top_repos_location(), relative_path)
        else:
            store_path = "%s/%s" % (pulp.server.util.top_repos_location(), repo['id'])
        report = self.file_repo_grinder.fetch(store_path, callback=progress_callback)
        if self.stopped:
            raise CancelException()
        self.progress = yum_rhn_progress_callback(report.last_progress)
        start = time.time()

        if self.stopped:
            raise CancelException()
        log.info("FileSynchronizer reported %s successes, %s downloads, %s errors" \
                % (report.successes, report.downloads, report.errors))
        return store_path

    def local(self, repo_id, repo_source, skip_dict={}, progress_callback=None,
              max_speed=None, threads=None):
        repo = self.repo_api._get_existing_repo(repo_id)
        src_repo_dir = urlparse(encode_unicode(repo_source['url']))[2]
        log.info("sync of %s for repo %s" % (src_repo_dir, repo['id']))
        self.init_progress_details(src_repo_dir, skip_dict)

        try:
            dst_repo_dir = "%s/%s" % (pulp.server.util.top_repos_location(), repo['relative_path'])

            if not os.path.exists(src_repo_dir):
                raise InvalidPathError("Path %s is invalid" % src_repo_dir)

            if not os.path.exists(dst_repo_dir):
                os.makedirs(dst_repo_dir)
            filelist = self.list_files(src_repo_dir)
            for count, pkg in enumerate(filelist):
                skip_copy = False
                log.debug("Processing files %s" % pkg)
                if count % 500 == 0:
                    log.info("Working on %s/%s" % (count, len(filelist)))
                try:
                    if self.is_clone:
                        self._create_clone(os.path.basename(pkg), src_repo_dir, dst_repo_dir)
                    else:
                        src_file_checksum = pulp.server.util.get_file_checksum(hashtype="sha256", filename=pkg)
                        dst_file_path = os.path.join(dst_repo_dir, os.path.basename(pkg))
                        if not pulp.server.util.check_package_exists(dst_file_path, src_file_checksum):
                            shutil.copy(pkg, dst_file_path)
                            self.progress['num_download'] += 1
                        else:
                            log.info("file %s already exists with same checksum. skip import" % os.path.basename(pkg))
                            skip_copy = True
                        log.debug("Imported delta rpm %s " % dst_file_path)
                    self.progress['details']["file"]["num_success"] += 1
                    self.progress["num_success"] += 1
                except (IOError, OSError):
                    log.error("%s" % (traceback.format_exc()))
                    error_info = {}
                    exctype, value = sys.exc_info()[:2]
                    error_info["error_type"] = str(exctype)
                    error_info["error"] = str(value)
                    error_info["traceback"] = traceback.format_exc().splitlines()
                    self._add_error_details(pkg, "file", error_info)
                self.progress['step'] = ProgressReport.DownloadItems
                item_size = self._calculate_bytes(src_repo_dir, [pkg])
                self.progress['size_left'] -= item_size
                self.progress['items_left'] -= 1
                self.progress['details']["file"]["items_left"] -= 1
                self.progress['details']["file"]["size_left"] -= item_size
                if progress_callback is not None:
                    progress_callback(self.progress)

        except InvalidPathError:
            log.error("Sync aborted due to invalid source path %s" % (src_repo_dir))
            raise
        except IOError:
            log.error("Unable to create repo directory %s" % dst_repo_dir)
            raise
        return dst_repo_dir

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

        files = self.list_files(src_repo_dir)
        self._init_progress_details("file", files, src_repo_dir)

    def list_files(self, file_repo_dir):
        return pulp.server.util.listdir(file_repo_dir)

    def stop(self):
        super(FileSynchronizer, self).stop()
        if self.file_repo_grinder:
            log.info("Stop sync is being issued")
            self.file_repo_grinder.stop(block=False)

    def update_metadata(self, repo_dir, repo_id, progress_callback=None):
        """
         Implement this method if there is a reason to regenerate file metadata.
        """
        return
 
def parse_treeinfo(treecfg):
    """
     Parse distribution treeinfo config and return general information
    """
    fields = ['family', 'variant', 'version', 'arch', 'timestamp']
    treeinfo_dict = dict(zip(fields, [None]*len(fields)))
    cfgparser = ConfigParser.ConfigParser()
    cfgparser.optionxform = str
    try:
        treecfg_fp = open(treecfg)
        cfgparser.readfp(treecfg_fp)
    except Exception, e:
        log.info("Unable to read the tree info config.")
        log.info(e)
        return treeinfo_dict
    if cfgparser.has_section('general'):
        for field in fields:
            try:
                treeinfo_dict[field] = cfgparser.get('general', field) or None
            except:
                log.error("No field with name [%s] found in treeinfo file; defaulting to None" % field)
                treeinfo_dict[field] = None
    treecfg_fp.close()
    return treeinfo_dict
