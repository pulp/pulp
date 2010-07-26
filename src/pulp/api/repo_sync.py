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

# Python
import logging
import os
import time
import traceback
import shutil
from urlparse import urlparse

# 3rd Party
import yum

# Pulp
from grinder.RepoFetch import YumRepoGrinder
from grinder.RHNSync import RHNSync
from pulp.api.package import PackageApi
from pulp.pexceptions import PulpException
import pulp.comps_util
import pulp.crontab
import pulp.upload
import pulp.util


log = logging.getLogger(__name__)


def sync(config, repo, repo_source):
    '''
    Synchronizes content for the given RepoSource.

    @param repo: repo to synchronize; may not be None
    @type  repo: L{pulp.model.Repo}

    @param repo_source: indicates the source from which the repo data will be syncced; may not be None
    @type  repo_source: L{pulp.model.RepoSource}
    '''
    if not TYPE_CLASSES.has_key(repo_source['type']):
        raise PulpException('Could not find synchronizer for repo type [%s]', repo_source['type'])

    synchronizer = TYPE_CLASSES[repo_source['type']](config)
    repo_dir = synchronizer.sync(repo, repo_source)
    return synchronizer.add_packages_from_dir(repo_dir, repo)

def update_schedule(config, repo):
    '''
    Updates the repo sync scheduler entry with the schedule for the given repo.

    @param config: pulp configuration values; may not be None
    @type  config: L{ConfigParser}

    @param repo: repo containg the id and sync schedule; may not be None
    @type  repo: L{pulp.model.Repo}
    '''
    tab = pulp.crontab.CronTab()

    cmd = _cron_command(repo)
    entries = tab.find_command(cmd)

    if len(entries) == 0:
        entry = tab.new(command=cmd)
    else:
        entry = entries[0]

    entry.parse(repo['sync_schedule'] + ' ' + cmd)

    log.debug('Writing updated cron entry [%s]' % entry.render())
    tab.write()

def delete_schedule(config, repo):
    '''
    Deletes the repo sync schedule file for the given repo.

    @param config: pulp configuration values; may not be None
    @type  config: L{ConfigParser}

    @param repo: repo containg the id and sync schedule; may not be None
    @type  repo: L{pulp.model.Repo}
    '''
    tab = pulp.crontab.CronTab()

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


class BaseSynchronizer(object):

    def __init__(self, config):
        self.config = config
        self.package_api = PackageApi(config)

    def add_packages_from_dir(self, dir, repo):
        
        startTime = time.time()
        package_list = pulp.util.get_repo_packages(dir)
        added_packages = []
        log.debug("Processing %s potential packages" % (len(package_list)))
        for package in package_list:
            package = self.import_package(package, repo)
            if (package != None):
                added_packages.append(package)
        endTime = time.time()
        log.debug("Repo: %s read [%s] packages took %s seconds" % 
                (repo['id'], len(added_packages), endTime - startTime))
        # Import groups metadata if present
        repomd_xml_path = os.path.join(dir.encode("ascii", "ignore"), 'repodata/repomd.xml')
        if os.path.isfile(repomd_xml_path):
            repo["repomd_xml_path"] = repomd_xml_path
            ftypes = pulp.util.get_repomd_filetypes(repomd_xml_path)
            log.debug("repodata has filetypes of %s" % (ftypes))
            if "group" in ftypes:
                group_xml_path = pulp.util.get_repomd_filetype_path(repomd_xml_path, "group")
                group_xml_path = os.path.join(dir.encode("ascii", "ignore"), group_xml_path)
                if os.path.isfile(group_xml_path):
                    groupfile = open(group_xml_path, "r")
                    repo['group_xml_path'] = group_xml_path
#                    self.sync_groups_data(groupfile, repo)
#                    log.debug("Loaded group info from %s" % (group_xml_path))
                else:
                    log.info("Group info not found at file: %s" % (group_xml_path))
            if "group_gz" in ftypes:
                group_gz_xml_path = pulp.util.get_repomd_filetype_path(
                        repomd_xml_path, "group_gz")
                group_gz_xml_path = os.path.join(dir.encode("ascii", "ignore"),
                        group_gz_xml_path)
                repo['group_gz_xml_path'] = group_gz_xml_path
            else:
                log.debug("Skipping group import, no group info present in repodata")
        return added_packages

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
                retval.download_url = self.config.get('server', 'base_url') + "/" + \
                                        self.config.get('server', 'relative_url') + "/" + \
                                        repo["id"] + "/" +  file_name
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
                ctg = pulp.comps_util.yum_category_to_model_category(c)
                ctg["immutable"] = True
                ctg["repo_defined"] = True
                repo['packagegroupcategories'][ctg['id']] = ctg
            for g in comps.groups:
                grp = pulp.comps_util.yum_group_to_model_group(g)
                grp["immutable"] = True
                grp["repo_defined"] = True
                repo['packagegroups'][grp['id']] = grp
        except yum.Errors.CompsException:
            log.error("Unable to parse group info for %s" % (compsfile))
            return False
        return True
    
class YumSynchronizer(BaseSynchronizer):
    def sync(self, repo, repo_source):
        cacert = clicert = clikey = None
        if repo['ca'] and repo['cert'] and repo['key']:
            cacert = repo['ca'].encode('utf8')
            clicert=repo['cert'].encode('utf8')
            clikey=repo['key'].encode('utf8')
        yfetch = YumRepoGrinder(repo['id'], repo_source['url'].encode('ascii', 'ignore'), 
                                1, cacert=cacert, clicert=clicert, clikey=clikey)
        yfetch.fetchYumRepo(self.config.get('paths', 'local_storage'))
        repo_dir = "%s/%s/" % (self.config.get('paths', 'local_storage'), repo['id'])
        return repo_dir
    
class LocalSynchronizer(BaseSynchronizer):
    """
        Sync class to synchronize a directory of rpms from a local filer
    """
    def sync(self, repo, repo_source):

        pkg_dir = urlparse(repo_source['url']).path.encode('ascii', 'ignore')
        try:
            repo_dir = "%s/%s" % (self.config.get('paths', 'local_storage'), repo['id'])
            if not os.path.exists(pkg_dir):
                raise InvalidPathError("Path %s is invalid" % pkg_dir)
            if repo['use_symlinks']:
                log.info("create a symlink to src directory %s %s" % (pkg_dir, repo_dir))
                os.symlink(pkg_dir, repo_dir)
            else:
                if not os.path.exists(repo_dir):
                    os.makedirs(repo_dir)
                pkglist = pulp.util.listdir(pkg_dir)
                for pkg in pkglist:
                    if pkg.endswith(".rpm"):
                        shutil.copy(pkg, os.path.join(repo_dir, os.path.basename(pkg)))
                groups_xml_path = None
                src_repomd_xml = os.path.join(pkg_dir, "repodata/repomd.xml")
                if os.path.isfile(src_repomd_xml):
                    ftypes = pulp.util.get_repomd_filetypes(src_repomd_xml)
                    log.debug("repodata has filetypes of %s" % (ftypes))
                    if "group" in ftypes:
                        g = pulp.util.get_repomd_filetype_path(src_repomd_xml, "group")
                        src_groups = os.path.join(pkg_dir, g)
                        if os.path.isfile(src_groups):
                            shutil.copy(src_groups,
                                os.path.join(repo_dir, os.path.basename(src_groups)))
                            log.debug("Copied groups over to %s" % (repo_dir))
                        groups_xml_path = os.path.join(repo_dir,
                            os.path.basename(src_groups))
                    if "group_gz" in ftypes:
                        g = pulp.util.get_repomd_filetype_path(src_repomd_xml, "group")
                        src_groups = os.path.join(pkg_dir, g)

                pulp.upload.create_repo(repo_dir, groups=groups_xml_path)
        except InvalidPathError:
            log.error("Sync aborted due to invalid source path %s" % (pkg_dir))
            return
        except IOError:
            log.error("Unable to create repo directory %s" % repo_dir)
        except pulp.upload.CreateRepoError:
            log.error("Unable to run createrepo on source path %s" % (repo_dir))
            return
        return repo_dir

class RHNSynchronizer(BaseSynchronizer):
    def sync(self, repo, repo_source):
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

        # Perform the sync
        dest_dir = '%s/%s/' % (self.config.get('paths', 'local_storage'), repo['id'])
        s.syncPackages(channel, savePath=dest_dir)
        s.createRepo(dest_dir)
        s.setParallel(self.config.get('rhn', 'threads'))

        return dest_dir
        
TYPE_CLASSES = {'yum'   : YumSynchronizer,
                'local' : LocalSynchronizer,
                'rhn'   : RHNSynchronizer,}

class InvalidPathError(Exception):
    pass

