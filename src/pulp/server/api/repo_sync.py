#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
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
import time
import traceback
import shutil
from urlparse import urlparse

import yum

import pulp.server.comps_util
import pulp.server.crontab
import pulp.server.upload
import pulp.server.util
from grinder.RepoFetch import YumRepoGrinder
from grinder.RHNSync import RHNSync
from pulp.server import updateinfo
from pulp.server.api.errata import ErrataApi
from pulp.server.api.package import PackageApi
from pulp.server import config
from pulp.server.pexceptions import PulpException


log = logging.getLogger(__name__)

# sync api --------------------------------------------------------------------

def yum_rhn_progress_callback(info):
    fields = ('status',
              'item_name',
              'items_left',
              'items_total',
              'size_left',
              'size_total')
    values = tuple(getattr(info, f) for f in fields)
    log.info("Progress: %s on <%s>, %s/%s items %s/%s bytes" % values)
    return dict(zip(fields, values))


def sync(repo, repo_source, progress_callback=None):
    '''
    Synchronizes content for the given RepoSource.

    @param repo: repo to synchronize; may not be None
    @type  repo: L{pulp.model.Repo}

    @param repo_source: indicates the source from which the repo data will be syncced; may not be None
    @type  repo_source: L{pulp.model.RepoSource}
    '''
    source_type = repo_source['type']
    if source_type not in type_classes:
        raise PulpException('Could not find synchronizer for repo type [%s]', source_type)
    synchronizer = type_classes[source_type]()
    repo_dir = synchronizer.sync(repo, repo_source, progress_callback)
    return synchronizer.add_packages_from_dir(repo_dir, repo)


def update_schedule(repo):
    '''
    Updates the repo sync scheduler entry with the schedule for the given repo.

    @param repo: repo containg the id and sync schedule; may not be None
    @type  repo: L{pulp.model.Repo}
    '''
    tab = pulp.server.crontab.CronTab()

    cmd = _cron_command(repo)
    entries = tab.find_command(cmd)

    if len(entries) == 0:
        entry = tab.new(command=cmd)
    else:
        entry = entries[0]

    entry.parse(repo['sync_schedule'] + ' ' + cmd)

    log.debug('Writing updated cron entry [%s]' % entry.render())
    tab.write()


def delete_schedule(repo):
    '''
    Deletes the repo sync schedule file for the given repo.

    @param repo: repo containg the id and sync schedule; may not be None
    @type  repo: L{pulp.model.Repo}
    '''
    tab = pulp.server.crontab.CronTab()

    cmd = _cron_command(repo)
    entries = tab.find_command(cmd)

    if len(entries) > 0:
        for entry in entries:
            log.debug('Removing entry [%s]' % entry.render())
            tab.remove(entry)
        tab.write()
    else:
        log.debug('No existing cron entry for repo [%s]' % repo['id'])

def _cron_command(repo):
    return 'pulp repo sync %s' % repo['id']

# synchronization classes -----------------------------------------------------

class InvalidPathError(Exception):
    pass


class BaseSynchronizer(object):

    def __init__(self):
        self.package_api = PackageApi()
        self.errata_api = ErrataApi()

    def add_packages_from_dir(self, dir, repo):

        startTime = time.time()
        log.debug("Begin to add packages from %s into %s" % (dir, repo['id']))
        package_list = pulp.server.util.get_repo_packages(dir)
        added_packages = {}
        added_errataids = []
        log.debug("Processing %s potential packages" % (len(package_list)))
        for package in package_list:
            package = self.import_package(package, repo)
            if (package is not None):
                added_packages[package["id"]] = package
        endTime = time.time()
        log.debug("Repo: %s read [%s] packages took %s seconds" %
                (repo['id'], len(added_packages), endTime - startTime))
        # Import groups metadata if present
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
            if "updateinfo" in ftypes:
                updateinfo_xml_path = pulp.server.util.get_repomd_filetype_path(
                        repomd_xml_path, "updateinfo")
                updateinfo_xml_path = os.path.join(dir.encode("ascii", "ignore"),
                        updateinfo_xml_path)
                log.info("updateinfo is found in repomd.xml, it's path is %s" % \
                        (updateinfo_xml_path))
                added_errataids = self.sync_updateinfo_data(updateinfo_xml_path, repo)
                log.debug("Loaded updateinfo from %s for %s" % \
                        (updateinfo_xml_path, repo["id"]))
        return added_packages, added_errataids

    def import_package(self, package, repo):
        try:
            retval = None
            file_name = package.relativepath
            hashtype = "sha256"
            checksum = package.checksum
            found = self.package_api.packages(name=package.name,
                    epoch=package.epoch, version=package.version,
                    release=package.release, arch=package.arch,
                    filename=file_name,
                    checksum_type=hashtype, checksum=checksum)
            if len(found) == 1:
                retval = found[0]
            else:
                retval = self.package_api.create(package.name, package.epoch,
                    package.version, package.release, package.arch, package.description,
                    hashtype, checksum, file_name)
                for dep in package.requires:
                    retval.requires.append(dep[0])
                for prov in package.provides:
                    retval.provides.append(prov[0])
                retval.download_url = config.config.get('server', 'base_url') + "/" + \
                                      config.config.get('server', 'relative_url') + "/" + \
                                      repo["id"] + "/" + file_name
                self.package_api.update(retval)
            return retval
        except Exception, e:
            log.error("error reading package %s" % (file_name))
            log.debug("%s" % (traceback.format_exc()))

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
                    self.errata_api.delete(e['id'])
                pkglist = e['pkglist']
                self.errata_api.create(id=e['id'], title=e['title'],
                        description=e['description'], version=e['version'],
                        release=e['release'], type=e['type'],
                        status=e['status'], updated=e['updated'],
                        issued=e['issued'], pushcount=e['pushcount'],
                        from_str=e['from_str'], reboot_suggested=e['reboot_suggested'],
                        references=e['references'], pkglist=pkglist,
                        repo_defined=True, immutable=True)
            end = time.time()
            log.debug("%s new/updated errata imported in %s seconds" % (len(eids), (end - start)))
        except yum.Errors.YumBaseError, e:
            log.error("Unable to parse updateinfo file %s for %s" % (updateinfo_xml_path, repo["id"]))
            return []
        return eids

    def repos_location():
        return "%s/%s" % (config.config.get('paths', 'local_storage'), "repos")

    def package_location():
        return "%s/%s" % (config.config.get('paths', 'local_storage'), "packages")


class YumSynchronizer(BaseSynchronizer):

    def sync(self, repo, repo_source, progress_callback=None):
        cacert = clicert = clikey = None
        if repo['ca'] and repo['cert'] and repo['key']:
            cacert = repo['ca'].encode('utf8')
            clicert = repo['cert'].encode('utf8')
            clikey = repo['key'].encode('utf8')

        yfetch = YumRepoGrinder('', repo_source['url'].encode('ascii', 'ignore'),
                                1, cacert=cacert, clicert=clicert, 
                                clikey=clikey, packages_location=package_location())
        relative_path = repo['relative_path']
        if relative_path:
            store_path = "%s/%s" % (repos_location(), relative_path)
        else:
            store_path = "%s/%s" % (repos_location(), repo['id'])
        yfetch.fetchYumRepo(store_path, callback=progress_callback)

        return store_path


class LocalSynchronizer(BaseSynchronizer):
    """
    Sync class to synchronize a directory of rpms from a local filer
    """
    def sync(self, repo, repo_source, progress_callback=None):
        pkg_dir = urlparse(repo_source['url']).path.encode('ascii', 'ignore')
        log.debug("sync of %s for repo %s" % (pkg_dir, repo['id']))
        try:
            repo_dir = "%s/%s" % (repos_location(), repo['id'])
            if not os.path.exists(pkg_dir):
                raise InvalidPathError("Path %s is invalid" % pkg_dir)
            if repo['use_symlinks']:
                log.info("create a symlink to src directory %s %s" % (pkg_dir, repo_dir))
                os.symlink(pkg_dir, repo_dir)
            else:
                if not os.path.exists(repo_dir):
                    os.makedirs(repo_dir)

                pkglist = pulp.server.util.listdir(pkg_dir)
                log.debug("Found %s packages in %s" % (len(pkglist), pkg_dir))
                for count, pkg in enumerate(pkglist):
                    if pkg.endswith(".rpm"):
                        if count % 500 == 0:
                            log.debug("Working on %s/%s" % (count, len(pkglist)))
                        pkg_info = pulp.server.util.get_rpm_information(pkg)
                        pkg_location = "%s/%s/%s/%s/%s/%s" % (package_location(), pkg_info.name, pkg_info.version, 
                                                                pkg_info.release, pkg_info.arch, os.path.basename(pkg))
                        
                        if not pulp.server.util.check_package_exists(pkg_location,\
                                                 pulp.server.util.get_file_checksum(filename=pkg)):
                            log.error("package doesn't exist. \
                                        Write the package to packages location: %s" % pkg_location)
                            pkg_dirname = os.path.dirname(pkg_location)
                            if not os.path.exists(pkg_dirname):
                                os.makedirs(pkg_dirname)
                            shutil.copy(pkg, pkg_location)
                        else:
                            log.error("package Already exists. continue")

                        repo_pkg_path = os.path.join(repo_dir, os.path.basename(pkg))
                        if not os.path.islink(repo_pkg_path):
                            os.symlink(pkg_location, repo_pkg_path)

##TODO: Need to revist the removal case
#                # Remove rpms which are no longer in source
#                existing_pkgs = []
#                for pkg in pulp.server.util.listdir(repo_dir):
#                    if pkg.endswith(".rpm"):
#                        existing_pkgs.append(os.path.basename(pkg))
#                source_pkgs = [os.path.basename(p) for p in pkglist]
#                for epkg in existing_pkgs:
#                    if epkg not in source_pkgs:
#                        log.info("Remove %s from repo %s because it is not in repo_source" % (epkg, repo["id"]))
#                        os.remove(os.path.join(repo_dir, epkg))
                groups_xml_path = None
                updateinfo_path = None
                src_repomd_xml = os.path.join(pkg_dir, "repodata/repomd.xml")
                if os.path.isfile(src_repomd_xml):
                    ftypes = pulp.server.util.get_repomd_filetypes(src_repomd_xml)
                    log.debug("repodata has filetypes of %s" % (ftypes))
                    if "group" in ftypes:
                        g = pulp.server.util.get_repomd_filetype_path(src_repomd_xml, "group")
                        src_groups = os.path.join(pkg_dir, g)
                        if os.path.isfile(src_groups):
                            shutil.copy(src_groups,
                                os.path.join(repo_dir, os.path.basename(src_groups)))
                            log.debug("Copied groups over to %s" % (repo_dir))
                        groups_xml_path = os.path.join(repo_dir,
                            os.path.basename(src_groups))
                    if "updateinfo" in ftypes:
                        f = pulp.server.util.get_repomd_filetype_path(src_repomd_xml, "updateinfo")
                        src_updateinfo_path = os.path.join(pkg_dir, f)
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
                                os.path.join(repo_dir, "updateinfo.xml"), "wt"))
                            log.debug("Copied %s to %s" % (src_updateinfo_path, repo_dir))
                            updateinfo_path = os.path.join(repo_dir, "updateinfo.xml")
                log.info("Running createrepo, this may take a few minutes to complete.")
                start = time.time()
                pulp.server.upload.create_repo(repo_dir, groups=groups_xml_path)
                end = time.time()
                log.info("Createrepo finished in %s seconds" % (end - start))
                if updateinfo_path:
                    log.debug("Modifying repo for updateinfo")
                    pulp.server.upload.modify_repo(os.path.join(repo_dir, "repodata"),
                            updateinfo_path)
        except InvalidPathError:
            log.error("Sync aborted due to invalid source path %s" % (pkg_dir))
            raise
        except IOError:
            log.error("Unable to create repo directory %s" % repo_dir)
            raise
        return repo_dir

class RHNSynchronizer(BaseSynchronizer):

    def sync(self, repo, repo_source, progress_callback=None):
        # Parse the repo source for necessary pieces
        # Expected format:   <server>/<channel>
        pieces = repo_source['url'].split('/')
        if len(pieces) < 2:
            raise PulpException('Feed format for RHN type must be <server>/<channel>. Feed: %s',
                                repo_source['url'])

        host = 'http://' + pieces[0]
        channel = pieces[1]

        log.info('Synchronizing from RHN. Host [%s], Channel [%s]' % (host, channel))

        # Create and configure the grinder hook to RHN
        s = RHNSync()
        s.setURL(host)
        s.setParallel(config.config.get('rhn', 'threads'))

        # Perform the sync
        dest_dir = '%s/%s/' % (config.config.get('paths', 'local_storage'), repo['id'])
        s.syncPackages(channel, savePath=dest_dir, callback=progress_callback)
        s.createRepo(dest_dir)
        updateinfo_path = os.path.join(dest_dir, "updateinfo.xml")
        if os.path.isfile(updateinfo_path):
            log.info("updateinfo_path is found, calling updateRepo")
            s.updateRepo(updateinfo_path, os.path.join(dest_dir, "repodata"))

        return dest_dir

# synchronization type map ----------------------------------------------------

type_classes = {
    'yum': YumSynchronizer,
    'local': LocalSynchronizer,
    'rhn': RHNSynchronizer,
}
