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
import gzip
from optparse import OptionParser
import os
import shutil
import traceback
from datetime import datetime
from itertools import chain
from urlparse import urlparse

# Pulp
from pulp.server import comps_util
from pulp.server import crontab
from pulp.server import upload
from pulp.server.api import repo_sync
from pulp.server.api.base import BaseApi
from pulp.server.api.package import PackageApi
from pulp.server.api.errata import ErrataApi
from pulp.server.auditing import audit
from pulp.server.event.dispatcher import event
from pulp.server import config
from pulp.server.db import model
from pulp.server.db.connection import get_object_db
from pulp.server.pexceptions import PulpException
from pulp.server.api.fetch_listings import CDNConnection

log = logging.getLogger(__name__)

repo_fields = model.Repo(None, None, None).keys()

class RepoApi(BaseApi):
    """
    API for create/delete/syncing of Repo objects
    """

    def __init__(self):
        BaseApi.__init__(self)
        self.packageApi = PackageApi()
        self.errataapi = ErrataApi()
        self.localStoragePath = config.config.get('paths', 'local_storage')

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

    @event(subject='repo.created')
    @audit(params=['id', 'name', 'arch', 'feed'])
    def create(self, id, name, arch, feed=None, symlinks=False, sync_schedule=None,
               cert_data=None, groupid=None, relative_path=None):
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
            r['groupid'].append(groupid)

        if relative_path is None:
            if r['source'] is not None :
                # For none product repos, default to repoid
                url_parse = urlparse(str(r['source']["url"]))
                r['relative_path'] = url_parse.path
            else:
                r['relative_path'] = r['id']
        else:
            r['relative_path'] = relative_path
        self.insert(r)

        if sync_schedule:
            repo_sync.update_schedule(r)

        return r

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
                self.update(repo)
            except:
                log.error("Error creating repo %s for product %s" % (label, groupid))
                continue

        serv.disconnect()
        
    def delete_product_repo(self, content_set, cert_data, groupid=None):
        """
         delete repos associated to a product. Usually through an event raised
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
                repo = self.delete(label)
            except:
                raise
                log.error("Error deleting repo %s for product %s" % (label, groupid))
                continue

        serv.disconnect()

    @audit()
    def delete(self, id):
        repo = self._get_existing_repo(id)
        repo_sync.delete_schedule(repo)
        log.error("Delete API call invoked %s" % repo)
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
                    log.error("removing repo files .... %s" % fpath)
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
        """
        repo = self._get_existing_repo(id)
        packages = repo['packages']
        # XXX this is WRONG!!!!, we are returning a dict if name is None
        # otherwise we are returning a list!
        if name is None:
            return packages
        return [p for p in packages.values() if p['name'].find(name) >= 0]

    def package_count(self, id):
        """
        Return the number of packages in a repository.
        @type id: str
        @param id: repository id
        @rtype: int
        @return: the number of package in the repository corresponding to id
        """
        packages = self.packages(id)
        return len(packages)

    def get_package(self, id, name):
        """
        Return matching Package object in this Repo
        """
        packages = self.packages(id, name)
        if not packages:
            return None
        return packages[0]

    @audit()
    def add_package(self, repoid, packageid):
        """
        Adds the passed in package to this repo
        """
        repo = self._get_existing_repo(repoid)
        package = self.packageApi.package(packageid)
        if package is None:
            raise PulpException("No Package with id: %s found" % packageid)
        # TODO:  We might want to restrict Packages we add to only
        #        allow 1 NEVRA per repo and require filename to be unique
        self._add_package(repo, package)
        self.update(repo)

    def _add_package(self, repo, p):
        """
        Responsible for properly associating a Package to a Repo
        """
        packages = repo['packages']
        if p['id'] in packages:
            # No need to update repo, this Package is already under this repo
            return
        packages[p['id']] = p

    @audit()
    def remove_package(self, repoid, p):
        repo = self._get_existing_repo(repoid)
        # this won't fail even if the package is not in the repo's packages
        repo['packages'].pop(p['id'], None)
        self.update(repo)

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
        self.update(repo)

    def add_errata(self, repoid, errataids=()):
        """
         Adds a list of errata to this repo
        """
        repo = self._get_existing_repo(repoid)
        for erratumid in errataids:
            self._add_erratum(repo, erratumid)
        self.update(repo)

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
        self.update(repo)

    def delete_errata(self, repoid, errataids):
        """
        delete list of errata from this repo
        """
        repo = self._get_existing_repo(repoid)
        for erratumid in errataids:
            self._delete_erratum(repo, erratumid)
        self.update(repo)

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
        except Exception, e:
            raise PulpException("Erratum %s delete failed due to Error: %s" % (erratum['id'], e))

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
        if group_id in repo['packagegroups']:
            raise PulpException("Package group %s already exists in repo %s" %
                                (group_id, repoid))
        group = model.PackageGroup(group_id, group_name, description)
        repo["packagegroups"][group_id] = group
        self.update(repo)
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
            return
        if repo['packagegroups'][groupid]["immutable"]:
            raise PulpException("Changes to immutable groups are not supported: %s" % (groupid))
        del repo['packagegroups'][groupid]
        self.update(repo)
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
        self.update(repo)
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
        self.update(repo)
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
    def add_packages_to_group(self, repoid, groupid, pkg_names=[], gtype="default"):
        """
        @param repoid: repository id
        @param groupid: group id
        @param pkg_names: package names
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

        '''
        Find packages non existent in this repo.
        Repo does not have direct references to package names. The way we find this is 
        to get all package-ids with this pkg name and verify whether at least one of them
        exists in the given repo
        '''
        non_existing_pkgs = []
        for pkg_name in pkg_names:
            pkgs = self.packageApi.packages(name=pkg_name)
            if len(pkgs) == 0:
                non_existing_pkgs.append(pkg_name)
            else:    
                package_present_in_repo = 0    
                for pkg in pkgs:
                    if pkg['id'] in repo['packages']:
                        package_present_in_repo = 1
                        break
                if package_present_in_repo == 0:
                    non_existing_pkgs.append(pkg_name)
                else:
                    if gtype == "mandatory":
                        if pkg_name not in group["mandatory_package_names"]:
                            group["mandatory_package_names"].append(pkg_name)
                    elif gtype == "conditional":
                        raise NotImplementedError("No support for creating conditional groups")
                    elif gtype == "optional":
                        if pkg_name not in group["optional_package_names"]:
                            group["optional_package_names"].append(pkg_name)
                    else:
                        if pkg_name not in group["default_package_names"]:
                            group["default_package_names"].append(pkg_name)
        self.update(repo)
        self._update_groups_metadata(repo["id"])
        if len(non_existing_pkgs) > 0:
            raise PulpException("Packages added to the group except for following packages \
 which don't exist in this repo: %s" % non_existing_pkgs)


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

        '''
        Repo does not have direct references to package names. The way we find whether package exists 
        in this repo is to get all package-ids with this pkg name and verify whether at least one of them 
        exists in the given repo.                                                                    
        '''

        pkgs = self.packageApi.packages(name=pkg_name)
        if len(pkgs) == 0:
            raise PulpException("Package %s not present in this repo" % pkg_name)
        else:
            present = 0
            for pkg in pkgs:
                if pkg['id'] in repo['packages']:
                    present = 1
                    break
            if present == 0:
                raise PulpException("Package %s not present in this repo" % pkg_name)
            else:
                if gtype == "mandatory":
                    if pkg_name in group["mandatory_package_names"]:
                        group["mandatory_package_names"].remove(pkg_name)
                elif gtype == "conditional":
                    raise NotImplementedError("No support for creating conditional groups")
                elif gtype == "optional":
                    if pkg_name in group["optional_package_names"]:
                        group["optional_package_names"].remove(pkg_name)
                else:
                    if pkg_name in group["default_package_names"]:
                        group["default_package_names"].remove(pkg_name)
        self.update(repo)
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
        self.update(repo)
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
        self.update(repo)
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
        self.update(repo)
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
                log.debug("Skipping update of groups metadata since missing repomd file: '%s'" %
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
            log.debug("_update_groups_metadata exception caught: %s" % (e))
            log.debug("Traceback: %s" % (traceback.format_exc()))
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
            if pid not in sync_packages:
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
        pkg_upload = upload.PackageUpload(repo, pkginfo, pkgstream)
        pkg, repo = pkg_upload.upload()
        self._add_package(repo, pkg)
        self.update(repo)
        log.info("Upload success %s %s" % (pkg['id'], repo['id']))
        return True

    def all_schedules(self):
        '''
        For all repositories, returns a mapping of repository name to sync schedule.
        
        @rtype:  dict
        @return: key - repo name, value - sync schedule
        '''
        return dict((r['id'], r['sync_schedule']) for r in self.repositories())


# The crontab entry will call this module, so the following is used to trigger the
# repo sync
if __name__ == '__main__':

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
