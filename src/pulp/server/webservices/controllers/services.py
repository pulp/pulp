#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © 2010 Red Hat, Inc.
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

import logging
import time
import web

from pulp.server.api.cds import CdsApi
from pulp.server.api.package import PackageApi
from pulp.server.api.repo import RepoApi
from pulp.server.api.file import FileApi
from pulp.server.api.upload import File
from pulp.server.api.upload import ImportUploadContent
from pulp.server.auth.authorization import READ, EXECUTE
from pulp.server.db.model import Status
from pulp.server.db.version import VERSION
from pulp.server.webservices import mongo
from pulp.server.webservices.controllers.base import JSONController, AsyncController

# globals ---------------------------------------------------------------------

cds_api = CdsApi()
rapi = RepoApi()
papi = PackageApi()
fapi = FileApi()
log = logging.getLogger(__name__)

# services controllers --------------------------------------------------------

class DependencyActions(JSONController):

    @JSONController.error_handler
    @JSONController.auth_required(EXECUTE)
    def POST(self):
        """
        list of available dependencies required \
        for a specified package per repo.
        expects passed in pkgnames and repoids from POST data
        @return: a dict of printable dependency result and suggested packages
        """
        data = self.params()
        return self.ok(papi.package_dependency(data['pkgnames'], data['repoids'], recursive=data['recursive']))


class PackageSearch(JSONController):

    @JSONController.error_handler
    @JSONController.auth_required(READ)
    def GET(self):
        """
        List available packages.
        @return: a list of packages
        """
        log.info("search:   GET received")
        valid_filters = ('id', 'name')
        filters = self.filters(valid_filters)
        spec = mongo.filters_to_re_spec(filters)
        return self.ok(papi.package_descriptions(spec))


    @JSONController.error_handler
    @JSONController.auth_required(EXECUTE)
    def POST(self):
        """
        Search for matching packages 
        expects passed in regex search strings from POST data
        @return: package meta data on successful creation of package
        """
        data = self.params()
        name = None
        if data.has_key("name"):
            name = data["name"]
        epoch = None
        if data.has_key("epoch"):
            epoch = data["epoch"]
        version = None
        if data.has_key("version"):
            version = data["version"]
        release = None
        if data.has_key("release"):
            release = data["release"]
        arch = None
        if data.has_key("arch"):
            arch = data["arch"]
        filename = None
        if data.has_key("filename"):
            filename = data["filename"]
        checksum_type = None
        if data.has_key("checksum_type"):
            checksum_type = data["checksum_type"]
        checksum = None
        if data.has_key("checksum"):
            checksum = data["checksum"]
        regex = data["regex"]
        start_time = time.time()
        pkgs = papi.packages(name=name, epoch=epoch, version=version,
            release=release, arch=arch, filename=filename, checksum=checksum,
            checksum_type=checksum_type, regex=regex)
        initial_search_end = time.time()
        for p in pkgs:
            p["repos"] = rapi.find_repos_by_package(p["id"])
        repo_lookup_time = time.time()
        log.info("Search [%s]: package lookup: %s, repo correlation: %s, total: %s" % \
                (data, (initial_search_end - start_time),
                    (repo_lookup_time - initial_search_end),
                    (repo_lookup_time - start_time)))
        return self.ok(pkgs)

    # this was not written correctly...
    def PUT(self):
        log.warning('deprecated DependencyActions.PUT called')
        return self.POST()

class StartUpload(JSONController):

    @JSONController.error_handler
    def POST(self):
        request = self.params()
        name = request['name']
        checksum = request['checksum']
        size = request['size']
        uuid = request.get('id')
        f = File.open(name, checksum, size, uuid)
        offset = f.next()
        d = dict(id=f.uuid, offset=offset)
        return self.ok(d)


class AppendUpload(JSONController):

    @JSONController.error_handler
    def PUT(self, uuid):
        f = File(uuid)
        content = self.data()
        f.append(content)
        return self.ok(True)

class ImportUpload(JSONController):

    @JSONController.error_handler
    @JSONController.auth_required(EXECUTE)
    def POST(self):
        """
        finalize the uploaded file(s)/package(s) on pulp server and
        import the metadata into pulp db to create an object;
        expects passed in metadata and upload_id from POST data
        @return: a dict of printable dependency result and suggested packages
        """
        data = self.params()
        capi = ImportUploadContent(data['metadata'], data['uploadid'])
        return self.ok(capi.process())


class FileSearch(JSONController):

    @JSONController.error_handler
    @JSONController.auth_required(EXECUTE)
    def POST(self):
        """
        Search for matching files 
        expects passed in regex search strings from POST data
        @return: matching file object
        """
        data = self.params()
        filename = None
        if data.has_key("filename"):
            filename = data["filename"]
        checksum_type = None
        if data.has_key("checksum_type"):
            checksum_type = data["checksum_type"]
        checksum = None
        if data.has_key("checksum"):
            checksum = data["checksum"]
        files = fapi.files(filename=filename, checksum_type=checksum_type, checksum=checksum, regex=True)
        for f in files:
            f["repos"] = rapi.find_repos_by_files(f["id"])
        return self.ok(files)

    def PUT(self):
        log.debug('deprecated Users.PUT method called')
        return self.POST()


class StatusService(JSONController):

    @JSONController.error_handler
    def GET(self):
        """
        Dummy call that just prints time.
        @return: db_version - current DB version number
        """
        start_time = time.time()
        collection = Status.get_collection()
        status = collection.find_one({}) or Status()

        # increment the counter and return
        status['count'] += 1
        status['timestamp'] = start_time
        collection.save(status, safe=True)

        # return the response
        return self.ok({
          "db_version": VERSION,
          "status_count": status['count'],
          "status_duration_ms": str(round((time.time() - start_time) * 1000, 2)),
        })
        
class PackagesChecksumSearch(JSONController):
    
    @JSONController.error_handler
    @JSONController.auth_required(EXECUTE)
    def POST(self):
        """
        Search for matching rpms to get all available checksums
        @return: {"rpmname1": [<checksums1>,<checksum2>,..],...} 
        """
        #NOTE: This call could be done with PackageSearch call.
        # need to efficiently rewrite the search to handle multiple queries.
        pkgnames = self.params()
        return self.ok(papi.get_package_checksums(pkgnames))

class FilesChecksumSearch(JSONController):
    
    @JSONController.error_handler
    @JSONController.auth_required(EXECUTE)
    def POST(self):
        """
        Search for matching files to get all available checksums
        @return: {"filename1": [<checksums1>,<checksum2>,..],...} 
        """
        filenames = self.params()
        return self.ok(fapi.get_file_checksums(filenames))


class CdsRedistribute(AsyncController):

    @JSONController.error_handler
    @JSONController.auth_required(EXECUTE)
    def POST(self, repo_id):
        '''
        Triggers a redistribution of consumers across all CDS instances for the
        given repo.
        '''

        # Kick off the async task
        task = self.start_task(cds_api.redistribute, [repo_id], unique=True)

        # If no task was returned, the uniqueness check was tripped which means
        # there's already a redistribute running for the given repo
        if task is None:
            return self.conflict('Sync already in process for repo [%s]' % repo_id)

        # Munge the task information to return to the caller
        task_info = self._task_to_dict(task)
        task_info['status_path'] = self._status_path(task.id)
        return self.accepted(task_info)

class AssociatePackages(JSONController):
    @JSONController.error_handler
    @JSONController.auth_required(EXECUTE)
    def POST(self):
        """
        Associate a collection of filename,checksum tuples to 
        multiple repositories.
        Returns an empty list on success or a dictionary of items
        which could not be associated
        """
        data = self.params()
        pkg_info = data["package_info"]
        return self.ok(rapi.associate_packages(pkg_info))


# web.py application ----------------------------------------------------------

URLS = (
    '/associate/packages/$', 'AssociatePackages',
    '/dependencies/$', 'DependencyActions',
    '/search/packages/$', 'PackageSearch',
    '/search/files/$', 'FileSearch',
    '/search/packages/checksum/$', 'PackagesChecksumSearch',
    '/search/files/checksum/$', 'FilesChecksumSearch',
    '/upload/$', 'StartUpload',
    '/upload/append/([^/]+)/$', 'AppendUpload',
    '/upload/import/$', 'ImportUpload',
    '/status/$', 'StatusService',
)

application = web.application(URLS, globals())
