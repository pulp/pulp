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
import gzip
import logging
import os
import time
import traceback
from urlparse import urlparse

import yum

# Pulp
from grinder.RepoFetch import YumRepoGrinder
from grinder.RHNSync import RHNSync
from pulp import model
from pulp.api.package import PackageApi
from pulp.api.package_version import PackageVersionApi
from pulp.api.package_group import PackageGroupApi
from pulp.api.package_group_category import PackageGroupCategoryApi
from pulp.pexceptions import PulpException
import pulp.util

log = logging.getLogger('pulp.repo_sync')


def sync(config, repo, repo_source):
    '''
    Synchronizes content for the given RepoSource.

    :param repo: instance of model.Repo; may not be None
    :param repo_source: instance of model.RepoSource; may not be None
    '''
    if not TYPE_CLASSES.has_key(repo_source.type):
        raise PulpException('Could not find synchronizer for repo type [%s]', repo_source.type)

    synchronizer = TYPE_CLASSES[repo_source.type](config)
    repo_dir = synchronizer.sync(repo, repo_source)
    synchronizer.add_packages_from_dir(repo_dir, repo)

class BaseSynchronizer(object):

    def __init__(self, config):
        self.config = config
        self.package_api = PackageApi(config)
        self.package_version_api = PackageVersionApi(config)
        self.package_group_category_api = PackageGroupCategoryApi(config)
        self.package_group_api = PackageGroupApi(config)

    def add_packages_from_dir(self, dir, repo):
        dir_list = os.listdir(dir)
        package_count = 0
        startTime = time.time()
        for fname in dir_list:
            self.import_package(dir + fname, repo)
            package_count = package_count + 1
        endTime = time.time()
        log.debug("Repo: %s read [%s] packages took %s seconds" % 
                (repo['id'], package_count, endTime - startTime))
        # TODO: Parse repomd.xml and lookup name for groups element
        compsfile = None
        compspath = os.path.join(dir, 'repodata/comps.xml')
        if os.path.isfile(compspath):
            compsfile = open(compspath, "r")
        else:
            compspath = os.path.join(dir, 'repodata/comps.xml.gz')
            if os.path.isfile(compspath):
                compsfile = gzip.open(compspath, 'r')
        if compsfile:
            repo['comps_xml_path'] = compspath
            self.import_groups_data(compsfile, repo)
            log.debug("Loaded comps info from %s" % (compspath))

    def import_package(self, pkg_path, repo):
        if (pkg_path.endswith(".rpm")):
            try:
                file_name = os.path.basename(pkg_path)
                info = pulp.util.get_rpm_information(pkg_path)
                if not repo["packages"].has_key(info['name']):
                    repo["packages"][info['name']] = []
                hashtype = "sha256"
                checksum = pulp.util.getFileChecksum(hashtype=hashtype, 
                        filename=pkg_path)
                found = self.package_version_api.packageversion(name=info['name'], 
                        epoch=info['epoch'], version=info['version'], 
                        release=info['release'], arch=info['arch'],filename=file_name, 
                        checksum_type=hashtype, checksum=checksum)
                if found.count() == 1:
                    pv = found[0]
                else:
                    pv = self.package_version_api.create(info['name'], info['epoch'],
                        info['version'], info['release'], info['arch'], info['description'],
                        "sha256", checksum, file_name)
                    for dep in info['requires']:
                        pv.requires.append(dep)
                    for dep in info['provides']:
                        pv.provides.append(dep)
                    self.package_version_api.update(pv)
                #TODO:  Ensure we don't add duplicate pv's to the 'packages' list
                repo['packages'][info['name']].append(pv)
            except Exception, e:
                log.debug("%s" % (traceback.format_exc()))
                log.error("error reading package %s" % (pkg_path))

    def import_groups_data(self, compsfile, repo):
        """
        Reads a comps.xml or comps.xml.gz under repodata from dir
        Loads PackageGroup and Category info our db
        """
        try:
            comps = yum.comps.Comps()
            comps.add(compsfile)
            for c in comps.categories:
                ctg = model.PackageGroupCategory(c.categoryid, c.name,
                    c.description, c.display_order)
                groupids = [grp for grp in c.groups]
                ctg['packagegroupids'].extend(groupids)
                ctg['translated_name'] = c.translated_name
                ctg['translated_description'] = c.translated_description
                repo['packagegroupcategories'][ctg['id']] = ctg
            for g in comps.groups:
                grp = model.PackageGroup(g.groupid, g.name, g.description,
                    g.user_visible, g.display_order, g.default, g.langonly)
                grp.mandatory_package_names.extend(g.mandatory_packages.keys())
                grp.optional_package_names.extend(g.optional_packages.keys())
                grp.default_package_names.extend(g.default_packages.keys())
                grp.conditional_package_names = g.conditional_packages
                grp.translated_name = g.translated_name
                grp.translated_description = g.translated_description
                repo['packagegroups'][grp['id']] = grp
        except yum.Errors.CompsException:
            log.error("Unable to parse comps info for %s" % (compspath))
            return False
        return True
    
class YumSynchronizer(BaseSynchronizer):
    def sync(self, repo, repo_source):
        yfetch = YumRepoGrinder(repo['id'], repo_source.url.encode('ascii', 'ignore'), 1)
        yfetch.fetchYumRepo(self.config.get('paths', 'local_storage'))
        repo_dir = "%s/%s/" % (self.config.get('paths', 'local_storage'), repo['id'])
        return repo_dir

class LocalSynchronizer(BaseSynchronizer):
    def sync(self, repo, repo_source):
        local_url = repo_source.url
        if (not local_url.endswith('/')):
            local_url = local_url + '/'
        parts = urlparse(local_url)
        return parts.path

class RHNSynchronizer(BaseSynchronizer):
    def sync(self, repo, repo_source):
        # Parse the repo source for necessary pieces
        # Expected format:   <server>/<channel>
        pieces = repo_source.url.split('/')
        if len(pieces) < 2:
            raise PulpException('Feed format for RHN type must be <server>/<channel>. Feed: %s',
                                repo_source.url)

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

