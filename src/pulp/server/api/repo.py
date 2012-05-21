# -*- coding: utf-8 -*-
#
# Copyright © 20102011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.


# Python
import gzip
import logging
import os
import re
import shutil
import sys
import time
import threading
import traceback
from datetime import datetime
from StringIO import StringIO
from urlparse import urlparse

# Pulp
import pulp.server.consumer_utils as consumer_utils
import pulp.server.util
from pulp.common.util import encode_unicode, decode_unicode
from pulp.common.bundle import Bundle
from pulp.common.dateutils import format_iso8601_datetime
from pulp.server import async
from pulp.server import constants
from pulp.server import comps_util
from pulp.server import config
from pulp.repo_auth.repo_cert_utils import RepoCertUtils
from pulp.repo_auth.protected_repo_utils import ProtectedRepoUtils
from pulp.server import updateinfo
from pulp.server.api.base import BaseApi
from pulp.server.api.cdn_connect import CDNConnection
from pulp.server.api.cds import CdsApi
from pulp.server.api.distribution import DistributionApi, DistributionHasReferences
from pulp.server.api.errata import ErrataApi, ErrataHasReferences
from pulp.server.api.file import FileApi, FileHasReferences
from pulp.server.api.filter import FilterApi
from pulp.server.api.keystore import KeyStore
from pulp.server.api.package import PackageApi, PackageHasReferences
from pulp.server.api.scheduled_sync import delete_repo_schedule
from pulp.server.async import run_async, find_async
from pulp.server.auditing import audit
from pulp.server.compat import chain
from pulp.server.db import model
from pulp.server.event.dispatcher import event
from pulp.server.exceptions import PulpException
from pulp.server.tasking.task import task_running, task_error
from pulp.server.agent import PulpAgent
from pymongo.errors import DuplicateKeyError

log = logging.getLogger(__name__)

repo_fields = model.Repo(None, None, None, None).keys()

def clear_sync_in_progress_flags():
    """
    Clears 'sync_in_progress' for all repositories
    Runs as part of initialization of wsgi application.

    If pulp server is shutdown in the middle of a sync it could leave
    some repositories 'locked'.  This will clear all locks on startup
    """
    collection = model.Repo.get_collection()
    #repos = collection.find(fields={"id":1, "sync_in_progress":1})
    # only fix those repos whose flag is actually set
    repos = collection.find({'sync_in_progress': True}, fields={'id': 1})
    for r in repos:
        collection.update({"id":r["id"]}, {"$set": {"sync_in_progress":False}})


class RepoApi(BaseApi):
    """
    API for create/delete/syncing of Repo objects
    """
    __sync_lock = threading.RLock()

    def __init__(self):
        self.packageapi = PackageApi()
        self.errataapi = ErrataApi()
        self.distroapi = DistributionApi()
        self.cdsapi = CdsApi()
        self.fileapi = FileApi()
        self.filterapi = FilterApi()
        self.localStoragePath = constants.LOCAL_STORAGE
        self.published_path = os.path.join(self.localStoragePath, "published", "repos")
        self.distro_path = os.path.join(self.localStoragePath, "published", "ks")
        self.__sync_lock = threading.RLock()

    def __getstate__(self):
        odict = self.__dict__.copy()
        for k, v in odict.items():
            if not isinstance(v, threading._RLock):
                continue
            odict.pop(k)
        return odict

    def _getcollection(self):
        return model.Repo.get_collection()

    def _get_existing_repo(self, id, fields=None):
        """
        Protected helper function to look up a repository by id and raise a
        PulpException if it is not found.
        """
        repo = self.repository(id, fields)
        if repo is None:
            raise PulpException("No Repo with id: %s found" % id)
        return repo

    def _hascontent(self, repo):
        """
        Get whether the specified repo has content
        @param repo: A repo.
        @type repo: dict
        @return: number of items in the repo
        @rtype: int
        """
        try:
            rootdir = pulp.server.util.top_repos_location()
            relativepath = repo['relative_path']
            path = os.path.join(rootdir, relativepath)
            return len(os.listdir(path))
        except:
            return 0

    def _consolidate_bundle(self, data):
        """
        Consolidate key & certificate.
        Used by create() and update().  Also performs some validation.
        @param data: cert dict (ca|cert|key)
        @type data: dict
        """
        KEY = 'key'
        CRT = 'cert'
        if data is None:
            return
        key = data.get(KEY, '')
        cert = data.get(CRT, '')
        if key:
            if not Bundle.haskey(key):
                raise Exception, 'key (PEM) not valid'
            if cert:
                if not Bundle.hascrt(cert):
                    raise Exception, 'certificate (PEM) not valid'
                data['cert'] = Bundle.join(key, cert)
            else:
                raise Exception, 'certificate must be specified'
        else:
            if cert and (not Bundle.hasboth(cert)):
                raise Exception, 'key and certificate (PEM) expected'
        if KEY in data:
            del data[KEY]


    def find_combined_whitelist_packages(self, repo_filters):
        combined_whitelist_packages = []
        for filter_id in repo_filters:
            filter = self.filterapi.filter(filter_id)
            if filter['type'] == "whitelist":
                combined_whitelist_packages.extend(filter['package_list'])
        return combined_whitelist_packages

    def find_combined_blacklist_packages(self, repo_filters):
        combined_blacklist_packages = []
        for filter_id in repo_filters:
            filter = self.filterapi.filter(filter_id)
            if filter['type'] == "blacklist":
                combined_blacklist_packages.extend(filter['package_list'])
        return combined_blacklist_packages

    def _find_filtered_package_list(self, unfiltered_pkglist, whitelist_packages, blacklist_packages):
        pkglist = {}

        if whitelist_packages:
            for key, pkg in unfiltered_pkglist.items():
                for whitelist_package in whitelist_packages:
                    w = re.compile(whitelist_package)
                    if w.match(pkg["filename"]):
                        pkglist[key] = pkg
                        break
        else:
            pkglist = unfiltered_pkglist

        if blacklist_packages:
            to_remove = []
            for key, pkg in pkglist.items():
                for blacklist_package in blacklist_packages:
                    b = re.compile(blacklist_package)
                    if b.match(pkg["filename"]):
                        to_remove.append(key)
                        break
            for key in to_remove:
                del pkglist[key]

        return pkglist


    @audit()
    def clean(self):
        """
        Delete all the Repo objects in the database and remove associated
        files from filesystem.  WARNING: Destructive
        """
        found = self.repositories(fields=["id"])
        for r in found:
            self.delete(r["id"])

    @audit(params=['id', 'name', 'arch', 'feed'])
    def create(self, id, name, arch=None, feed=None,
               feed_cert_data=None, consumer_cert_data=None, groupid=(),
               relative_path=None, gpgkeys=(), checksum_type="sha256", notes={},
               preserve_metadata=False, content_types="yum", publish=None):
        """
        Create a new Repository object and return it
        """
        self.check_for_whitespace(id)
        if relative_path:
            self.check_for_whitespace(relative_path, "relative_path")
            relative_path = encode_unicode(relative_path)
        id = encode_unicode(id)
        repo = self.repository(id)
        if repo is not None:
            raise PulpException("A Repo with id %s already exists" % id)

        if not model.Repo.is_supported_arch(arch):
            raise PulpException('Architecture must be one of [%s]' % ', '.join(model.Repo.SUPPORTED_ARCHS))

        if not model.Repo.is_supported_checksum(checksum_type):
            raise PulpException('Checksum Type must be one of [%s]' % ', '.join(model.Repo.SUPPORTED_CHECKSUMS))

        if not model.Repo.is_supported_content_type(content_types):
            raise PulpException('Content Type must be one of [%s]' % ', '.join(model.Repo.SUPPORTED_CONTENT_TYPES))
        source = None
        if feed:
            source = model.RepoSource(feed)
        # Relative path calculation
        if relative_path is None or relative_path == "":
            if source is not None :
                if source['type'] == "local":
                    relative_path = id
                else:
                    # For none product repos, default to repoid
                    url_parse = urlparse(encode_unicode(source["url"]))
                    relative_path = url_parse[2] or id
            else:
                relative_path = id
        else:
            relative_path = relative_path

        # Remove leading "/", they will interfere with symlink
        # operations for publishing a repository
        relative_path = relative_path.strip('/')

        # Verify that the new relative path will not cause problems with existing repositories
        all_repos = self.collection.find()
        for existing in all_repos:
            existing['relative_path'] = encode_unicode(existing['relative_path'])
            if not validate_relative_path(relative_path, existing['relative_path']):
                msg  = 'New relative path [%s] conflicts with existing relative path [%s]; ' % (relative_path, existing['relative_path'])
                msg += 'paths may not be a parent or child directory of another relative path'
                raise PulpException(msg)

        r = model.Repo(id, name, arch, relative_path, feed, notes)

        # Store any certificates and add the full paths to their files in the repo object
        repo_cert_utils = RepoCertUtils(config.config)
        protected_repo_utils = ProtectedRepoUtils(config.config)

        if feed_cert_data:
            # consolidate key & certificate
            self._consolidate_bundle(feed_cert_data)
            # store certificates
            feed_cert_files = repo_cert_utils.write_feed_cert_bundle(id, feed_cert_data)
            r['feed_ca'] = feed_cert_files['ca']
            r['feed_cert'] = feed_cert_files['cert']

        if consumer_cert_data:
            # consolidate key & certificate
            self._consolidate_bundle(consumer_cert_data)
            # store certificates
            consumer_cert_files = repo_cert_utils.write_consumer_cert_bundle(id, consumer_cert_data)
            r['consumer_ca'] = consumer_cert_files['ca']
            r['consumer_cert'] = consumer_cert_files['cert']
            protected_repo_utils.add_protected_repo(r['relative_path'], id)

        if groupid:
            for gid in groupid:
                r['groupid'].append(gid)

        r['repomd_xml_path'] = \
            os.path.join(pulp.server.util.top_repos_location(),
                         r['relative_path'], 'repodata/repomd.xml')
        r['checksum_type'] = checksum_type
        if gpgkeys:
            root = pulp.server.util.top_repos_location()
            path = r['relative_path']
            ks = KeyStore(path)
            added = ks.add(gpgkeys)
        #set if the repo can be a mirror;a sync operation
        # can override this at runtime for specific sync.
        if feed:
            # only preserve metadata if its a feed repo
            r['preserve_metadata'] = preserve_metadata
        if content_types:
            r['content_types'] = content_types
        try:
            self.collection.insert(r, safe=True)
        except DuplicateKeyError, dke:
            raise PulpException("A Repo with relative path `%s` already exists; failed to create repo `%s`" % (r['relative_path'], id))
        # create an empty repodata
        repo_path = os.path.join(\
            pulp.server.util.top_repos_location(), r['relative_path'])
        repo_path = encode_unicode(repo_path)
        if not os.path.exists(repo_path):
            pulp.server.util.makedirs(repo_path)
        if content_types in ("yum") and not r['preserve_metadata']:
            # if its yum or if metadata is not preserved, trigger an empty repodata
            pulp.server.util.create_repo(repo_path, checksum_type=r['checksum_type'])
        if publish is None:
            default_to_publish = config.config.getboolean('repos', 'default_to_published')
        else:
            default_to_publish = publish
        self.publish(r["id"], default_to_publish)
        # refresh repo object from mongo
        created = self.repository(r["id"])
        self.__created(r)
        return created

    @event(subject='repo.created')
    def __created(self, repo):
        """
        Event placeholder.
        """
        pass

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
        self.collection.save(repo, safe=True)
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
            self.update_repo_on_consumers(repo)
        except Exception, e:
            log.error(e)
            return False
        return True

    def _create_published_link(self, repo):
        if not os.path.isdir(self.published_path):
            pulp.server.util.makedirs(self.published_path)
        source_path = os.path.join(pulp.server.util.top_repos_location(),
                                   repo["relative_path"])
        source_path = encode_unicode(source_path)
        if not os.path.isdir(source_path):
            pulp.server.util.makedirs(source_path)
        link_path = os.path.join(self.published_path, repo["relative_path"])
        link_path = encode_unicode(link_path)
        pulp.server.util.create_rel_symlink(source_path, link_path)

    def _delete_published_link(self, repo):
        if repo["relative_path"]:
            repo["relative_path"] = encode_unicode(repo["relative_path"])
            link_path = os.path.join(self.published_path, repo["relative_path"])
            if os.path.lexists(link_path):
                # need to use lexists so we will return True even for broken links
                try:
                    os.unlink(link_path)
                    # after unlinking, make sure to clean up the directory tree
                    pulp.server.util.delete_empty_directories(os.path.dirname(link_path))
                except Exception, e:
                    log.error(e)


    @audit(params=['groupid', 'content_set'])
    def create_product_repo(self, content_set, cert_data, groupid=None, gpg_keys=None):
        """
         Creates a repo associated to a product. Usually through an event raised
         from candlepin
         @param groupid: A product the candidate repo should be associated with.
         @type groupid: str
         @param content_set: a dict of content set labels and relative urls
         @type content_set: dict(<label> : <relative_url>,)
         @param cert_data: a dictionary of ca_cert, cert and key for this product
         @type cert_data: dict(ca : <ca_cert>, cert: <ent_cert>, key : <cert_key>)
         @param gpg_keys: list of keys to be associated with the repo
         @type gpg_keys: list(dict(gpg_key_label : <gpg-key-label>, gpg_key_url : url),)
        """
        if not cert_data or not content_set:
            # Nothing further can be done, exit
            return
        repo_cert_utils = RepoCertUtils(config.config)
        cert_files = repo_cert_utils.write_feed_cert_bundle(groupid, cert_data)
        CDN_URL = config.config.get("repos", "content_url")
        CDN_HOST = urlparse(CDN_URL).hostname
        serv = CDNConnection(CDN_HOST, cacert=cert_files['ca'],
                             cert=cert_files['cert'], key=cert_files['key'])
        serv.connect()
        repo_info = serv.fetch_listing(content_set)
        gkeys = self._get_gpg_keys(serv, gpg_keys)
        for label, uri in repo_info.items():
            try:
                repo = self.create(label, label, arch=label.split("-")[-1],
                                   feed=CDN_URL + '/' + uri,
                                   feed_cert_data=cert_data, groupid=[groupid],
                                   relative_path=uri)
                repo['release'] = label.split("-")[-2]
                self.addkeys(repo['id'], gkeys)
                self.collection.save(repo, safe=True)
            except:
                log.error("Error creating repo %s for product %s" % (label, groupid))
                continue

        serv.disconnect()

    @audit(params=['groupid', 'content_set'])
    def update_product_repo(self, content_set, cert_data, groupid=None, gpg_keys=[]):
        """
         Creates a repo associated to a product. Usually through an event raised
         from candlepin
         @param groupid: A product the candidate repo should be associated with.
         @type groupid: str
         @param content_set: a dict of content set labels and relative urls
         @type content_set: dict(<label> : <relative_url>,)
         @param cert_data: a dictionary of ca_cert, cert and key for this product
         @type cert_data: dict(ca : <ca_cert>, cert: <ent_cert>, key : <cert_key>)
         @param gpg_keys: list of keys to be associated with the repo
         @type gpg_keys: list(dict(gpg_key_label : <gpg-key-label>, gpg_key_url : url),)
        """
        if not cert_data or not content_set:
            # Nothing further can be done, exit
            return
        repo_cert_utils = RepoCertUtils(config.config)
        cert_files = repo_cert_utils.write_feed_cert_bundle(groupid, cert_data)
        CDN_URL = config.config.get("repos", "content_url")
        CDN_HOST = urlparse(CDN_URL).hostname
        serv = CDNConnection(CDN_HOST, cacert=cert_files['ca'],
                             cert=cert_files['cert'], key=cert_files['key'])
        serv.connect()
        repo_info = serv.fetch_listing(content_set)
        gkeys = self._get_gpg_keys(serv, gpg_keys)
        for label, uri in repo_info.items():
            try:
                repo = self._get_existing_repo(label)
                repo['feed'] =  CDN_URL + '/' + uri
                if cert_data:
                    cert_files = repo_cert_utils.write_feed_cert_bundle(label, cert_data)
                    for key, value in cert_files.items():
                        repo[key] = value
                repo['arch'] = label.split("-")[-1]
                repo['relative_path'] = uri
                repo['groupid'] = [groupid]
                self.addkeys(repo['id'], gkeys)
                self.collection.save(repo, safe=True)
            except PulpException, pe:
                log.error(pe)
                continue
            except:
                log.error("Error updating repo %s for product %s" % (label, groupid))
                continue

        serv.disconnect()

    def _get_gpg_keys(self, serv, gpg_key_list):
        gpg_keys = []
        for gpgkey in gpg_key_list:
            label = gpgkey['gpg_key_label']
            uri = str(gpgkey['gpg_key_url'])
            try:
                if uri.startswith("file://"):
                    key_path = urlparse(encode_unicode(uri)).path
                    ginfo = open(key_path, "rb").read()
                else:
                    ginfo = serv.fetch_gpgkeys(uri)
                gpg_keys.append((label, ginfo))
            except Exception:
                log.error("Unable to fetch the gpg key info for %s" % uri)
        return gpg_keys

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
        log.info("List of repos to be deleted %s" % repos)
        for repo in repos:
            try:
                self.collection.delete({'id':repo['id']}, safe=True)
            except:
                log.error("Error deleting repo %s for product %s" % (repo['id'], groupid))
                continue

    def find_if_running_sync(self, id):
        """
        Returns True if sync is running for this repo, else returns False.
        """
        tasks = [t for t in find_async(method_name="_sync")
                 if (t.args and encode_unicode(id) in t.args) or
                 (t.kwargs and encode_unicode(id) in t.kwargs.values())]
        for t in tasks:
            if getattr(t, 'state', None) not in (task_running,):
                continue
            log.info("Current running a sync on repo : %s", id)
            return True
        return False

    @event(subject='repo.deleted')
    @audit()
    def delete(self, id, keep_files=False):
        repo = self._get_existing_repo(id)
        log.info("Delete API call invoked %s" % repo['id'])

        # delete scheduled syncs, if any
        delete_repo_schedule(repo)

        # find if sync in progress
        if self.find_if_running_sync(id):
            raise PulpException("Repo [%s] cannot be deleted because of sync in progress." % id)

        # unassociate from CDS(s)
        self.cdsapi.unassociate_all_from_repo(id, True)

        #update feed of clones of this repo to None unless they point to origin feed
        for clone_id in repo['clone_ids']:
            try:
                cloned_repo = self._get_existing_repo(clone_id)
                if cloned_repo['source'] != repo['source']:
                    cloned_repo['source'] = None
                    self.collection.save(cloned_repo, safe=True)
            except PulpException:
                log.debug('Clone with id [%s] does not exist anymore. Safe to delete repo', clone_id)

        #update clone_ids of its parent repo
        parent_repos = self.repositories({'clone_ids' : id})

        if len(parent_repos) == 1:
            parent_repo = parent_repos[0]
            clone_ids = parent_repo['clone_ids']
            clone_ids.remove(decode_unicode(id))
            parent_repo['clone_ids'] = clone_ids
            self.collection.save(parent_repo, safe=True)

        self._delete_published_link(repo)
        delete_repo_schedule(repo)

        # delete gpg key links
        path = repo['relative_path']
        ks = KeyStore(path)
        ks.clean(True)

        #remove packages
        # clear package list to decrement each package's reference count
        packages = repo["packages"]
        repo["packages"] = []
        self.collection.save(repo, safe=True)
        for pkgid in packages:
            try:
                self.packageapi.delete(pkgid, keep_files)
            except PackageHasReferences:
                log.debug(
                    'package "%s" has references, not deleted',
                    pkgid)
            except Exception, ex:
                log.exception(ex)

        errata = repo["errata"]
        repo["errata"] = []
        self.collection.save(repo, safe=True)
        for eid in errata:
            try:
                self.errataapi.delete(eid)
            except ErrataHasReferences:
                log.debug(
                    'errata "%s" has references, not deleted',
                    eid)
            except Exception, ex:
                log.exception(ex)

        #remove any distributions
        for distroid in repo['distributionid']:
            self.remove_distribution(repo['id'], distroid)
            try:
                self.distroapi.delete(distroid, keep_files)
            except DistributionHasReferences:
                log.info("Distribution Id [%s] has other references; leaving it in the db" % distroid)
        #remove files:
        for fileid in repo['files']:
            self.remove_file(repo['id'], [fileid])
            try:
                self.fileapi.delete(fileid, keep_files)
            except FileHasReferences:
                log.info("file Id [%s] has other references; leaving it in the db" % fileid)
        #unsubscribe consumers from this repo
        #importing here to bypass circular imports
        from pulp.server.api.consumer import ConsumerApi
        capi = ConsumerApi()
        bound_consumers = consumer_utils.consumers_bound_to_repo(repo['id'])
        for consumer in bound_consumers:
            try:
                log.info("Unsubscribe repoid %s from consumer %s" % (repo['id'], consumer['id']))
                capi.unbind(consumer['id'], repo['id'])
            except:
                log.error("failed to unbind repoid %s from consumer %s moving on.." % \
                          (repo['id'], consumer['id']))
                continue

        repo_location = pulp.server.util.top_repos_location()

        #delete any data associated to this repo
        for field in ['relative_path']:
            if field == 'relative_path' and repo[field]:
                fpath = os.path.join(repo_location, repo[field])
            else:
                fpath = repo[field]
            if fpath and os.path.exists(fpath):
                try:
                    if os.path.isfile(fpath):
                        os.remove(fpath)
                    else: # os.path.isdir(fpath):
                        shutil.rmtree(fpath)
                    log.info("removing repo files .... %s" % fpath)
                except:
                    #file removal failed
                    log.error("Unable to cleanup file %s " % fpath)
                    continue
        pulp.server.util.delete_empty_directories(os.path.dirname(fpath))
        # Delete any certificate bundles for the repo
        repo_cert_utils = RepoCertUtils(config.config)
        repo_cert_utils.delete_for_repo(id)

        # Remove this repo from the protected repos list in case that existed
        protected_repo_utils = ProtectedRepoUtils(config.config)
        protected_repo_utils.delete_protected_repo(repo['relative_path'])

        # remove any completed tasks related to this repo
        for task in async.complete_async():
            if encode_unicode(repo['_id']) in task.args or encode_unicode(repo['_id']) in task.kwargs.values():
                async.drop_complete_async(task)

        # remove task history related to this repo
        collection = model.TaskHistory.get_collection()
        collection.remove({'args': repo['_id']}, safe=True) # misses id in kwargs

        # delete the object
        self.collection.remove({'id' : id}, safe=True)

    @event(subject='repo.updated')
    @audit()
    def update(self, id, delta):
        """
        Update a repo object.
        @param id: The repo ID.
        @type id: str
        @param delta: A dict containing update keywords.
        @type delta: dict
        @return: The updated object
        @rtype: dict
        """
        delta.pop('id', None)
        repo = self._get_existing_repo(id)
        prevpath = ''
        if repo['source']:
            prevpath = urlparse(encode_unicode(repo['source']['url']))[2].strip('/')
        hascontent = self._hascontent(repo)
        repo_cert_utils = RepoCertUtils(config.config)
        protected_repo_utils = ProtectedRepoUtils(config.config)

        # Keeps a running track of whether or not the changes require notifying consumers
        # Also need to know later on if a consumer cert was updated.
        update_consumers = False
        consumer_cert_updated = False
        update_metadata = False
        for key, value in delta.items():
            # simple changes
            if key == "addgrp":
                groupids = repo['groupid']
                if value not in groupids:
                    groupids.append(value)
                repo["groupid"] = groupids
                continue
            if key == "rmgrp":
                groupids = repo['groupid']
                if value in groupids:
                    groupids.remove(value)
                repo["groupid"] = groupids
                continue
            if key == 'addkeys':
                self.addkeys(id, value)
                continue
            if key == 'rmkeys':
                self.rmkeys(id, value)
                continue
            if key in ('name', 'arch',):
                repo[key] = value
                if key == 'name':
                    update_consumers = True
                continue
            # Feed certificate bundle changed
            if key == 'feed_cert_data':
                # consolidate key & certificate
                self._consolidate_bundle(value)
                # store certificates
                written_files = repo_cert_utils.write_feed_cert_bundle(id, value)
                for item in written_files:
                    repo['feed_' + item] = written_files[item]
                continue
            # Consumer certificate bundle changed
            if key == 'consumer_cert_data':
                # consolidate key & certificate
                self._consolidate_bundle(value)
                # store certificates
                written_files = repo_cert_utils.write_consumer_cert_bundle(id, value)
                for item in written_files:
                    repo['consumer_' + item] = written_files[item]
                consumer_cert_updated = True
                update_consumers = True
                continue
            # feed changed
            if key == 'feed':
                repo[key] = value
                if value:
                    newpath = urlparse(encode_unicode(value))[2].strip('/')
                    if prevpath != newpath:
                        log.error("MisMatch %s != %s" % (prevpath, newpath))
                        raise PulpException("Relativepath of the new feed [%s] does not match existing feed [%s]; cannot perform update" % (newpath, prevpath))
                    ds = model.RepoSource(value)
                    repo['source'] = ds
                continue
            if key == 'checksum_type':
                if not model.Repo.is_supported_checksum(value):
                    raise PulpException('Checksum Type must be one of [%s]' % ', '.join(model.Repo.SUPPORTED_CHECKSUMS))
                if repo[key] != value:
                    repo[key] = value
                    update_metadata = True
                else:
                    log.info('the repo checksum type is already %s' % value)
                continue
            raise Exception, \
                  'update keyword "%s", not-supported' % key

        # If the consumer certs were updated, update the protected repo listings.
        # This has to be done down here in case the relative path has changed as well.
        if consumer_cert_updated:
            bundle = repo_cert_utils.read_consumer_cert_bundle(id)
            if bundle is None:
                protected_repo_utils.delete_protected_repo(repo['relative_path'])
            else:
                protected_repo_utils.add_protected_repo(repo['relative_path'], id)

        # store changed object
        self.collection.save(repo, safe=True)
            
        # Update subscribed consumers after the object has been saved
        if update_consumers:
            self.update_repo_on_consumers(repo)
        if update_metadata:
            # update the existing metadata with new checksum type
            self.generate_metadata(id)
        return repo

    def repositories(self, spec=None, fields=None):
        """
        Return a list of Repositories
        """
        return list(self.collection.find(spec=spec, fields=fields))

    def repository(self, id, fields=None):
        """
        Return a single Repository object
        """
        repos = self.repositories({'id': id}, fields)
        if not repos:
            return None
        return repos[0]

    def packages(self, repo_id, **kwargs):
        """
        Return list of Package objects in this Repo
        @type repo_id: str
        @param repo_id: repository id
        @type kwargs: variable keyword arguments accepted
        @param kwargs: keyword arguments will be passed into package lookup query
        @rtype: list
        @return: package objects belonging to this repository
        """
        repo = self._get_existing_repo(repo_id)
        if not kwargs:
            return self.packageapi.packages_by_id(repo["packages"])
        search_dict = {}
        for key in kwargs:
            search_dict[key] = kwargs[key]
        return self.packageapi.packages_by_id(repo["packages"], **search_dict)

    def package_count(self, id):
        """
        Return the number of packages in a repository.
        @type id: str
        @param id: repository id
        @rtype: int
        @return: the number of package in the repository corresponding to id
        """
        return self.repository(id, fields=["package_count"])['package_count']

    def get_package(self, repo_id, name):
        return self.get_packages_by_name(repo_id, name)

    def get_packages_by_id(self, repo_id, pkg_ids):
        """
        Return package objects for the passed in pkg_ids that are in repo_id
        @type repo_id: string
        @param repo_id: repository id
        @type pkg_ids: list of strings
        @param pkg_ids: list of package ids
        """
        repo = self._get_existing_repo(repo_id)
        #Restrict id's to only those that are in this repository
        ids = list(set(pkg_ids).intersection(repo["packages"]))
        return self.packageapi.packages_by_id(ids)

    def get_packages_by_name(self, repo_id, name):
        """
        Return matching Package objects in this Repo
        """
        repo = self._get_existing_repo(repo_id)
        return self.packageapi.packages_by_id(repo["packages"], name=name)

    def get_packages_by_nvrea(self, repo_id, nvreas=[], verify_existing=True):
        """
        Check if package exists or not in this repo for given nvrea
        @return: [{"filename":pulp.server.db.model.resoure.Package}
        """
        log.debug("looking up pkg(s) [%s] in repo [%s]" % (nvreas, repo_id))
        repo = self._get_existing_repo(repo_id)
        repo_packages = repo['packages']
        result = self.packageapi.or_query(nvreas, restrict_ids=repo_packages)
        pkgs = {}
        for p in result:
            if verify_existing:
                pkg_repo_path = pulp.server.util.get_repo_package_path(
                    repo['relative_path'], p['filename'])
                if os.path.exists(pkg_repo_path):
                    pkgs[p['filename']] = p
            else:
                pkgs[p['filename']] = p
        return pkgs

    def get_packages_by_filename(self, repo_id, filenames=[]):
        """
          Return matching Package object in this Repo by filename
        """
        repo = self._get_existing_repo(repo_id)
        return self.packageapi.packages_by_id(repo["packages"], filename={"$in":filenames})

    def get_packages(self, repo_id, spec={}, pkg_fields=None):
        """
        Generic call to get the packages in a repository that match the given
        specification.
        """
        repo = self._get_existing_repo(repo_id, ['packages'])
        collection = model.Package.get_collection()
        spec['id'] = {'$in': list(repo['packages'])}
        cursor = collection.find(spec=spec, fields=pkg_fields)
        if cursor.count() > 0:
            return list(cursor)
        return []

    @audit()
    def add_package(self, repoid, packageids=[]):
        """
        Adds the passed in package to this repo
        @return:    [], filtered_count on success
                    [(package_id,(name,epoch,version,release,arch),filename,checksum)], filtered_count on error,
                    where each id represents a package id that couldn't be added
        """
        filtered_count = 0
        if not packageids:
            log.debug("add_package(%s, %s) called with no packageids to add" % (repoid, packageids))
            return [], filtered_count
        def get_pkg_tup(package):
            return (package['name'], package['epoch'], package['version'], package['release'], package['arch'])
        def get_pkg_nevra(package):
            return dict(zip(("name", "epoch", "version", "release", "arch"), get_pkg_tup(package)))
        def form_error_tup(pkg, error_message=None):
            pkg_tup = get_pkg_tup(pkg)
            return (pkg["id"], pkg_tup, pkg["filename"], pkg["checksum"].values()[0], error_message)

        start_add_packages = time.time()
        errors = []
        repo = self._get_existing_repo(repoid)
        if not repo:
            log.error("Couldn't find repository [%s]" % (repoid))
            return [(pkg_id, (None, None, None, None, None), None, None) for pkg_id in packageids], filtered_count
        repo_path = os.path.join(
            pulp.server.util.top_repos_location(), repo['relative_path'])
        if not os.path.exists(repo_path):
            pulp.server.util.makedirs(repo_path)
        packages = {}
        nevras = {}
        filenames = {}
        # Convert package ids to package objects
        pkg_coll = model.Package.get_collection()
        result = pkg_coll.find({"id":{"$in":packageids}})
        pkg_objects = {}
        for p in result:
            pkg_objects[p["id"]] = p
        log.debug("Finished created pkg_object in %s seconds" % (time.time() - start_add_packages))

        for pkg_id in packageids:
            if not pkg_objects.has_key(pkg_id):
                # Detect if any packageids passed in could not be located
                log.debug("No Package with id: %s found" % pkg_id)
                errors.append((pkg_id, (None, None, None, None, None), None, None))
                packageids.remove(pkg_id)

        # Process repo filters if any
        if repo['filters']:
            log.info("Repo filters : %s" % repo['filters'])
            whitelist_packages = self.find_combined_whitelist_packages(repo['filters'])
            blacklist_packages = self.find_combined_blacklist_packages(repo['filters'])
            log.debug("combined whitelist packages = %s" % whitelist_packages)
            log.debug("combined blacklist packages = %s" % blacklist_packages)
        else:
            whitelist_packages = []
            blacklist_packages = []

        original_pkg_objects_count = len(pkg_objects)
        pkg_objects = self._find_filtered_package_list(pkg_objects, whitelist_packages, blacklist_packages)
        if original_pkg_objects_count > len(pkg_objects):
            filtered_count = original_pkg_objects_count - len(pkg_objects)
            for pkg_id in packageids:
                if not pkg_objects.has_key(pkg_id):
                    # Detect filtered package ids
                    packageids.remove(pkg_id)

        if not pkg_objects:
            log.debug("No packages left to be added after removing filtered packages")
            return [], filtered_count

        # Desire to keep the order dictated by calling arg of 'packageids'
        for pkg_id in packageids:
            pkg = pkg_objects[pkg_id]
            pkg_tup = get_pkg_tup(pkg)

            if nevras.has_key(pkg_tup):
                log.debug("Duplicate NEVRA detected [%s] with package id [%s] and sha256 [%s]" \
                         % (pkg_tup, pkg["id"], pkg["checksum"].values()[0]))
                errors.append(form_error_tup(pkg))
                continue
            if filenames.has_key(pkg["filename"]):
                error_msg = "Duplicate filename detected [%s] with package id [%s] and sha256 [%s]" \
                    % (pkg["filename"], pkg["id"], pkg["checksum"].values()[0])
                log.debug(error_msg)
                errors.append(form_error_tup(pkg, error_msg))
                continue
            nevras[pkg_tup] = pkg["id"]
            filenames[pkg["filename"]] = pkg
            packages[pkg["id"]] = pkg
        # Check for duplicate NEVRA already in repo
        log.debug("Finished check of NEVRA/filename in argument data by %s seconds" % (time.time() - start_add_packages))
        # This took 528 seconds with rhel-i386-vt-5 being added and roughly 14Gig of RAM in mongo
        # found = self.get_packages_by_nvrea(repo['id'], nevras.values())
        # Exploring alternate of operating on each nevra one at a time for now
        found = {}
        for n in nevras:
            pkg = pkg_objects[nevras[n]]
            nevra = get_pkg_nevra(pkg)
            result = self.get_packages_by_nvrea(repo['id'], [nevra])
            for f in result:
                found[f] = result[f]
        for fname in found:
            pkg = found[fname]
            pkg_tup = get_pkg_tup(pkg)
            if not nevras.has_key(pkg_tup):
                log.error("Unexpected error, can't find [%s] yet it was returned as a duplicate NEVRA in repo [%s]" % (pkg_tup, repo["id"]))
                continue
            error_message = "Package with same NVREA [%s] already exists in repo [%s]" % (pkg_tup, repo['id'])
            log.debug(error_message)
            errors.append(form_error_tup(pkg, error_message))
            if packages.has_key(nevras[pkg_tup]):
                del packages[nevras[pkg_tup]]
        # Check for same filename in calling data or for existing
        log.info("Finished check of existing NEVRA by %s seconds" % (time.time() - start_add_packages))
        found = self.get_packages_by_filename(repo["id"], filenames.keys())
        for pid in found:
            pkg = found[pid]
            if not filenames.has_key(pkg["filename"]):
                log.error("Unexpected error, can't find [%s] yet it was returned as a duplicate filename in repo [%s]" % (pkg["filename"], repo["id"]))
                continue
            error_message = "Package with same filename [%s] already exists in repo [%s]" \
                % (pkg["filename"], repo['id'])
            log.debug(error_message)
            errors.append(form_error_tup(pkg, error_message))
            del_pkg_id = filenames[pkg["filename"]]["id"]
            if packages.has_key(del_pkg_id):
                del packages[del_pkg_id]
        log.debug("Finished check of get_packages_by_filename() by %s seconds" % (time.time() - start_add_packages))
        pkg_collection = model.Package.get_collection()

        for index, pid in enumerate(packages):
            pkg = packages[pid]
            self._add_package(repo, pkg)
            log.debug("Added: %s to repo: %s, progress %s/%s" % (pkg['filename'], repo['id'], index, len(packages)))
            shared_pkg = pulp.server.util.get_shared_package_path(
                pkg['name'], pkg['version'], pkg['release'],
                pkg['arch'], pkg["filename"], pkg['checksum'])
            pkg_repo_path = pulp.server.util.get_repo_package_path(
                repo['relative_path'], pkg["filename"])
            if not os.path.exists(pkg_repo_path):
                try:
                    pulp.server.util.create_rel_symlink(shared_pkg, pkg_repo_path)
                except OSError:
                    log.error("Link %s already exists" % pkg_repo_path)
            if repo['id'] not in pkg['repoids']:
                # Add the repoid to the list on the package
                pkg['repoids'].append(repo['id'])
                pkg_collection.save(pkg, safe=True)
        self.collection.save(repo, safe=True)
        end_add_packages = time.time()
        log.debug("inside of repo.add_package() adding packages took %s seconds" % (end_add_packages - start_add_packages))
        return errors, filtered_count

    def _add_package(self, repo, p):
        """
        Responsible for properly associating a Package to a Repo
        """
        pkgid = p
        try:
            pkgid = p["id"]
        except:
            # Attempt to access as a SON or a Dictionary, Fall back to a regular package id
            pass
        if pkgid not in repo['packages']:
            repo['packages'].append(pkgid)
            repo['package_count'] = repo['package_count'] + 1

    @audit()
    def remove_package(self, repoid, p):
        """Note: This method does not update repo metadata.
        It is assumed metadata has already been updated.
        """
        return self.remove_packages(repoid, [p])

    def remove_packages(self, repoid, pkgobjs=[]):
        """
         Remove one or more packages from a repository
         @return:   [] on success of removal of all packages
                    [error_packages] on an error, error_packages being a list of each package failed to remove
        """
        errors = []
        if not pkgobjs:
            log.debug("remove_packages invoked on %s with no packages" % (repoid))
            # Nothing to perform, return
            return errors
        repo = self._get_existing_repo(repoid)
        pkg_collection = model.Package.get_collection()
        for pkg in pkgobjs:
            if pkg['id'] not in repo['packages']:
                log.debug("Attempted to remove a package<%s> that isn't part of repo[%s]" % (pkg["filename"], repoid))
                errors.append(pkg)
                continue
            repo['packages'].remove(pkg['id'])
            repo['package_count'] = repo['package_count'] - 1
            if repoid in pkg['repoids']:
                del pkg['repoids'][pkg['repoids'].index(repoid)]
                pkg_collection.save(pkg, safe=True)
            # Remove package from repo location on file system
            pkg_repo_path = pulp.server.util.get_repo_package_path(
                repo['relative_path'], pkg["filename"])
            if os.path.exists(encode_unicode(pkg_repo_path)):
                log.debug("Delete package %s at %s" % (pkg["filename"], pkg_repo_path))
                os.remove(encode_unicode(pkg_repo_path))
        self.collection.save(repo, safe=True)
        repo_path = os.path.join(
            pulp.server.util.top_repos_location(), repo['relative_path'])
        if not os.path.exists(encode_unicode(repo_path)):
            pulp.server.util.makedirs(encode_unicode(repo_path))
        return errors

    def find_repos_by_package(self, pkgid):
        """
        Return repos that contain passed in package id
        @param pkgid: package id
        """
        found = self.collection.find({"packages":pkgid}, fields=["id"])
        return [r["id"] for r in found]

    def errata(self, id, types=(), severity=None):
        """
         Look up all applicable errata for a given repo id
        """
        repo = self._get_existing_repo(id)
        errata = repo['errata']
        if not errata:
            return []
        if types:
            for type in types:
                if type not in errata:
                    types.remove(type)

            errataids = [item for type in types for item in errata[type]]
        else:
            errataids = list(chain.from_iterable(errata.values()))
        # For each erratum find id, title and type
        repo_errata = []
        for errataid in errataids:
            errata_obj = self.errataapi.erratum(errataid, fields=['id', 'title', 'type', 'severity', 'repoids'])
            if severity:
                if errata_obj['severity'] in severity:
                    repo_errata.append(errata_obj)
            else:
                repo_errata.append(errata_obj)
        return repo_errata

    @audit()
    def add_erratum(self, repoid, erratumid):
        """
        Adds in erratum to this repo
        """
        repo = self._get_existing_repo(repoid)
        self._add_erratum(repo, erratumid)
        self.collection.save(repo, safe=True)
        self._update_errata_packages(repoid, [erratumid], action='add')
        updateinfo.generate_updateinfo(repo)

    def _find_filtered_erratum_packages(self, unfiltered_pkglist, whitelist_packages, blacklist_packages):
        pkglist = []

        if whitelist_packages:
            for pkg in unfiltered_pkglist:
                for whitelist_package in whitelist_packages:
                    w = re.compile(whitelist_package)
                    if w.match(pkg["filename"]):
                        pkglist.append(pkg)
                        break
        else:
            pkglist = unfiltered_pkglist

        if blacklist_packages:
            for pkg in pkglist:
                for blacklist_package in blacklist_packages:
                    b = re.compile(blacklist_package)
                    if b.match(pkg["filename"]):
                        pkglist.remove(pkg)
                        break

        return pkglist


    def add_errata(self, repoid, errataids=()):
        """
         Adds a list of errata to this repo
         Returns a list of errataids which are skipped because of repository filters
        """
        repo = self._get_existing_repo(repoid)
        filtered_errata = []
        # Process repo filters if any
        if repo['filters']:
            log.info("Repo filters : %s" % repo['filters'])
            whitelist_packages = self.find_combined_whitelist_packages(repo['filters'])
            blacklist_packages = self.find_combined_blacklist_packages(repo['filters'])
            log.info("combined whitelist packages = %s" % whitelist_packages)
            log.info("combined blacklist packages = %s" % blacklist_packages)

            for erratumid in errataids:
                erratum = self.errataapi.erratum(erratumid)
                original_pkg_objects = [p for pkg in erratum['pkglist'] for p in pkg['packages']]
                original_pkg_count = len(original_pkg_objects)
                pkg_objects = self._find_filtered_erratum_packages(original_pkg_objects, whitelist_packages, blacklist_packages)
                if len(pkg_objects) != original_pkg_count:
                    errataids.remove(erratumid)
                    filtered_errata.append(erratumid)
                    log.info("Filtered errata : %s" % erratumid)
                else:
                    self._add_erratum(repo, erratumid)
        else:
            for erratumid in errataids:
                self._add_erratum(repo, erratumid)

        self.collection.save(repo, safe=True)
        self._update_errata_packages(repoid, errataids, action='add')
        updateinfo.generate_updateinfo(repo)
        return filtered_errata

    def _update_errata_packages(self, repoid, errataids=[], action=None):
        repo = self._get_existing_repo(repoid)
        addids = []
        rmids = []
        for erratumid in errataids:
            erratum = self.errataapi.erratum(erratumid)
            if erratum is None:
                log.info("No Erratum with id: %s found" % erratumid)
                continue

            for pkg in erratum['pkglist']:
                for pinfo in pkg['packages']:
                    if pinfo['epoch'] in ['None', None]:
                        epoch = '0'
                    else:
                        epoch = pinfo['epoch']
                    epkg = self.packageapi.package_by_ivera(pinfo['name'],
                                                            pinfo['version'],
                                                            epoch,
                                                            pinfo['release'],
                                                            pinfo['arch'])
                    if epkg:
                        addids.append(epkg['id'])
                        rmids.append(epkg)
        if action == 'add':
            self.add_package(repo['id'], addids)
        elif action == 'delete':
            self.remove_packages(repo['id'], rmids)

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
        if repo['id'] not in erratum['repoids']:
            erratum['repoids'].append(repo['id'])
            err_collection = model.Errata.get_collection()
            err_collection.save(erratum, safe=True)

    @audit()
    def delete_erratum(self, repoid, erratumid):
        """
        delete erratum from this repo
        """
        repo = self._get_existing_repo(repoid)
        self._delete_erratum(repo, erratumid)
        self.collection.save(repo, safe=True)
        self._update_errata_packages(repoid, [erratumid], action='delete')
        updateinfo.generate_updateinfo(repo)

    def delete_errata(self, repoid, errataids):
        """
        delete list of errata from this repo
        """
        repo = self._get_existing_repo(repoid)
        for erratumid in errataids:
            self._delete_erratum(repo, erratumid)
        self.collection.save(repo, safe=True)
        self._update_errata_packages(repoid, errataids, action='delete')
        updateinfo.generate_updateinfo(repo)

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
            if repo['id'] in erratum['repoids']:
                del erratum['repoids'][erratum['repoids'].index(repo['id'])]
                err_collection = model.Errata.get_collection()
                err_collection.save(erratum, safe=True)
        except Exception, e:
            raise PulpException("Erratum %s delete failed due to Error: %s" % (erratum['id'], e))

    def find_repos_by_errataid(self, errata_id):
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
        self.collection.save(repo, safe=True)
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
        self.collection.save(repo, safe=True)
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
        self.collection.save(repo, safe=True)
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
        self.collection.save(repo, safe=True)
        self._update_groups_metadata(repo["id"])

    def packagegroups(self, id, filter_missing_packages=False, filter_incomplete_groups=False):
        """
        Return list of PackageGroup objects in this Repo
        @param id: repo id
        @return: packagegroup or None
        """
        repo = self._get_existing_repo(id)
        pkggroups = repo['packagegroups']
        # Filter operations will restrict based on packages in this repo
        if filter_incomplete_groups or filter_missing_packages:
            # We are only filtering on the common group type of 'default_package_names'
            pkggroups = self._filter_package_groups(id, pkggroups, ["default_package_names"],
                                                    filter_missing_packages, filter_incomplete_groups)
        return pkggroups

    def _filter_package_groups(self, repo_id, pkggroups, types,
                               filter_missing_packages, filter_incomplete_groups):
        """
        Return package groups filtered so that packages not in repo are removed
        @param repo_id: repository id
        @param pkggroups: package group data
        @param types: package group types to process
        @param filter_missing_packages: if True will restrict returned groups to only packages in repo
        @param filter_incomplete_groups: if True will only return groups where every package is in repo
        """
        repo_pkgs = self.packages(repo_id)
        repo_pkg_names = [p["name"] for pid, p in repo_pkgs.items()]
        for grp_type in types:
            pkgs = []
            for grpid in pkggroups:
                for name in pkggroups[grpid][grp_type]:
                    pkgs.append((name, grpid))
            for name, grpid in pkgs:
                if name not in repo_pkg_names:
                    if filter_incomplete_groups:
                        if pkggroups.has_key(grpid):
                            del pkggroups[grpid]
                    elif filter_missing_packages:
                        pkggroups[grpid][grp_type].remove(name)
        return pkggroups

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
    def add_packages_to_group(self, repoid, groupid, pkg_names=(),
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
                    if pkg_name not in group["mandatory_package_names"]:
                        group["mandatory_package_names"].append(pkg_name)
            elif gtype == "conditional":
                if not requires:
                    raise PulpException("Parameter 'requires' has not been set, it is required by conditional group types")
                group["conditional_package_names"][pkg_name] = requires
            elif gtype == "optional":
                if pkg_name not in group["optional_package_names"]:
                    if pkg_name not in group["optional_package_names"]:
                        group["optional_package_names"].append(pkg_name)
            else:
                if pkg_name not in group["default_package_names"]:
                    if pkg_name not in group["default_package_names"]:
                        group["default_package_names"].append(pkg_name)
        self.collection.save(repo, safe=True)
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

        self.collection.save(repo, safe=True)
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
        self.collection.save(repo, safe=True)
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
        self.collection.save(repo, safe=True)
        self._update_groups_metadata(repo["id"])

    @audit()
    def delete_packagegroup_from_category(self, repoid, categoryid, groupid):
        repo = self._get_existing_repo(repoid)
        if categoryid in repo['packagegroupcategories']:
            if repo["packagegroupcategories"][categoryid]["immutable"]:
                raise PulpException(
                    "Changes to immutable categories are not supported: %s" \
                    % (categoryid))
            if groupid not in repo['packagegroupcategories'][categoryid]['packagegroupids']:
                raise PulpException(
                    "Group id [%s] is not in category [%s]" % \
                    (groupid, categoryid))
            repo['packagegroupcategories'][categoryid]['packagegroupids'].remove(groupid)
        self.collection.save(repo, safe=True)
        self._update_groups_metadata(repo["id"])

    @audit()
    def add_packagegroup_to_category(self, repoid, categoryid, groupid):
        repo = self._get_existing_repo(repoid)
        if categoryid in repo['packagegroupcategories']:
            if repo["packagegroupcategories"][categoryid]["immutable"]:
                raise PulpException(
                    "Changes to immutable categories are not supported: %s" \
                    % (categoryid))
        if groupid not in repo['packagegroupcategories'][categoryid]["packagegroupids"]:
            repo['packagegroupcategories'][categoryid]["packagegroupids"].append(groupid)
            self.collection.save(repo, safe=True)
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
        self.collection.save(repo, safe=True)
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
        self.collection.save(repo, safe=True)
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
                repo["group_xml_path"] = os.path.join(os.path.dirname(repo["repomd_xml_path"]),
                                                      "comps.xml")
                self.collection.save(repo, safe=True)
            f = open(repo["group_xml_path"], "w")
            f.write(xml.encode("utf-8"))
            f.close()
            return comps_util.update_repomd_xml_file(encode_unicode(repo["repomd_xml_path"]), encode_unicode(repo["group_xml_path"]))
        except Exception, e:
            log.warn("_update_groups_metadata exception caught: %s" % (e))
            log.warn("Traceback: %s" % (traceback.format_exc()))
            return False

    def list_syncs(self, id):
        """
        List all the syncs for a given repository.
        """
        return [task
                for task in find_async(method='_sync')
                if encode_unicode(id) in task.args]

    def get_sync_status_by_tasks(self, tasks):
        """
        Given a list of tasks, return a list of the repo sync statuses
        associated with those tasks.
        @param tasks: List of tasks
        @type tasks: list
        @return: List of of repo sync statuses
        @rtype: list of L{model.RepoStatus}
        """
        statuses = [self.get_sync_status_by_task(t) for t in tasks]
        # Not all tasks will have repo syncs associated with them yet, if
        # they're waiting for instance, so remove None values.
        statuses = [s for s in statuses if s is not None]
        return statuses

    def get_sync_status_by_task(self, task):
        """
        Given a task, return the repo sync statuses
        associated with that task.
        @param task: repo sync task
        @type tasks: L{pulp.server.api.repo_sync_task.RepoSyncTask}
        @return: repo sync status assocated with the task
        @rtype: L{model.RepoStatus}
        """
        # If there's no task.args, then we can't even look up the repo
        # associated with this task.
        if not task.args:
            return None

        # The repo id should always be the first argument of the task
        repo_id = task.args[0]
        repo_sync_status = model.RepoStatus(repo_id)

        repo_sync_status["state"] = task.state
        repo_sync_status["progress"] = task.progress
        repo_sync_status["state"] = task.state
        repo_sync_status["state"] = task_error
        repo_sync_status["exception"] = task.exception
        repo_sync_status["traceback"] = task.traceback

        return repo_sync_status

    def get_sync_status_for_repos(self, repos):
        """
        Get the sync status for a list of repos.
        @param repos: List of repos.
        @type repos: list of L{Repo}
        @return: List of repo sync statuses
        @rtype: list of L{model.RepoStatus}
        """
        statuses = [self.get_sync_status(r["id"]) for r in repos]
        return statuses

    def get_sync_status(self, id):
        """
        Get the sync status for a repo id.
        @param id: Repo id.
        @type id: int
        @return: repo sync status
        @rtype: L{model.RepoStatus}
        """
        # Look up the tasks for this repo id
        tasks = [t for t in find_async(method_name="_sync")
                 if (t.args and encode_unicode(id) in t.args) or
                 (t.kwargs and encode_unicode(id) in t.kwargs.values())]

        # Assume we only founds 1 task.
        if tasks:
            task = tasks[0]
        else:
            task = None

        repo_sync_status = model.RepoStatus(id)

        if task:
            repo_sync_status["state"] = task.state
            repo_sync_status["progress"] = task.progress
            repo_sync_status["exception"] = task.exception
            repo_sync_status["traceback"] = task.traceback

            if task.scheduled_time:
                repo_sync_status["next_sync_time"] = format_iso8601_datetime(
                    task.scheduled_time)

        return repo_sync_status

    @audit(params=['id', 'keylist'])
    def addkeys(self, id, keylist):
        repo = self._get_existing_repo(id)
        path = repo['relative_path']
        ks = KeyStore(path)
        added = ks.add(keylist)
        log.info('repository (%s), added keys: %s', id, added)

        # Retrieve the latest set of key names and contents and send to consumers
        gpg_keys = ks.keys_and_contents()
        self.update_gpg_keys_on_consumers(repo, gpg_keys)

        return added

    @audit(params=['id', 'keylist'])
    def rmkeys(self, id, keylist):
        repo = self._get_existing_repo(id)
        path = repo['relative_path']
        ks = KeyStore(path)
        deleted = ks.delete(keylist)
        log.info('repository (%s), delete keys: %s', id, deleted)

        # Retrieve the latest set of key names and contents and send to consumers
        gpg_keys = ks.keys_and_contents()
        self.update_gpg_keys_on_consumers(repo, gpg_keys)

        return deleted

    def listkeys(self, id):
        repo = self._get_existing_repo(id)
        path = repo['relative_path']
        ks = KeyStore(path)
        return ks.list()

    def update_repo_on_consumers(self, repo):
        '''
        Notifies all consumers bound to the given repo that the repo metadata has
        changed. This only refers to data on the repo itself, not its GPG keys or
        host URLs.

        @param repo: repo object containing the full data for the repo, not just the
                     changes
        @type  repo: L{Repo}
        '''
        consumers = consumer_utils.consumers_bound_to_repo(repo['id'])
        bind_data = consumer_utils.build_bind_data(repo, None, None)

        # Blank out the values that haven't changed
        bind_data['host_urls'] = None
        bind_data['gpg_keys'] = None

        # For each consumer, retrieve its proxy and send the update request
        for consumer in consumers:
            agent = PulpAgent(consumer, async=True)
            repo_proxy = agent.Repo()
            repo_proxy.update(repo['id'], bind_data)

    def update_gpg_keys_on_consumers(self, repo, gpg_keys):
        '''
        Notifies all consumers bound to the given repo that the GPG keys for the
        repo have changed. The full set of current keys on the repo will be
        sent to consumers. The repo object itself will not be sent.

        @param repo: repo object containing the full data for the repo, not just the
                     changes
        @type  repo: L{Repo}

        @param gpg_keys: mapping of key name to contents; this should contain the
                         full listing of keys for the repo, not just changed keys
        @type  gpg_keys: dict {string : string}
        '''

        consumers = consumer_utils.consumers_bound_to_repo(repo['id'])
        bind_data = consumer_utils.build_bind_data(repo, None, gpg_keys)

        # Blank out the values that haven't changed
        bind_data['host_urls'] = None
        bind_data['repo'] = None

        # For each consumer, retrieve its proxy and send the update request
        for consumer in consumers:
            agent = PulpAgent(consumer, async=True)
            repo_proxy = agent.Repo()
            repo_proxy.update(repo['id'], bind_data)

    def all_schedules(self):
        '''
        For all repositories, returns a mapping of repository name to sync schedule.

        @rtype:  dict
        @return: key - repo name, value - sync schedule
        '''
        return dict((r['id'], r['sync_schedule']) for r in self.repositories())

    def add_distribution(self, repoid, distroid):
        """
         Associate a distribution to a given repo
         @param repoid: The repo ID.
         @type repoid: str
         @param distroid: The distribution ID.
         @type distroid: str
        """
        repo = self._get_existing_repo(repoid)
        distro_obj = self.distroapi.distribution(distroid)
        if distro_obj is None:
            raise PulpException("Distribution ID [%s] does not exist" % distroid)
        repo['distributionid'].append(distroid)
        self.collection.save(repo, safe=True)

        # Add the repoid to the list on the distribution as well.
        distro_obj = self.distroapi.distribution(distroid)
        distro_obj['repoids'].append(repoid)
        distro_collection = model.Distribution.get_collection()
        distro_collection.save(distro_obj, safe=True)
        
        distro_path = "%s/%s" % (pulp.server.util.top_distribution_location(), distroid)
        repo_path = os.path.join(pulp.server.util.top_repos_location(), repo['relative_path'])
        for imfile in distro_obj['files']:
            if not os.path.exists(imfile):
                log.error("distribution file [%s] missing from the filesystem; skipping")
                continue
            if os.path.basename(imfile) in ['treeinfo', '.treeinfo']:
                repo_treefile_path = os.path.join(repo_path, os.path.basename(imfile))
                if not os.path.islink(repo_treefile_path):
                    pulp.server.util.create_rel_symlink(imfile, repo_treefile_path)
            else:
                repo_dist_path = "%s/%s/%s" % (repo_path, "images", imfile.split(distro_path)[-1])
                if not os.path.islink(repo_dist_path):
                    pulp.server.util.create_rel_symlink(imfile, repo_dist_path)
        if repo['publish']:
            self._create_ks_link(repo)
        log.info("Successfully added distribution %s to repo %s" % (distroid, repoid))

    def remove_distribution(self, repoid, distroid):
        """
         Delete a distribution from a given repo
         @param repoid: The repo ID.
         @param distroid: The distribution ID.
        """
        repo = self._get_existing_repo(repoid)
        if not distroid in repo['distributionid']:
            log.error("No Distribution with ID %s associated to this repo" % distroid)
        distro_obj = self.distroapi.distribution(distroid)
        if distro_obj is None:
            log.error("Distribution ID [%s] does not exist" % distroid)
            return
        distro_path = "%s/%s" % (pulp.server.util.top_distribution_location(), distroid)
        repo_path = os.path.join(pulp.server.util.top_repos_location(), repo['relative_path'])
        for imfile in distro_obj['files']:
            if os.path.basename(imfile) in ['treeinfo', '.treeinfo']:
                repo_treefile_path = os.path.join(repo_path, os.path.basename(imfile))
                repo_treefile_path = encode_unicode(repo_treefile_path)
                if os.path.islink(repo_treefile_path):
                    os.unlink(repo_treefile_path)
            else:
                repo_dist_path = "%s/%s/%s" % (repo_path, "images", imfile.split(distro_path)[-1])
                repo_dist_path = encode_unicode(repo_dist_path)
                if os.path.islink(repo_dist_path):
                    os.unlink(repo_dist_path)
        del repo['distributionid'][repo['distributionid'].index(distroid)]
        self.collection.save(repo, safe=True)

        if repoid in distro_obj['repoids']:
            # Delete the repoid from the list on the distribution as well.
            del distro_obj['repoids'][distro_obj['repoids'].index(repoid)]
            distro_collection = model.Distribution.get_collection()
            distro_collection.save(distro_obj, safe=True)

        log.info("Successfully removed distribution %s from repo %s" % (distroid, repoid))
        self._delete_ks_link(repo)

    def _create_ks_link(self, repo):
        if not os.path.isdir(self.distro_path):
            pulp.server.util.makedirs(self.distro_path)
        source_path = os.path.join(pulp.server.util.top_repos_location(),
                                   repo["relative_path"])
        if not os.path.isdir(source_path):
            pulp.server.util.makedirs(source_path)
        link_path = os.path.join(self.distro_path, repo["relative_path"])
        log.info("Linking %s" % link_path)
        pulp.server.util.create_rel_symlink(source_path, link_path)

    def _delete_ks_link(self, repo):
        link_path = os.path.join(self.distro_path, repo["relative_path"])
        log.info("Unlinking %s" % link_path)
        link_path = encode_unicode(link_path)
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

    def get_file_checksums(self, data):
        '''
        Fetch the package checksums and filesizes
        @param data: {"repo_id1": ["file_name", ...], "repo_id2": [], ...}
        @return  {"repo_id1": {"file_name": {'checksum':...},...}, "repo_id2": {..}}
        '''
        result = {}
        for repoid, filenames in data.items():
            repo = self._get_existing_repo(repoid)
            fchecksum = {}
            for fname in filenames:
                filedata = self.packageapi.package_checksum(fname)
                if filedata:
                    fchecksum[fname] = filedata[0]['checksum']
                else:
                    fchecksum[fname] = None
            result[repoid] = fchecksum
        return result

    @event(subject='repo.updated.content')
    @audit()
    def add_file(self, repoid, fileids=[]):
        '''
         Add a file to a repo
         @param repoid: The repo ID.
         @param fileid: file ID.
        '''
        repo = self._get_existing_repo(repoid)
        changed = False
        for fid in fileids:
            fileobj = self.fileapi.file(fid)
            if fileobj is None:
                log.error("File ID [%s] does not exist" % fid)
                continue
            if fid not in repo['files']:
                repo['files'].append(fid)
                changed = True
                shared_file = "%s/%s/%s/%s/%s" % (pulp.server.util.top_file_location(), fileobj['filename'][:3],
                                                  fileobj['filename'],fileobj['checksum']['sha256'], fileobj['filename'])
                file_repo_path = "%s/%s/%s" % (pulp.server.util.top_repos_location(),
                                               repo['relative_path'], fileobj["filename"])
                if not os.path.exists(file_repo_path):
                    try:
                        pulp.server.util.create_symlinks(shared_file, file_repo_path)
                    except OSError:
                        log.error("Link %s already exists" % file_repo_path)
        self.collection.save(repo, safe=True)
        if changed:
            self._generate_file_manifest(repo)
        log.info("Successfully added files %s to repo %s" % (fileids, repoid))

    @event(subject='repo.updated.content')
    @audit()
    def remove_file(self, repoid, fileids=[]):
        '''
         remove a file from a given repo
         @param repoid: The repo ID.
         @param fileid: file ID.
        '''
        repo = self._get_existing_repo(repoid)
        changed = False
        for fid in fileids:
            fileobj = self.fileapi.file(fid)
            if fileobj is None:
                log.error("File ID [%s] does not exist" % fid)
                continue
            if fid in repo['files']:
                del repo['files'][repo['files'].index(fid)]
                changed = True
                # Remove package from repo location on file system
                file_repo_path = "%s/%s/%s" % (pulp.server.util.top_repos_location(),
                                               repo['relative_path'], fileobj["filename"])
                if os.path.exists(file_repo_path):
                    log.debug("Delete file %s at %s" % (fileobj["filename"], file_repo_path))
                    os.remove(file_repo_path)
        self.collection.save(repo, safe=True)
        if changed:
            self._generate_file_manifest(repo)
        log.info("Successfully removed file %s from repo %s" % (fileids, repoid))

    def _generate_file_manifest(self, repo):
        """
         generate a file manifest for all files in a repo
         @param repo: The repo object.
        """
        fileids = repo['files']
        try:
            manifest_path = "%s/%s/%s" % (pulp.server.util.top_repos_location(), repo['relative_path'], "PULP_MANIFEST")
            f = open(manifest_path, "w")
            for fileid in fileids:
                fileobj = self.fileapi.file(fileid)
                if fileobj is None:
                    log.error("File ID [%s] does not exist" % fileid)
                    continue
                write_str = "%s,%s,%s\n" % (fileobj['filename'], fileobj['checksum']['sha256'], \
                                            fileobj['size'] or 0)
                f.write(write_str)
            f.close()
        except:
            log.error("Error creating manifest for repo [%s]" % repo['id'])

    def list_files(self, repoid):
        '''
         List files in a given repo
         @param repoid: The repo ID.
         @return list: file objects.
        '''
        repo = self._get_existing_repo(repoid)
        files = []
        for fileid in repo['files']:
            fileobj = self.fileapi.file(fileid)
            if not fileobj:
                continue
            files.append(fileobj)
        return files

    def find_repos_by_files(self, fileid):
        """
        Return repos that contain passed in file id
        @param pkgid: file id
        """
        found = self.collection.find({"files":fileid}, fields=["id"])
        return [r["id"] for r in found]

    @audit(params=['id', 'filter_ids'])
    def add_filters(self, id, filter_ids):
        repo = self._get_existing_repo(id)
        if repo['source'] and repo['source']['type'] != 'local':
            raise PulpException("Filters can be added to repos with 'local' feed only")
        for filter_id in filter_ids:
            filter = self.filterapi.filter(filter_id)
            if filter is None:
                raise PulpException("No Filter with id: %s found" % filter_id)

        filters = repo['filters']
        for filter_id in filter_ids:
            if filter_id in filters:
                continue
            filters.append(filter_id)

        repo["filters"] = filters
        self.collection.save(repo, safe=True)
        log.info('repository (%s), added filters: %s', id, filter_ids)

    @audit(params=['id', 'filter_ids'])
    def remove_filters(self, id, filter_ids):
        repo = self._get_existing_repo(id)
        filters = repo['filters']
        for filter_id in filter_ids:
            if filter_id not in filters:
                continue
            filters.remove(filter_id)

        repo["filters"] = filters
        self.collection.save(repo, safe=True)
        log.info('repository (%s), removed filters: %s', id, filter_ids)

    @audit(params=['id', 'addgrp'])
    def add_group(self, id, addgrp):
        repo = self._get_existing_repo(id)
        groupids = repo['groupid']
        if addgrp not in groupids:
            groupids.append(addgrp)
        repo["groupid"] = groupids
        self.collection.save(repo, safe=True)
        log.info('repository (%s), added group: %s', id, addgrp)

    @audit(params=['id', 'rmgrp'])
    def remove_group(self, id, rmgrp):
        repo = self._get_existing_repo(id)
        groupids = repo['groupid']
        if rmgrp in groupids:
            groupids.remove(rmgrp)

        repo["groupid"] = groupids
        self.collection.save(repo, safe=True)
        log.info('repository (%s), removed group: %s', id, rmgrp)

    def list_filters(self, id):
        repo = self._get_existing_repo(id)
        return repo['filters']

    def _translate_filename_checksum_pairs(self, pkg_infos):
        """
        Translates a list of filename/checksum structures to a list of package ids.
        @param pkg_infos: format is [((filename, checksum), [repoids])]
        @return:    {'repo_id':[pkgids]}, {errors}
        """
        start_translate = time.time()
        p_col = model.Package.get_collection()
        repo_pkgs = {}
        errors = {}
        for item in pkg_infos:
            filename = item[0][0]
            checksum = item[0][1]
            repos = item[1]
            found = p_col.find_one({"filename":filename, "checksum.sha256":checksum}, {"id":1})
            #Lookup package id from returned mongo results
            if not found:
                log.error("Unable to find package id for filename=%s, checksum=%s" % (filename, checksum))
                if not errors.has_key(filename):
                    errors[filename] = {}
                if not errors[filename].has_key(checksum):
                    errors[filename][checksum] = [repos]
                else:
                    errors[filename][checksum].append(repos)
                continue
            pkg_id = found["id"]
            # Build up a list per repository of package ids we want to add
            for r_id in repos:
                if not repo_pkgs.has_key(r_id):
                    repo_pkgs[r_id] = [pkg_id]
                else:
                    repo_pkgs[r_id].append(pkg_id)
        end_translate = time.time()
        log.info("Translated %s filename,checksums in %s seconds" % (len(pkg_infos), end_translate - start_translate))
        return repo_pkgs, errors

    def associate_packages(self, pkg_infos):
        """
        Associates a list of packages to multiple repositories.
        Each package is identified by it's (filename,checksum)
        @param pkg_infos: format is [((filename,checksum), [repoids])]
        @return:    [] on success
                    or {"filename":{"checksum":[repoids]} on error
        """
        repo_pkgs, errors = self._translate_filename_checksum_pairs(pkg_infos)
        for repo_id in repo_pkgs:
            start_time = time.time()
            add_pkg_errors, filtered_count = self.add_package(repo_id, repo_pkgs[repo_id])
            for e in add_pkg_errors:
                filename = e[2]
                checksum = e[3]
                if not errors.has_key(filename):
                    errors[filename] = {}
                if not errors[filename].has_key(checksum):
                    errors[filename][checksum] = [repo_id]
                elif repo_id not in errors[filename][checksum]:
                    errors[filename][checksum].append(repo_id)
            end_time = time.time()
            log.info("repo.associate_packages(%s) for %s packages took %s seconds" % (repo_id, len(repo_pkgs[repo_id]), end_time - start_time))
        return errors

    def disassociate_packages(self, pkg_infos):
        """
        Disassociates a list of packages to multiple repositories.
        Each package is identified by it's (filename,checksum)
        @param pkg_infos: format is [((filename,checksum), [repoids])]
        @return:    [] on success
                    or {"filename":{"checksum":[repoids]} on error
        """
        repo_pkgs, errors = self._translate_filename_checksum_pairs(pkg_infos)
        for repo_id in repo_pkgs:
            start_time = time.time()
            pkgids = repo_pkgs[repo_id]
            to_remove_pkgs = self.packageapi.packages_by_id(pkgids)
            to_remove_pkgs = to_remove_pkgs.values()
            rm_pkg_errors = self.remove_packages(repo_id, to_remove_pkgs)
            for p in rm_pkg_errors:
                filename = p["filename"]
                checksum = p["checksum"].values()[0]
                if not errors.has_key(filename):
                    errors[filename] = {}
                if not errors[filename].has_key(checksum):
                    errors[filename][checksum] = [repo_id]
                elif repo_id not in errors[filename][checksum]:
                    errors[filename][checksum].append(repo_id)
            end_time = time.time()
            log.info("repo.disassociate_packages(%s) for %s packages took %s seconds" % (repo_id, len(repo_pkgs[repo_id]), end_time - start_time))
        return errors

    def generate_metadata(self, id):
        """
         spawn repo metadata generation for a specific repo
         @param id: repository id
         @return task:
        """
        if self.list_metadata_task(id):
            # repo generation task already pending; task not created
            return None
        task = run_async(self._generate_metadata, [id], {})
        return task

    @event(subject='repo.updated.content')
    def _generate_metadata(self, id):
        """
         spawn repo metadata generation for a specific repo
         @param id: repository id
        """
        repo = self._get_existing_repo(id)
        if repo['preserve_metadata']:
            msg = "Metadata for repo [%s] is set to be preserved. Cannot re-generate metadata" % id
            log.info(msg)
            raise PulpException(msg)
        repo_path = os.path.join(
            pulp.server.util.top_repos_location(), repo['relative_path'])
        if not os.path.exists(repo_path):
            pulp.server.util.makedirs(repo_path)
        log.info("Spawning repo metadata generation for repo [%s] with path [%s]" % (repo['id'], repo_path))
        if repo['content_types'] in ('yum'):
            repo_path = encode_unicode(repo_path)
            pulp.server.util.create_repo(repo_path, checksum_type=repo["checksum_type"])
        elif repo['content_types'] in ('file'):
            self._generate_file_manifest(repo)
        else:
            raise PulpException("Cannot spawn metadata generation for repo with content type %s" % repo['content_types'])

    def list_metadata_task(self, id):
        """
        List all the metadata tasks for a given repository.
        """
        return [task
                for task in find_async(method='_generate_metadata')
                if encode_unicode(id) in task.args]

    def set_sync_in_progress(self, id, state):
        """
        @type id: string
        @param id: repository id
        @type state: bool
        @param state:   boolean state requested.
                        True means we want to set sync in progress
                        False means we want to clear sync in progress
        @rtype: bool
        @return:    True - requested state was set
                    False - requested state was _not_ set
        """
        try:
            locked = self.__sync_lock.acquire()
            repo = self.collection.find_one({"id":id}, {"sync_in_progress":1})
            if not repo:
                log.error("no repo exists for [%s]" % (id))
                return False
            if repo.has_key("sync_in_progress") and repo["sync_in_progress"]:
                # This repository is currently being synchronized
                if state:
                    return False
                self.collection.update({"id":id}, {"$set": {"sync_in_progress":False}})
                return True
            # This repository is _not_ currently being synchronized
            self.collection.update({"id":id}, {"$set": {"sync_in_progress":state}})
            return True
        finally:
            #bz700508 - fast sync/cancel_sync locks up task subsystem
            # Tasking system may inject multiple CancelExceptions into this thread
            # we have seen sometimes the CancelException will be injected while we are
            # trying to clean up a repo sync.
            # Intent is to loop over the release of __sync_lock in case we are interrupted while trying to unlock it.
            # Desired behavior is that we will always ensure __sync_lock is released prior to exiting this function.
            while locked:
                try:
                    self.__sync_lock.release()
                    locked = False
                except RuntimeError:
                    # lock.release() could throw a RuntimeError if we didn't own the lock
                    # allow this to be raised
                    raise
                except Exception, e:
                    # suppress all other exceptions and retry
                    log.error("Exception: %s" % (e))
                    log.error("Traceback: %s" % (traceback.format_exc()))


    def sync_history(self, id, limit=None, sort='descending'):
        '''
        Queries repo sync history.

        @param id: repo id
        @type  id: string

        @param limit: if specified, the query will only return up to this amount of
                      entries; default is to not limit the entries returned
        @type  limit: number greater than zero

        @return: list of completed syncs for given repo;
                 empty list (not None) if no matching entries are found
        @rtype:

        @raise PulpException: if any of the input values are invalid
        '''

        # Verify the limit makes sense
        if limit is not None and limit < 1:
            raise PulpException('Invalid limit [%s], limit must be greater than zero' % limit)

        tasks = find_async(method_name="_sync", repo_id=id)

        if limit is not None:
            sync_history_list = [task.__dict__ for task in tasks[:limit]]
        else:
            sync_history_list = [task.__dict__ for task in tasks]
        return sync_history_list

    def add_metadata(self, id, metadata):
        '''
        Add custom metadata to a repo
        @param id: repo id
        @type  id: string
        @param metadata: custom metadata dict; eg: {'filetype' : 'productid', 'filedata' : data_stream}
        @type metadata: dictionary
        @raise PulpException: if any of the input values are invalid
        '''
        repo = self._get_existing_repo(id)
        repo_path = os.path.join(
            pulp.server.util.top_repos_location(), repo['relative_path'])
        repo_metdata_dir = "%s/%s" % (repo_path, "repodata")
        # if there is no repodata dir, then its probably not a yum repo; exit now
        if not os.path.exists(repo_metdata_dir):
            msg = "No repodata found for repo [%s]; Cannot perform add metadata on a non yum repo" % id
            log.info(msg)
            raise PulpException(msg)

        if repo['preserve_metadata']:
            msg = "Metadata for repo [%s] is set to be preserved. Cannot add custom metadata" % id
            log.info(msg)
            raise PulpException(msg)
        # write the metadata to a file
        custom_path = "%s/%s" % (repo_path, metadata['filetype'])
        if os.path.exists(custom_path):
            # if there is an older file, nuke it and start fresh
            os.remove(custom_path)
        try:
            custom_obj = open(custom_path, 'wb')
            custom_obj.write(metadata['filedata'])
            custom_obj.close()
        except:
            msg = "Unable to write custom metadata for repo [%s]" % id
            log.info(msg)
            raise PulpException(msg)
        # now run modify repo and add the metadata to yum
        pulp.server.util.modify_repo(repo_metdata_dir, custom_path)

    def list_metadata(self, id):
        '''
        list metadata filetype information from a repo
        @param id: repo id
        @type  id: string
        @raise PulpException: if any of the input values are invalid
        @return: dump of all the filetypes in repo metadata
        @rtype: dict
        '''
        repo = self._get_existing_repo(id)
        repo_path = os.path.join(
            pulp.server.util.top_repos_location(), repo['relative_path'])
        repodata_file = "%s/%s" % (repo_path, "repodata/repomd.xml")
        dump = pulp.server.util.get_repomd_filetype_dump(repodata_file)
        return dump

    def get_metadata(self, id, filetype):
        '''
        get an xml dump of the matched filetype from a repo
        @param id: repo id
        @type  id: string
        @param filetype: file type to look up in metadata
        @type  filetype: string
        @return: metadata stream if found or None if no match
        @rtype: string
        '''
        repo = self._get_existing_repo(id)
        repo_path = os.path.join(
            pulp.server.util.top_repos_location(), repo['relative_path'])
        repo_repomd_path = "%s/%s" % (repo_path, "repodata/repomd.xml")
        #return pulp.server.util.get_repomd_filetype_xml(repo_repomd_path, filetype)
        file_path = pulp.server.util.get_repomd_filetype_path(repo_repomd_path, filetype)
        if not file_path:
            return None
        metadata_file = os.path.join(repo_path, file_path)
        try:
            f = metadata_file.endswith('.gz') and gzip.open(metadata_file) \
                or open(metadata_file, 'rt')
            return f.read().decode("utf-8", "replace")
        except Exception, e:
            msg = "Error [%s] reading the metadata file for type [%s] at location [%s]" % (str(e), filetype, file_path)
            log.info(msg)
            raise PulpException(msg)

    def remove_metadata(self, id, filetype):
        '''
        remove a metadata file from a repo
        @param id: repo id
        @type  id: string
        @param filetype: file type to look up in metadata
        @type  filetype: string
        @raise PulpException: if any of the input values are invalid
        '''
        repo = self._get_existing_repo(id)
        repo_path = os.path.join(
            pulp.server.util.top_repos_location(), repo['relative_path'])
        repo_repomd_path = "%s/%s" % (repo_path, "repodata/repomd.xml")
        file_path = pulp.server.util.get_repomd_filetype_path(repo_repomd_path, filetype)
        if not file_path:
            msg = "metadata file of type [%s] cannot be found in repository [%s]" % (filetype, id)
            log.info(msg)
            raise PulpException(msg)
        try:
            pulp.server.util.modify_repo(os.path.dirname(repo_repomd_path), filetype, remove=True)
        except Exception, e:
            msg = "Error [%s] removing the metadata file for type [%s]" % (str(e), filetype)
            log.info(msg)
            raise PulpException(msg)

    
    @audit()
    def add_note(self, id, key, value):
        """
        Add note to a repo in the form of key-value pairs.
        @param id: repo id.
        @type id: str
        @param key: key
        @type key: str
        @param value: value
        @type value: str
        @raise PulpException: When repo is not found or given key exists.
        """
        repo = self.repository(id)
        if not repo:
            raise PulpException('Repository [%s] does not exist', id)
        key_value_pairs = repo['notes']
        if key not in key_value_pairs.keys():
            key_value_pairs[key] = value
        else:
            raise PulpException('Given key [%s] already exists', key)
        repo['notes'] = key_value_pairs
        self.collection.save(repo, safe=True)

    @audit()
    def delete_note(self, id, key):
        """
        Delete key-value note from a repo.
        @param id: repo id.
        @type id: str
        @param key: key
        @type key: str
        @raise PulpException: When repo does not exist or key is not found.
        """
        repo = self.repository(id)
        if not repo:
            raise PulpException('Repository [%s] does not exist', id)
        key_value_pairs = repo['notes']
        if key in key_value_pairs.keys():
            del key_value_pairs[key]
        else:
            raise PulpException('Given key [%s] does not exist', key)
        repo['notes'] = key_value_pairs
        self.collection.save(repo, safe=True)

    @audit()
    def update_note(self, id, key, value):
        """
        Update key-value note of a repo.
        @param id: repo id.
        @type id: str
        @param key: key
        @type key: str
        @param value: value
        @type value: str
        @raise PulpException: When repo is not found or given key exists.
        """
        repo = self.repository(id)
        if not repo:
            raise PulpException('Repository [%s] does not exist', id)
        key_value_pairs = repo['notes']
        if key not in key_value_pairs.keys():
            raise PulpException('Given key [%s] does not exist', key)
        else:
            key_value_pairs[key] = value
        repo['notes'] = key_value_pairs
        self.collection.save(repo, safe=True)

    def has_parent(self, id):
        """
        Check if a repo has a parent
        @param id: repository Id
        @return: True if success; else False
        """
        parent_repos = self.repositories({'clone_ids' : id})
        if len(parent_repos):
            return True
        return False
 
def validate_relative_path(new_path, existing_path):
    """
    Checks that the proposed new relative path will not conflict with an
    existing path.

    The primary source of contention is if the new repository
    would cause the two repositories to be nested. In other words, given
    an existing repository with relative path foo/bar, a repository should not
    be created inside of that directory, for example foo/bar/baz. The opposite
    holds true as well; if foo/bar/baz exists, a new repository at foo/bar
    should not be allowed.

    This call will apply both directions of logic and return true or false to
    indicate whether or not the new path is valid given the existing repository.

    @param new_path: propsed relative path for a newly created repository
    @type  new_path: str

    @param existing_path: relative path of a existing repository in Pulp
    @type  existing_path: str

    @return: True if the new path does not conflict with the existing path; False otherwise
    @rtype:  bool
    """
    # Easy out clause: if they are the same, they are invalid
    existing_path = decode_unicode(existing_path)
    new_path = decode_unicode(new_path)

    if new_path == existing_path:
        return False


    # If both paths are in the same parent directory but have different
    # names, we're safe
    new_path_dirname = os.path.dirname(new_path)
    existing_path_dirname = os.path.dirname(existing_path)

    if new_path_dirname == existing_path_dirname:
        return True

    # See if either path is a parent of the other. This is safe from the case of
    # /foo/bar and /foo/bar2 since the above check will have punched out early
    # if this was the case. If the above check wasn't there, this example would
    # reflect as invalid when in reality it is safe.
    
    if existing_path.startswith(new_path):
        log.warn('New relative path [%s] is a parent directory of existing path [%s]' % (new_path, existing_path))
        return False

    if new_path.startswith(existing_path):
        log.warn('New relative path [%s] is nested in existing path [%s]' % (existing_path, new_path))
        return False

    # If we survived the parent/child tests, the new path is safe
    return True
