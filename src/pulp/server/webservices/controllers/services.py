# -*- coding: utf-8 -*-
#
# Copyright © 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import logging
import time
import web
import urllib

from pulp.server import async
from pulp.server.api import exporter
from pulp.server.api.auth import AuthApi
from pulp.server.api.cds import CdsApi
from pulp.server.api.consumer import ConsumerApi
from pulp.server.api.package import PackageApi
from pulp.server.api.repo import RepoApi
from pulp.server.api.file import FileApi
from pulp.server.api.upload import File
from pulp.server.api.upload import ImportUploadContent
from pulp.server.api.discovery import get_discovery, \
    discovery_progress_callback, InvalidDiscoveryInput
from pulp.server.agent import Agent
from pulp.server.auth.authorization import READ, EXECUTE
from pulp.server.db.model import Status
from pulp.server.db.version import VERSION
from pulp.server.exceptions import PulpException
from pulp.server.exporter.base import TargetExistsException, ExportException
from pulp.server.tasking.job import Job
from pulp.server.webservices import mongo
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import (
    auth_required, error_handler)

# globals ---------------------------------------------------------------------

auth_api = AuthApi()
cds_api = CdsApi()
rapi = RepoApi()
papi = PackageApi()
fapi = FileApi()
capi = ConsumerApi()
log = logging.getLogger(__name__)

# services controllers --------------------------------------------------------

class DependencyActions(JSONController):

    @error_handler
    @auth_required(EXECUTE)
    def POST(self):
        """
        [[wiki]]
        title: list of available dependencies.
        description: list of available dependencies required for a specified package per repo.
        method: POST
        path: /services/dependencies/
        permission: READ
        success response: 200 OK
        failure response:
        return: a dictionary of dependency info in the format {'printable_dependency_result' : '', 'resolved' : [], 'unresolved' : [], 'dependency_tree' : {}}
        parameters:
         * pkgnames, list, list of package names in the format name, name.arch, name-ver-rel.arch, name-ver,
                    name-ver-rel, epoch:name-ver-rel.arch, name-epoch:ver-rel.arch.
         * repoids, list, list of repo ids
         * recursive?, boolean, performs dependency resolution recursively
         * make_tree?, boolean, constrcts a dependency results as a tree form
        """
        data = self.params()
        # validate required params
        if not data.has_key('pkgnames') or not len(data['pkgnames']):
            return self.bad_request('atleast one package required to perform dependency lookup')
        if not data.has_key('repoids') or not len(data['repoids']):
            return self.bad_request('atleast one repoid required to perform dependency lookup')
        recursive = 0
        if data.has_key("recursive"):
            recursive = data['recursive']
        make_tree = 0
        if data.has_key("make_tree"):
            make_tree = data["make_tree"]
        return self.ok(papi.package_dependency(data['pkgnames'], data['repoids'], \
                                               recursive=recursive, make_tree=make_tree))


class PackageSearch(JSONController):

    @error_handler
    @auth_required(READ)
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


    @error_handler
    @auth_required(EXECUTE)
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
        regex = False
        if data.has_key("regex"):
            regex = data["regex"]
        start_time = time.time()
        pkgs = papi.packages(name=name, epoch=epoch, version=version,
            release=release, arch=arch, filename=filename, checksum=checksum,
            checksum_type=checksum_type, regex=regex)
        repoids = None
        if data.has_key("repoids"):
            repoids = data["repoids"]
        initial_search_end = time.time()

        # select packages only from given repositories
        if repoids:
            pkgs = [p for p in pkgs if ( set(p["repoids"]) & set(repoids) )]

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

    @error_handler
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

    @error_handler
    def PUT(self, uuid):
        f = File(uuid)
        content = self.data()
        f.append(content)
        return self.ok(True)

class ImportUpload(JSONController):

    @error_handler
    @auth_required(EXECUTE)
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

    @error_handler
    @auth_required(EXECUTE)
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
            f["repoids"] = rapi.find_repos_by_files(f["id"])
        return self.ok(files)

    def PUT(self):
        log.debug('deprecated Users.PUT method called')
        return self.POST()


class StatusService(JSONController):

    @error_handler
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

    @error_handler
    @auth_required(EXECUTE)
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

    @error_handler
    @auth_required(EXECUTE)
    def POST(self):
        """
        Search for matching files to get all available checksums
        @return: {"filename1": [<checksums1>,<checksum2>,..],...}
        """
        filenames = self.params()
        return self.ok(fapi.get_file_checksums(filenames))


class CdsRedistribute(JSONController):

    @error_handler
    @auth_required(EXECUTE)
    def POST(self, repo_id):
        '''
        Triggers a redistribution of consumers across all CDS instances for the
        given repo.
        '''

        # Kick off the async task
        task = async.run_async(cds_api.redistribute, [repo_id], unique=True)

        # If no task was returned, the uniqueness check was tripped which means
        # there's already a redistribute running for the given repo
        if task is None:
            return self.conflict('Sync already in process for repo [%s]' % repo_id)

        # Munge the task information to return to the caller
        task_info = self._task_to_dict(task)
        return self.accepted(task_info)

class AssociatePackages(JSONController):
    @error_handler
    @auth_required(EXECUTE)
    def POST(self):
        """
        Associate a collection of filename,checksum tuples to
        multiple repositories.
        Returns an empty list on success or a dictionary of items
        which could not be associated
        """
        data = self.params()
        if not data.has_key('package_info'):
            return self.bad_request("Missing data for 'package_info'")
        pkg_info = data["package_info"]
        return self.ok(rapi.associate_packages(pkg_info))

class DisassociatePackages(JSONController):
    @error_handler
    @auth_required(EXECUTE)
    def POST(self):
        """
        [[wiki]]
        title: Disassociate a collection of filename,checksum tuples from multiple repositories
        description: Disassociate a collection of packages from a series of repositories
        method: POST
        path: /services/disassociate/packages/
        permission: READ
        success response: 200 OK
        failure response:
        return: a list of errors in the format of [{'filename':{'checksum_value':[repoid]}}]
        parameters:
         * package_info: list of tuples in the format [((filename, checksum),[repoids]]
        """
        data = self.params()
        if not data.has_key('package_info'):
            return self.bad_request("Missing data for 'package_info'")
        pkg_info = data["package_info"]
        return self.ok(rapi.disassociate_packages(pkg_info))

class AgentStatus(JSONController):

    @error_handler
    @auth_required(READ)
    def POST(self):
        """
        Get the availabiliy of an agent.
        @return: {uuid:{online:bool,heatbeat:str,capabilities:bool}}
        """
        data = self.params()
        filter = data.get('filter', [])
        log.info("agent status:   GET received")
        report = Agent.status(filter)
        for k,v in report.items():
            report[k] = dict(online=v[0], heartbeat=v[1], capabilities={})
        query = {'id':{'$in':report.keys()}}
        fields = {'id':1,'capabilities':1}
        for consumer in capi.consumers(query, fields):
            cid = consumer['id']
            for k in ('capabilities',):
                report[cid][k] = consumer[k]
        return self.ok(report)

class EnableGlobalRepoAuth(JSONController):

    @error_handler
    @auth_required(EXECUTE)
    def POST(self):
        '''
        [[wiki]]
        title: Enable Global Repository Authentication
        description: Configures the Pulp server to apply the given credentials to requests against all of its repositories.
        method: POST
        path: /enable_global_repo_credentials
        permission: EXECUTE
        success response: 200 OK
        failure response: 206 PARTIAL CONTENT
        return: list of CDS hostnames that were successfully updated and a list of the ones that failed to update
        '''
        data = self.params()
        bundle = data['cert_bundle']
        log.info('Enabling global repo authentication')

        auth_api.enable_global_repo_auth(bundle)

        self.ok({})

class DisableGlobalRepoAuth(JSONController):

    @error_handler
    @auth_required(EXECUTE)
    def POST(self):
        '''
        [[wiki]]
        title: Disable Global Repository Authentication
        description: Configures the Pulp server to not authenticate access to repositories on a global level (individual repo access can still be controlled using the repo APIs).
        method: POST
        path: /disable_global_repo_credentials
        permission: EXECUTE
        success response: 200 OK
        failure response: 206 PARTIAL CONTENT
        return: list of CDS hostnames that were successfully updated and a list of the ones that failed to update
        '''
        log.info('Disabling global repo authentication')

        auth_api.disable_global_repo_auth()

        self.ok({})

class RepoDiscovery(JSONController):
    @error_handler
    @auth_required(EXECUTE)
    def POST(self):
        '''
        [[wiki]]
        title: Repository Discovery
        description: Discover repository urls with metadata and create candidate repos. Supports http, https and file based urls. The file based url paths should be accessible by apache to perform discovery.
        method: POST
        path: /services/discovery/repo/
        permission: EXECUTE
        success response: 200 OK
        failure response: 206 PARTIAL CONTENT
        return: list of matching repourls.
        parameters:
         * url, str, remote url to perform discovery
         * type, str, type of content to discover(supported types: 'yum')
         * cert_data?, dict, a hash of ca and cert info to access if url is secure; {'ca' : <ca>,'cert':<cert>}
        '''
        data = self.params()
        try:
            type = data.get('type', None)
            discovery_obj = get_discovery(type)
        except InvalidDiscoveryInput:
            return self.bad_request('Invalid content type [%s]' % type)
        try:
            url = data.get('url', None)
            discovery_obj.validate_url(url)
            cert_data = data.get('cert_data', None)
            cert = ca = None
            if cert_data:
                cert = cert_data.get('cert', None)
                ca   = cert_data.get('ca', None)
        except InvalidDiscoveryInput:
            return self.bad_request('Invalid url [%s]' % url)

        log.info('Discovering compatible repo urls @ [%s]' % data['url'])
        # Kick off the async task
        task = async.run_async(discovery_obj.discover, [url, ca, cert])
        if not task:
            return self.conflict('Repo discovery is already in progress')    
        task.set_progress('progress_callback', discovery_progress_callback)
        # Munge the task information to return to the caller
        task_info = self._task_to_dict(task)
        return self.accepted(task_info)

class RepositoryExport(JSONController):
    @error_handler
    @auth_required(EXECUTE)
    def POST(self):
        """
        [[wiki]]
        title: Repository Content Export
        description: Export the repository's content into target directory from its source.
        method: POST
        path: /services/export/repository/
        permission: EXECUTE
        success response: 202 Accepted
        failure response: 404 Not Found if the id does not match a repository
                          406 Not Acceptable if the repository does not have a source
                          409 Conflict if a export is already in progress for the repository
        return: a Task object
        parameters:
         * repoid, str, id of the repository to export
         * target_location, str, target location on the server filesystem where the content needs to be exported
         * generate_isos?, boolean, wrap the exported content into iso image files.
         * overwrite?, boolean, overwrite the content in target location if not empty
        """
        export_params = self.params()
        repoid = export_params.get('repoid', None)
        if repoid is None:
           return self.not_found('A repository with the id, %s, does not exist' % repoid)

        target_location = export_params.get('target_location', None)
        generate_isos = export_params.get('generate_isos', False)
        overwrite = export_params.get('overwrite', False)
        # Check for valid target_location values
        try:
            exporter.validate_target_path(target_dir=target_location, overwrite=overwrite)
        except TargetExistsException:
            return self.bad_request("Target location [%s] already has content; must use overwrite to perform export." % target_location)
        except ExportException, ee:
            raise PulpException(str(ee))
        task = exporter.export(repoid, target_directory=target_location, generate_isos=generate_isos, overwrite=overwrite)
        if not task:
            return self.conflict('Export already in process for repo [%s]' % repoid)
        task_info = self._task_to_dict(task)
        return self.accepted(task_info)

class RepoGroupExport(JSONController):
    @error_handler
    @auth_required(EXECUTE)
    def POST(self):
        '''
        [[wiki]]
        title: Repository group export
        description: schedule an export on a group of repositories
        method: POST
        path: /services/export/repository_group/
        permission: EXECUTE
        success response: 200 OK
        failure response: 206 PARTIAL CONTENT
        return: Job object
         parameters:
         * groupid, str, repository group to export
         * target_location, str, target location on the server filesystem where the content needs to be exported
         * generate_isos?, boolean, wrap the exported content into iso image files.
         * overwrite?, boolean, overwrite the content in target location if not empty
        '''
        export_params = self.params()
        groupid = export_params.get('groupid', None)
        if not groupid:
            return self.bad_request('Invalid content groupid [%s]' % groupid)
        target_location = export_params.get('target_location', None)
        generate_isos = export_params.get('generate_isos', False)
        overwrite = export_params.get('overwrite', False)
        # Check for valid target_location values
        try:
            exporter.validate_target_path(target_dir=target_location, overwrite=overwrite)
        except TargetExistsException:
            return self.bad_request("Target location [%s] already has content; must use overwrite to perform export." % target_location)
        except ExportException, ee:
            raise PulpException(str(ee))

        repos = rapi.repositories({'groupid': groupid}, fields=['id'])
        log.error("Repo ids in group %s" % repos)
        if not len(repos):
            return self.bad_request("No repositories associated to the group id [%s]; nothing to export." % groupid)
        job = Job()
        for repo in repos:
            repoid = repo['id']
            repo_target_location = "%s/%s" % (target_location, repoid)
            task = exporter.export(repoid, target_directory=repo_target_location, generate_isos=generate_isos, overwrite=overwrite)
            if not task:
                log.error('Export already in process for repo [%s]' % id)
            job.add(task)
        jobdict = self._job_to_dict(job)
        return self.accepted(jobdict)

# web.py application ----------------------------------------------------------

URLS = (
    '/associate/packages/$', 'AssociatePackages',
    '/disassociate/packages/$', 'DisassociatePackages',
    '/dependencies/$', 'DependencyActions',
    '/search/packages/$', 'PackageSearch',
    '/search/files/$', 'FileSearch',
    '/search/packages/checksum/$', 'PackagesChecksumSearch',
    '/search/files/checksum/$', 'FilesChecksumSearch',
    '/upload/$', 'StartUpload',
    '/upload/append/([^/]+)/$', 'AppendUpload',
    '/upload/import/$', 'ImportUpload',
    '/status/$', 'StatusService',
    '/agent/status/$', 'AgentStatus',
    '/cds_redistribute/$', 'CdsRedistribute',
    '/enable_global_repo_auth/$', 'EnableGlobalRepoAuth',
    '/disable_global_repo_auth/$', 'DisableGlobalRepoAuth',
    '/discovery/repo/$', 'RepoDiscovery',
    '/export/repository/$', 'RepositoryExport',
    '/export/repository_group/$', 'RepoGroupExport',
)

application = web.application(URLS, globals())
