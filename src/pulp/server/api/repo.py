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
from datetime import datetime
import logging
import gzip
from itertools import chain
from optparse import OptionParser
import os
import shutil
import traceback
from urlparse import urlparse

# Pulp
from pulp.server import comps_util
from pulp.server import config
from pulp.server import crontab
from pulp.server import upload
from pulp.server.api import repo_sync
from pulp.server.api.base import BaseApi
from pulp.server.api.fetch_listings import CDNConnection
from pulp.server.api.errata import ErrataApi
from pulp.server.api.keystore import KeyStore
from pulp.server.api.package import PackageApi
from pulp.server.auditing import audit
from pulp.server.db import model
from pulp.server.db.connection import get_object_db
from pulp.server.event.dispatcher import event
import pulp.server.logs
from pulp.server.pexceptions import PulpException
import pulp.server.util
from pulp.server.api.fetch_listings import CDNConnection
from pulp.server.agent import Agent
from pulp.server.api.distribution import DistributionApi
log = logging.getLogger(__name__)

repo_fields = model.Repo(None, None, None).keys()

class RepoApi(BaseApi):
    """
    API for create/delete/syncing of Repo objects
    """

    def __init__(self):
        BaseApi.__init__(self)
        self.packageapi = PackageApi()
        self.errataapi = ErrataApi()
        self.distroapi = DistributionApi()
        self.localStoragePath = config.config.get('paths', 'local_storage')
        self.published_path = os.path.join(self.localStoragePath, "published", "repos")
        self.distro_path = os.path.join(self.localStoragePath, "published", "ks")

    @property
    def _indexes(self):
        return ["packages", "packagegroups", "packagegroupcategories"]

    @property
    def _unique_indexes(self):
        return ["id"]

    def _getcollection(self):
        return get_object_db('repos',
                             self._unique_indexes,
                             self._indexes)

    def _validate_schedule(self, sync_schedule):
        '''
        Verifies the sync schedule is in the correct cron syntax, throwing an exception if
        it is not.
        '''
        if sync_schedule:
            item = crontab.CronItem(sync_schedule + ' null') # CronItem expects a command
            if not item.is_valid():
                raise PulpException('Invalid sync schedule specified [%s]' % sync_schedule)

    def _get_existing_repo(self, id):
        """
        Protected helper function to look up a repository by id and raise a
        PulpException if it is not found.
        """
        repo = self.repository(id)
        if repo is None:
            raise PulpException("No Repo with id: %s found" % id)
        return repo

    @audit()
    def clean(self):
        """
        Delete all the Repo objects in the database and remove associated
        files from filesystem.  WARNING: Destructive
        """
        found = self.repositories(fields=["id"])
        for r in found:
            self.delete(r["id"])

    @event(subject='repo.created')
    @audit(params=['id', 'name', 'arch', 'feed'])
    def create(self, id, name, arch, feed=None, symlinks=False, sync_schedule=None,
               cert_data=None, groupid=None, relative_path=None, gpgkeys=[]):
        """
        Create a new Repository object and return it
        """
        repo = self.repository(id)
        if repo is not None:
            raise PulpException("A Repo with id %s already exists" % id)
        self._validate_schedule(sync_schedule)

        r = model.Repo(id, name, arch, feed)
        r['sync_schedule'] = sync_schedule
        r['use_symlinks'] = symlinks
        if cert_data:
            cert_files = self._write_certs_to_disk(id, cert_data)
            for key, value in cert_files.items():
                r[key] = value
        if groupid:
            for gid in groupid:
                r['groupid'].append(gid)

        if relative_path is None or relative_path == "":
            if r['source'] is not None :
                if r['source']['type'] == "local":
                    r['relative_path'] = r['id']
                else:
                    # For none product repos, default to repoid
                    url_parse = urlparse(str(r['source']["url"]))
                    r['relative_path'] = url_parse.path or r['id']
            else:
                r['relative_path'] = r['id']
                # There is no repo source, allow package uploads
                r['allow_upload']  = 1
        else:
            r['relative_path'] = relative_path
        # Remove leading "/", they will interfere with symlink
        # operations for publishing a repository
        r['relative_path'] = r['relative_path'].strip('/')
        r['repomd_xml_path'] = \
                os.path.join(pulp.server.util.top_repos_location(),
                        r['relative_path'], 'repodata/repomd.xml')
        if gpgkeys:
            root = pulp.server.util.top_repos_location()
            path = r['relative_path']
            ks = KeyStore(path)
            added = ks.add(gpgkeys)
        self.insert(r)
        if sync_schedule:
            repo_sync.update_schedule(r)
        default_to_publish = \
            config.config.getboolean('repos', 'default_to_published')
        self.publish(r["id"], default_to_publish)
        # refresh repo object from mongo
        r = self.repository(r["id"])
        return r

    @audit(params=['id', 'state'])
    def publish(self, id, state):
        """
        Controls if we publish this repository through Apache.  True means the
        repository will be published, False means it will not be.
        @type id: str
        @param id: repository id
        @type state: boolean
        @param state: True is enable publish, False is disable publish
        """
        repo = self._get_existing_repo(id)
        repo['publish'] = state
        self.update(repo)
        repo = self._get_existing_repo(id)
        try:
            if repo['publish']:
                self._create_published_link(repo)
                if repo['distributionid']:
                    self._create_ks_link(repo)
            else:
                self._delete_published_link(repo)
                if repo['distributionid']:
                    self._delete_ks_link(repo)
            self.update_subscribed(id)
        except Exception, e:
            log.error(e)
            return False
        return True

    def _create_published_link(self, repo):
        if not os.path.isdir(self.published_path):
            os.mkdir(self.published_path)
        source_path = os.path.join(pulp.server.util.top_repos_location(), 
                repo["relative_path"])
        link_path = os.path.join(self.published_path, repo["relative_path"])
        pulp.server.util.create_symlinks(source_path, link_path)

    def _delete_published_link(self, repo):
        if repo["relative_path"]:
            link_path = os.path.join(self.published_path, repo["relative_path"])
            if os.path.lexists(link_path):
                # need to use lexists so we will return True even for broken links
                os.unlink(link_path)

    def _clone(self, id, clone_id, clone_name, feed='parent', groupid=None, relative_path=None, progress_callback=None):
        repo = self.repository(id)
        if repo is None:
            raise PulpException("A Repo with id %s does not exist" % id)
        cloned_repo = self.repository(clone_id)
        if cloned_repo is not None:
            raise PulpException("A Repo with id %s exists. Choose a different id." % clone_id)   

        REPOS_LOCATION = "%s/%s/" % (config.config.get('paths', 'local_storage'), "repos")
        parent_relative_path = "local:file://" + REPOS_LOCATION + repo["relative_path"]
        log.info("Creating repo [%s] cloned from [%s]" % (id, repo))
        self.create(clone_id, clone_name, repo['arch'], feed=parent_relative_path, groupid=groupid, 
                        relative_path=relative_path)
        """
        Sync from parent repo
        """
        try:
            self._sync(clone_id)
        except:
            raise PulpException("Repo cloning of [%s] failed" % id)
        
        """
        Update feed type for cloned repo if "origin" or "feedless"        
        """
        cloned_repo = self.repository(clone_id)
        if feed == "origin":
            cloned_repo['source'] = repo['source']
        elif feed == "none":
            cloned_repo['source'] = None
        self.update(cloned_repo)    
            
        """
        Update clone_ids for parent repo
        """            
        clone_ids = repo['clone_ids']
        clone_ids.append(clone_id)
        repo['clone_ids'] = clone_ids
        self.update(repo)   
        
        """
        Update gpg keys from parent repo
        """
        keylist = []
        key_paths = self.listkeys(id)
        for key_path in key_paths:
            key_path = REPOS_LOCATION + key_path
            f = open(key_path)
            fn = os.path.basename(key_path)
            content = f.read()
            keylist.append((fn, content))
            f.close()
        self.addkeys(clone_id, keylist)
        
    @audit()
    def clone(self, id, clone_id, clone_name, feed='parent', groupid=None, relative_path=None, progress_callback=None, timeout=None):
        """
        Run a repo clone asynchronously.
        """
        return self.run_async(self._clone,
                              [id, clone_id, clone_name, feed, groupid, relative_path],
                              {'progress_callback': progress_callback},
                              timeout=timeout)
 
    def _write_certs_to_disk(self, repoid, cert_data):
        CONTENT_CERTS_PATH = config.config.get("repos", "content_cert_location")
        cert_dir = os.path.join(CONTENT_CERTS_PATH, repoid)

        if not os.path.exists(cert_dir):
            os.makedirs(cert_dir)
        cert_files = {}
        for key, value in cert_data.items():
            fname = os.path.join(cert_dir, repoid + "." + key)
            try:
                log.error("storing file %s" % fname)
                f = open(fname, 'w')
                f.write(value)
                f.close()
                cert_files[key] = str(fname)
            except:
                raise PulpException("Error storing certificate file %s " % key)
        return cert_files

    @audit(params=['groupid', 'content_set'])
    def create_product_repo(self, content_set, cert_data, groupid=None):
        """
         Creates a repo associated to a product. Usually through an event raised
         from candlepin
         @param groupid: A product the candidate repo should be associated with.
         @type groupid: str
         @param content_set: a dict of content set labels and relative urls
         @type content_set: dict(<label> : <relative_url>,)
         @param cert_data: a dictionary of ca_cert, cert and key for this product
         @type cert_data: dict(ca : <ca_cert>, cert: <ent_cert>, key : <cert_key>)
        """
        if not cert_data or not content_set:
            # Nothing further can be done, exit
            return
        cert_files = self._write_certs_to_disk(groupid, cert_data)
        CDN_URL = config.config.get("repos", "content_url")
        CDN_HOST = urlparse(CDN_URL).hostname
        serv = CDNConnection(CDN_HOST, cacert=cert_files['ca'],
                                     cert=cert_files['cert'], key=cert_files['key'])
        serv.connect()
        repo_info = serv.fetch_urls(content_set)
        for label, uri in repo_info.items():
            try:
                repo = self.create(label, label, arch=label.split("-")[-1],
                                   feed="yum:" + CDN_URL + '/' + uri,
                                   cert_data=cert_data, groupid=groupid,
                                   relative_path=uri)
                repo['release'] = label.split("-")[-2]
                self.update(repo)
            except:
                log.error("Error creating repo %s for product %s" % (label, groupid))
                continue

        serv.disconnect()
        
    @audit(params=['groupid', 'content_set'])
    def update_product_repo(self, content_set, cert_data, groupid=None):
        """
         Creates a repo associated to a product. Usually through an event raised
         from candlepin
         @param groupid: A product the candidate repo should be associated with.
         @type groupid: str
         @param content_set: a dict of content set labels and relative urls
         @type content_set: dict(<label> : <relative_url>,)
         @param cert_data: a dictionary of ca_cert, cert and key for this product
         @type cert_data: dict(ca : <ca_cert>, cert: <ent_cert>, key : <cert_key>)
        """
        if not cert_data or not content_set:
            # Nothing further can be done, exit
            return
        cert_files = self._write_certs_to_disk(groupid, cert_data)
        CDN_URL = config.config.get("repos", "content_url")
        CDN_HOST = urlparse(CDN_URL).hostname
        serv = CDNConnection(CDN_HOST, cacert=cert_files['ca'],
                                     cert=cert_files['cert'], key=cert_files['key'])
        serv.connect()
        repo_info = serv.fetch_urls(content_set)

        for label, uri in repo_info.items():
            try:
                repo = self._get_existing_repo(label)
                repo['feed'] = "yum:" + CDN_URL + '/' + uri
                if cert_data:
                    cert_files = self._write_certs_to_disk(label, cert_data)
                    for key, value in cert_files.items():
                        repo[key] = value
                repo['arch'] = label.split("-")[-1]
                repo['relative_path'] = uri
                repo['groupid'] = groupid
                self.update(repo)
            except PulpException, pe:
                log.error(pe)
                continue
            except:
                log.error("Error updating repo %s for product %s" % (label, groupid))
                continue

        serv.disconnect()
        
    def delete_product_repo(self, groupid=None):
        """
         delete repos associated to a product. Usually through an event raised
         from candlepin
         @param groupid: A product the candidate repo should be associated with.
         @type groupid: str
        """
        if not groupid:
            # Nothing further can be done, exit
            return
        
        repos = self.repositories(spec={"groupid" : groupid})
        for repo in repos:
            try:
                self.delete(repo['id'])
            except:
                log.error("Error deleting repo %s for product %s" % (repo['id'], groupid))
                continue
    
    @event(subject='repo.deleted')
    @audit()
    def delete(self, id):
        repo = self._get_existing_repo(id)
        log.info("Delete API call invoked %s" % repo)
        #update feed of clones of this repo to None unless they point to origin feed
        for clone_id in repo['clone_ids']:
            cloned_repo = self._get_existing_repo(clone_id)
            if cloned_repo['source'] != repo['source']:
                cloned_repo['source'] = None
                self.update(cloned_repo)
        
        #update clone_ids of its parent repo        
        parent_repos = self.repositories({'clone_ids' : id})
        if len(parent_repos) == 1:
            parent_repo = parent_repos[0]
            clone_ids = parent_repo['clone_ids']
            clone_ids.remove(id)
            parent_repo['clone_ids'] = clone_ids
            self.update(parent_repo)

        self._delete_published_link(repo)
        repo_sync.delete_schedule(repo)
        
        #remove any distributions
        for distroid in repo['distributionid']:
            self.remove_distribution(repo['id'], distroid)
        #unsubscribe consumers from this repo
        #importing here to bypass circular imports
        from pulp.server.api.consumer import ConsumerApi 
        capi = ConsumerApi()
        bound_consumers = capi.findsubscribed(repo['id'])
        for consumer in bound_consumers:
            try:
                log.info("Unsubscribe repoid %s from consumer %s" % (repo['id'], consumer['id']))
                capi.unbind(consumer['id'], repo['id'])
            except:
                log.error("failed to unbind repoid %s from consumer %s moving on.." % \
                          (repo['id'], consumer['id']))
                continue
        
        repo_location = "%s/%s" % (config.config.get('paths', 'local_storage'), "repos")
        #delete any data associated to this repo
        for field in ['relative_path', 'cert', 'key', 'ca']:
            if field == 'relative_path' and repo[field]:
                fpath = os.path.join(repo_location, repo[field])
            else:
                fpath =  repo[field]
            if fpath and os.path.exists(fpath):
                try:
                    if os.path.isfile(fpath):
                        os.remove(fpath)
                    else: # os.path.isdir(fpath):
                        shutil.rmtree(fpath)
                    log.info("removing repo files .... %s" % fpath)
                except:
                    #file removal failed
                    raise
                    log.error("Unable to cleanup file %s " % fpath)
                    continue
        self.objectdb.remove({'id' : id}, safe=True)
        
    @audit()
    def update(self, repo_data):
        repo = self._get_existing_repo(repo_data['id'])
        # make sure we're only updating the fields in the model
        for field in repo_fields:
            #default to the existing value if the field isn't in the data
            repo[field] = repo_data.get(field, repo[field])
        if repo_data.has_key('feed') and repo_data['feed']:
            repo['source'] = model.RepoSource(repo_data['feed'])
        self._validate_schedule(repo['sync_schedule'])

        self.objectdb.save(repo, safe=True)

        if repo['sync_schedule']:
            repo_sync.update_schedule(repo)
        else:
            repo_sync.delete_schedule(repo)

        return repo

    def repositories(self, spec=None, fields=None):
        """
        Return a list of Repositories
        """
        return list(self.objectdb.find(spec=spec, fields=fields))

    def repository(self, id, fields=None):
        """
        Return a single Repository object
        """
        repos = self.repositories({'id': id}, fields)
        if not repos:
            return None
        return repos[0]

    def packages(self, id, name=None):
        """
        Return list of Package objects in this Repo
        @type id: str
        @param id: repository id
        @type name: str
        @param name: package name
        @rtype: list
        @return: package objects belonging to this repository
        """
        repo = self._get_existing_repo(id)
        repo_packages = repo['packages']
        packages = [self.packageapi.package(p) for p in repo_packages.keys()]
        if name is not None:
            packages = [p for p in packages if p['name'].find(name) >= 0]
        return packages

    def package_count(self, id):
        """
        Return the number of packages in a repository.
        @type id: str
        @param id: repository id
        @rtype: int
        @return: the number of package in the repository corresponding to id
        """
        return self.repository(id, fields=["package_count"])['package_count']

    def get_package(self, id, name):
        """
        Return matching Package object in this Repo
        """
        packages = self.packages(id, name)
        if not packages:
            return None
        return packages[0]
    
    def get_package_by_nvrea(self, id, name, version, release, epoch, arch):
        """
         CHeck if package exists or not in this repo for given nvrea
        """
        log.error('looking up pkg [%s] in repo [%s]' % (name, id))
        repo = self._get_existing_repo(id)
        packages = repo['packages']
        for p in packages.values():
            if (name, version, release, epoch, arch) == \
                (p['name'], p['version'], p['release'], p['epoch'], p['arch']):
                pkg_repo_path = pulp.server.util.get_repo_package_path(
                repo['relative_path'], p['filename'])
                if os.path.exists(pkg_repo_path):
                    return p
        return {}

    @audit()
    def add_package(self, repoid, packageid):
        """
        Adds the passed in package to this repo
        """
        repo = self._get_existing_repo(repoid)
        package = self.packageapi.package(packageid)
        if package is None:
            raise PulpException("No Package with id: %s found" % packageid)
        # TODO:  We might want to restrict Packages we add to only
        #        allow 1 NEVRA per repo and require filename to be unique
        self._add_package(repo, package)
        self.objectdb.save(repo, safe=True)

    def _add_package(self, repo, p):
        """
        Responsible for properly associating a Package to a Repo
        """
        packages = repo['packages']
        if p['id'] in packages:
            # No need to update repo, this Package is already under this repo
            return
        packages[p['id']] = p
        # increment the package count
        repo['package_count'] = repo['package_count'] + 1 

    @audit()
    def remove_package(self, repoid, p):
        """Note: This method does not update repo metadata.
        It is assumed metadata has already been updated.
        """
        repo = self._get_existing_repo(repoid)
        # this won't fail even if the package is not in the repo's packages
        repo['packages'].pop(p['id'], None)
        repo['package_count'] = repo['package_count'] - 1
        self.objectdb.save(repo, safe=True)
        # Remove package from repo location on file system
        pkg_repo_path = pulp.server.util.get_repo_package_path(
                repo['relative_path'], p["filename"])
        if os.path.exists(pkg_repo_path):
            log.debug("Delete package %s at %s" % (p, pkg_repo_path))
            os.remove(pkg_repo_path)

        repos_with_pkg = self.find_repos_by_package(p["id"])
        if len(repos_with_pkg) == 0:
            self.packageapi.delete(p["id"])
            pkg_packages_path = pulp.server.util.get_shared_package_path(
                    p["name"], p["version"], p["release"], p["arch"],
                    p["filename"], p["checksum"])
            if os.path.exists(pkg_packages_path):
                log.debug("Delete package %s at %s" % (p, pkg_packages_path))
                os.remove(pkg_packages_path)

    def find_repos_by_package(self, pkgid):
        """
        Return repos that contain passed in package id
        @param pkgid: package id
        """
        key = "packages.%s" % pkgid
        found = list(self.objectdb.find({key: {"$exists": True}}, fields=["id"]))
        return [r["id"] for r in found]

    def errata(self, id, types=()):
        """
         Look up all applicable errata for a given repo id
        """
        repo = self._get_existing_repo(id)
        errata = repo['errata']
        if not errata:
            return []
        if types:
            try:
                return [item for type in types for item in errata[type]]
            except KeyError, ke:
                log.debug("Invalid errata type requested :[%s]" % (ke))
                raise PulpException("Invalid errata type requested :[%s]" % (ke))
        return list(chain.from_iterable(errata.values()))

    @audit()
    def add_erratum(self, repoid, erratumid):
        """
        Adds in erratum to this repo
        """
        repo = self._get_existing_repo(repoid)
        self._add_erratum(repo, erratumid)
        self.objectdb.save(repo, safe=True)

    def add_errata(self, repoid, errataids=()):
        """
         Adds a list of errata to this repo
        """
        repo = self._get_existing_repo(repoid)
        for erratumid in errataids:
            self._add_erratum(repo, erratumid)
        self.objectdb.save(repo, safe=True)

    def _add_erratum(self, repo, erratumid):
        """
        Responsible for properly associating an Erratum to a Repo
        """
        erratum = self.errataapi.erratum(erratumid)
        if erratum is None:
            raise PulpException("No Erratum with id: %s found" % erratumid)

        errata = repo['errata']
        try:
            if erratum['id'] in errata[erratum['type']]:
                #errata already in repo, continue
                return
        except KeyError:
            errata[erratum['type']] = []

        errata[erratum['type']].append(erratum['id'])

    @audit()
    def delete_erratum(self, repoid, erratumid):
        """
        delete erratum from this repo
        """
        repo = self._get_existing_repo(repoid)
        self._delete_erratum(repo, erratumid)
        self.objectdb.save(repo, safe=True)

    def delete_errata(self, repoid, errataids):
        """
        delete list of errata from this repo
        """
        repo = self._get_existing_repo(repoid)
        for erratumid in errataids:
            self._delete_erratum(repo, erratumid)
        self.objectdb.save(repo, safe=True)

    def _delete_erratum(self, repo, erratumid):
        """
        Responsible for properly removing an Erratum from a Repo
        """
        erratum = self.errataapi.erratum(erratumid)
        if erratum is None:
            raise PulpException("No Erratum with id: %s found" % erratumid)
        try:
            curr_errata = repo['errata'][erratum['type']]
            if erratum['id'] not in curr_errata:
                log.debug("Erratum %s Not in repo. Nothing to delete" % erratum['id'])
                return
            del curr_errata[curr_errata.index(erratum['id'])]
            repos = self.find_repos_by_errata(erratum['id'])
            if repo["id"] in repos and len(repos) == 1:
                self.errataapi.delete(erratum['id'])
            else:
                log.debug("Not deleting %s since it is referenced by these repos: %s" % (erratum["id"], repos))
        except Exception, e:
            raise PulpException("Erratum %s delete failed due to Error: %s" % (erratum['id'], e))

    def find_repos_by_errata(self, errata_id):
        """
        Return repos that contain passed in errata_id
        """
        ret_val = []
        repos = self.repositories(fields=["id", "errata"])
        for r in repos:
            for e_type in r["errata"]:
                if errata_id in r["errata"][e_type]:
                    ret_val.append(r["id"])
                    break
        return ret_val

    @audit(params=['repoid', 'group_id', 'group_name'])
    def create_packagegroup(self, repoid, group_id, group_name, description):
        """
        Creates a new packagegroup saved in the referenced repo
        @param repoid:
        @param group_id:
        @param group_name:
        @param description:
        @return packagegroup object
        """
        repo = self._get_existing_repo(repoid)
        if not repo:
            raise PulpException("Unable to find repository [%s]" % (repoid))
        if group_id in repo['packagegroups']:
            raise PulpException("Package group %s already exists in repo %s" %
                                (group_id, repoid))
        group = model.PackageGroup(group_id, group_name, description)
        repo["packagegroups"][group_id] = group
        self.objectdb.save(repo, safe=True)
        self._update_groups_metadata(repo["id"])
        return group

    @audit()
    def delete_packagegroup(self, repoid, groupid):
        """
        Remove a packagegroup from a repo
        @param repoid: repo id
        @param groupid: package group id
        """
        repo = self._get_existing_repo(repoid)
        if groupid not in repo['packagegroups']:
            raise PulpException("Group [%s] does not exist in repo [%s]" % (groupid, repo["id"]))
        if repo['packagegroups'][groupid]["immutable"]:
            raise PulpException("Changes to immutable groups are not supported: %s" % (groupid))
        del repo['packagegroups'][groupid]
        self.objectdb.save(repo, safe=True)
        self._update_groups_metadata(repo["id"])

    @audit()
    def update_packagegroup(self, repoid, pg):
        """
        Save the passed in PackageGroup to this repo
        @param repoid: repo id
        @param pg: packagegroup
        """
        repo = self._get_existing_repo(repoid)
        pg_id = pg['id']
        if pg_id in repo['packagegroups']:
            if repo["packagegroups"][pg_id]["immutable"]:
                raise PulpException("Changes to immutable groups are not supported: %s" % (pg["id"]))
        repo['packagegroups'][pg_id] = pg
        self.objectdb.save(repo, safe=True)
        self._update_groups_metadata(repo["id"])

    @audit()
    def update_packagegroups(self, repoid, pglist):
        """
        Save the list of passed in PackageGroup objects to this repo
        @param repoid: repo id
        @param pglist: list of packagegroups
        """
        repo = self._get_existing_repo(repoid)
        for item in pglist:
            if item['id'] in repo['packagegroups']:
                if repo['packagegroups'][item["id"]]["immutable"]:
                    raise PulpException("Changes to immutable groups are not supported: %s" % (item["id"]))
            repo['packagegroups'][item['id']] = item
        self.objectdb.save(repo, safe=True)
        self._update_groups_metadata(repo["id"])

    def packagegroups(self, id):
        """
        Return list of PackageGroup objects in this Repo
        @param id: repo id
        @return: packagegroup or None
        """
        repo = self._get_existing_repo(id)
        return repo['packagegroups']

    def packagegroup(self, repoid, groupid):
        """
        Return a PackageGroup from this Repo
        @param repoid: repo id
        @param groupid: packagegroup id
        @return: packagegroup or None
        """
        repo = self._get_existing_repo(repoid)
        return repo['packagegroups'].get(groupid, None)


    @audit()
    def add_packages_to_group(self, repoid, groupid, pkg_names=[], 
            gtype="default", requires=None):
        """
        @param repoid: repository id
        @param groupid: group id
        @param pkg_names: package names
        @param gtype: OPTIONAL type of package group,
            example "mandatory", "default", "optional", "conditional"
        @param requires: represents the 'requires' field for a 
            conditonal package group entry only needed when 
            gtype is 'conditional'
        We are not restricting package names to packages in the repo.  
        It is possible and acceptable for a package group to refer to packages which
        are not known to the repo or pulp.  The package group will be used on 
        the client and will have access to all repos the client can see.
        """

        repo = self._get_existing_repo(repoid)
        if groupid not in repo['packagegroups']:
            raise PulpException("No PackageGroup with id: %s exists in repo %s"
                                % (groupid, repoid))
        group = repo["packagegroups"][groupid]
        if group["immutable"]:
            raise PulpException("Changes to immutable groups are not supported: %s" % (group["id"]))

        for pkg_name in pkg_names:
            if gtype == "mandatory":
                if pkg_name not in group["mandatory_package_names"]:
                    group["mandatory_package_names"].append(pkg_name)
            elif gtype == "conditional":
                if not requires:
                    raise PulpException("Parameter 'requires' has not been set, it is required by conditional group types")
                group["conditional_package_names"][pkg_name] = requires
            elif gtype == "optional":
                if pkg_name not in group["optional_package_names"]:
                    group["optional_package_names"].append(pkg_name)
            else:
                if pkg_name not in group["default_package_names"]:
                    group["default_package_names"].append(pkg_name)
        self.update(repo)
        self._update_groups_metadata(repo["id"])

    @audit()
    def delete_package_from_group(self, repoid, groupid, pkg_name, gtype="default"):
        """
        @param repoid: repository id
        @param groupid: group id
        @param pkg_name: package name
        @param gtype: OPTIONAL type of package group,
            example "mandatory", "default", "optional"
        """
        repo = self._get_existing_repo(repoid)
        if groupid not in repo['packagegroups']:
            raise PulpException("No PackageGroup with id: %s exists in repo %s"
                                % (groupid, repoid))
        group = repo["packagegroups"][groupid]
        if group["immutable"]:
            raise PulpException("Changes to immutable groups are not supported: %s" % (group["id"]))

        if gtype == "mandatory":
            if pkg_name in group["mandatory_package_names"]:
                group["mandatory_package_names"].remove(pkg_name)
            else:
                raise PulpException("Package %s not present in package group" % (pkg_name))
        elif gtype == "conditional":
            if pkg_name in group["conditional_package_names"]:
                del group["conditional_package_names"][pkg_name]
            else:
                raise PulpException("Package %s not present in conditional package group" % (pkg_name))
        elif gtype == "optional":
            if pkg_name in group["optional_package_names"]:
                group["optional_package_names"].remove(pkg_name)
            else:
                raise PulpException("Package %s not present in package group" % (pkg_name))
        else:
            if pkg_name in group["default_package_names"]:
                group["default_package_names"].remove(pkg_name)
            else:
                raise PulpException("Package %s not present in package group" % (pkg_name))

        self.objectdb.save(repo, safe=True)
        self._update_groups_metadata(repo["id"])

    @audit(params=['repoid', 'cat_id', 'cat_name'])
    def create_packagegroupcategory(self, repoid, cat_id, cat_name, description):
        """
        Creates a new packagegroupcategory saved in the referenced repo
        @param repoid:
        @param cat_id:
        @param cat_name:
        @param description:
        @return packagegroupcategory object
        """
        repo = self._get_existing_repo(repoid)
        if cat_id in repo['packagegroupcategories']:
            raise PulpException("Package group category %s already exists in repo %s" %
                                (cat_id, repoid))
        cat = model.PackageGroupCategory(cat_id, cat_name, description)
        repo["packagegroupcategories"][cat_id] = cat
        self.objectdb.save(repo, safe=True)
        self._update_groups_metadata(repo["id"])
        return cat

    @audit()
    def delete_packagegroupcategory(self, repoid, categoryid):
        """
        Remove a packagegroupcategory from a repo
        """
        repo = self._get_existing_repo(repoid)
        if categoryid not in repo['packagegroupcategories']:
            return
        if repo['packagegroupcategories'][categoryid]["immutable"]:
            raise PulpException("Changes to immutable categories are not supported: %s" % (categoryid))
        del repo['packagegroupcategories'][categoryid]
        self.objectdb.save(repo, safe=True)
        self._update_groups_metadata(repo["id"])

    @audit()
    def delete_packagegroup_from_category(self, repoid, categoryid, groupid):
        repo = self._get_existing_repo(repoid)
        if categoryid in repo['packagegroupcategories']:
            if repo["packagegroupcategories"][categoryid]["immutable"]:
                raise PulpException(
                        "Changes to immutable categories are not supported: %s" \
                                % (categoryid))
            repo['packagegroupcategories'].remove(categoryid)

        self.update(repo)
        self._update_groups_metadata(repo["id"])

    @audit()
    def add_packagegroup_to_category(self, repoid, categoryid, groupid):
        repo = self._get_existing_repo(repoid)
        if categoryid in repo['packagegroupcategories']:
            if repo["packagegroupcategories"][categoryid]["immutable"]:
                raise PulpException(
                        "Changes to immutable categories are not supported: %s" \
                                % (categoryid))
        repo['packagegroupcategories'][categoryid].append(groupid)
        self.update(repo)
        self._update_groups_metadata(repo["id"])

    @audit()
    def update_packagegroupcategory(self, repoid, pgc):
        """
        Save the passed in PackageGroupCategory to this repo
        """
        repo = self._get_existing_repo(repoid)
        if pgc['id'] in repo['packagegroupcategories']:
            if repo["packagegroupcategories"][pgc["id"]]["immutable"]:
                raise PulpException("Changes to immutable categories are not supported: %s" % (pgc["id"]))
        repo['packagegroupcategories'][pgc['id']] = pgc
        self.objectdb.save(repo, safe=True)
        self._update_groups_metadata(repo["id"])

    @audit()
    def update_packagegroupcategories(self, repoid, pgclist):
        """
        Save the list of passed in PackageGroupCategory objects to this repo
        """
        repo = self._get_existing_repo(repoid)
        for item in pgclist:
            if item['id'] in repo['packagegroupcategories']:
                if repo["packagegroupcategories"][item["id"]]["immutable"]:
                    raise PulpException("Changes to immutable categories are not supported: %s" % item["id"])
            repo['packagegroupcategories'][item['id']] = item
        self.objectdb.save(repo, safe=True)
        self._update_groups_metadata(repo["id"])

    def packagegroupcategories(self, id):
        """
        Return list of PackageGroupCategory objects in this Repo
        """
        repo = self._get_existing_repo(id)
        return repo['packagegroupcategories']

    def packagegroupcategory(self, repoid, categoryid):
        """
        Return a PackageGroupCategory object from this Repo
        """
        repo = self._get_existing_repo(repoid)
        return repo['packagegroupcategories'].get(categoryid, None)

    def _update_groups_metadata(self, repoid):
        """
        Updates the groups metadata (example: comps.xml) for a given repo
        @param repoid: repo id
        @return: True if metadata was successfully updated, otherwise False
        """
        repo = self._get_existing_repo(repoid)
        try:
            # If the repomd file is not valid, or if we are missingg
            # a group metadata file, no point in continuing. 
            if not os.path.exists(repo["repomd_xml_path"]):
                log.warn("Skipping update of groups metadata since missing repomd file: '%s'" %
                          (repo["repomd_xml_path"]))
                return False
            xml = comps_util.form_comps_xml(repo['packagegroupcategories'],
                repo['packagegroups'])
            if repo["group_xml_path"] == "":
                repo["group_xml_path"] = os.path.dirname(repo["repomd_xml_path"])
                repo["group_xml_path"] = os.path.join(os.path.dirname(repo["repomd_xml_path"]),
                                                      "comps.xml")
                self.update(repo)
            f = open(repo["group_xml_path"], "w")
            f.write(xml.encode("utf-8"))
            f.close()
            if repo["group_gz_xml_path"]:
                gz = gzip.open(repo["group_gz_xml_path"], "wb")
                gz.write(xml.encode("utf-8"))
                gz.close()
            return comps_util.update_repomd_xml_file(repo["repomd_xml_path"],
                repo["group_xml_path"], repo["group_gz_xml_path"])
        except Exception, e:
            log.warn("_update_groups_metadata exception caught: %s" % (e))
            log.warn("Traceback: %s" % (traceback.format_exc()))
            return False

    def _sync(self, id, progress_callback=None):
        """
        Sync a repo from the URL contained in the feed
        """
        repo = self._get_existing_repo(id)
        repo_source = repo['source']
        if not repo_source:
            raise PulpException("This repo is not setup for sync. Please add packages using upload.")
        sync_packages, sync_errataids = repo_sync.sync(repo, repo_source, progress_callback)
        log.info("Sync returned %s packages, %s errata" % (len(sync_packages),
            len(sync_errataids)))
        # We need to update the repo object in Mongo to account for
        # package_group info added in sync call
        self.update(repo)
        # Remove packages that are no longer in source repo
        for pid in repo["packages"]:
            if pid not in sync_packages and \
                repo["packages"][pid]["repo_defined"]:
                # Only remove packages that are defined by the repo
                # Example: don't delete uploaded packages
                log.info("Removing package <%s> from repo <%s>" % (repo["packages"][pid], repo["id"]))
                self.remove_package(repo["id"], repo["packages"][pid])
        # Refresh repo object since we may have deleted some packages
        repo = self._get_existing_repo(id)
        for p in sync_packages.values():
            self._add_package(repo, p)
        # Update repo for package additions
        self.update(repo)
        # Determine removed errata
        log.info("Examining %s errata from repo %s" % (len(self.errata(id)), id))
        for eid in self.errata(id):
            if eid not in sync_errataids:
                log.info("Removing errata %s from repo %s" % (eid, id))
                self.delete_erratum(id, eid)
        # Add in all errata, existing errata will be skipped
        repo = self._get_existing_repo(id) #repo object must be refreshed
        for eid in sync_errataids:
            self._add_erratum(repo, eid)
        repo['last_sync'] = datetime.now()
        self.update(repo)

    @audit()
    def sync(self, id, progress_callback=None, timeout=None):
        """
        Run a repo sync asynchronously.
        """
        return self.run_async(self._sync,
                              [id],
                              {'progress_callback': progress_callback},
                              timeout=timeout)

    def list_syncs(self, id):
        """
        List all the syncs for a given repository.
        """
        return [task
                for task in self.find_async(method='_sync')
                if id in task.args]


    @audit(params=['id', 'pkginfo'])
    def upload(self, id, pkginfo, pkgstream):
        """
        Store the uploaded package and associate to this repo
        """
        repo = self._get_existing_repo(id)
        if not repo['allow_upload']:
            raise PulpException('Package Uploads are not allowed to Repo %s' % repo['id'])
        pkg_upload = upload.PackageUpload(repo, pkginfo, pkgstream)
        pkg, repo = pkg_upload.upload()
        self._add_package(repo, pkg)
        self.objectdb.save(repo, safe=True)
        log.info("Upload success %s %s" % (pkg['id'], repo['id']))
        return True

    @audit(params=['id', 'keylist'])
    def addkeys(self, id, keylist):
        repo = self._get_existing_repo(id)
        path = repo['relative_path']
        ks = KeyStore(path)
        added = ks.add(keylist)
        log.info('repository (%s), added keys: %s', id, added)
        self.update_subscribed(id)
        return added

    @audit(params=['id', 'keylist'])
    def rmkeys(self, id, keylist):
        repo = self._get_existing_repo(id)
        path = repo['relative_path']
        ks = KeyStore(path)
        deleted = ks.delete(keylist)
        log.info('repository (%s), delete keys: %s', id, deleted)
        self.update_subscribed(id)
        return deleted

    def listkeys(self, id):
        repo = self._get_existing_repo(id)
        path = repo['relative_path']
        ks = KeyStore(path)
        return ks.list()

    def update_subscribed(self, repoid):
        """
        Do an asynchronous RMI to subscribed agents
        to update the .repo file.
        @param repoid: The updated repo ID.
        @type repoid: str
        """
        from pulp.server.api.consumer import ConsumerApi
        capi = ConsumerApi()
        cids = [str(c['id']) for c in capi.findsubscribed(repoid)]
        agent = Agent(cids, async=True)
        repolib = agent.RepoLib()
        repolib.update()

    def all_schedules(self):
        '''
        For all repositories, returns a mapping of repository name to sync schedule.
        
        @rtype:  dict
        @return: key - repo name, value - sync schedule
        '''
        return dict((r['id'], r['sync_schedule']) for r in self.repositories())
    
    def add_distribution(self, repoid, distroid):
        '''
         Associate a distribution to a given repo
         @param repoid: The repo ID.
         @param distroid: The distribution ID.
        '''
        repo = self._get_existing_repo(repoid)
        if self.distroapi.distribution(distroid) is None:
            raise PulpException("Distribution ID [%s] does not exist" % distroid)
        repo['distributionid'].append(distroid)
        self.objectdb.save(repo, safe=True)
        if repo['publish']:
            self._create_ks_link(repo)
        log.info("Successfully added distribution %s to repo %s" % (distroid, repoid))
        
    def remove_distribution(self, repoid, distroid):
        '''
         Delete a distribution from a given repo
         @param repoid: The repo ID.
         @param distroid: The distribution ID.
        '''
        repo = self._get_existing_repo(repoid)
        if distroid in repo['distributionid']:
            del repo['distributionid'][repo['distributionid'].index(distroid)]
            self.objectdb.save(repo, safe=True)
            self._delete_ks_link(repo)
            log.info("Successfully removed distribution %s from repo %s" % (distroid, repoid))
        else:
            log.error("No Distribution with ID %s associated to this repo" % distroid)
            
    def _create_ks_link(self, repo):
        if not os.path.isdir(self.distro_path):
            os.mkdir(self.distro_path)
        source_path = os.path.join(pulp.server.util.top_repos_location(), 
                repo["relative_path"])
        link_path = os.path.join(self.distro_path, repo["relative_path"])
        log.info("Linking %s" % link_path)
        pulp.server.util.create_symlinks(source_path, link_path)
    
    def _delete_ks_link(self, repo):
        link_path = os.path.join(self.distro_path, repo["relative_path"])
        log.info("Unlinking %s" % link_path)
        if os.path.lexists(link_path):
            # need to use lexists so we will return True even for broken links
            os.unlink(link_path)
            
    def list_distributions(self, repoid):
        '''
         List distribution in a given repo
         @param repoid: The repo ID.
         @return list: distribution objects.
        '''
        repo = self._get_existing_repo(repoid)
        distributions = []
        for distro in repo['distributionid']:
            distributions.append(self.distroapi.distribution(distro))
        return distributions

# The crontab entry will call this module, so the following is used to trigger the
# repo sync
if __name__ == '__main__':

    # Need to start logging since this will be called outside of the WSGI application
    pulp.server.logs.start_logging()

    # Currently this option parser is configured to automatically assume repo sync. If
    # further repo-related operations are ever added this will need to be refined, along
    # with the call in repo_sync.py that creates the cron entry that calls this script.
    parser = OptionParser()
    parser.add_option('--repoid', dest='repo_id', action='store')

    options, args = parser.parse_args()

    if options.repo_id:
        log.info('Running scheduled sync for repo [%s]' % options.repo_id)
        repo_api = RepoApi()
        repo_api._sync(options.repo_id)
