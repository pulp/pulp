# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from pulp.client.api.base import PulpAPI


class ServiceAPI(PulpAPI):
    '''
    Connection class to the services handler
    '''
    def search_packages(self, name=None, epoch=None, version=None, release=None,
                        arch=None, filename=None, checksum_type=None, checksum=None, regex=True, repoids=None):
        data = {}
        if name:
            data["name"] = name
        if epoch:
            data["epoch"] = epoch
        if version:
            data["version"] = version
        if release:
            data["release"] = release
        if arch:
            data["arch"] = arch
        if filename:
            data["filename"] = filename
        if checksum_type:
            data["checksum_type"] = checksum_type
        if checksum:
            data["checksum"] = checksum
        if repoids:
            data["repoids"] = repoids
        data["regex"] = regex
        path = "/services/search/packages/"
        return self.server.POST(path, data)[1]

    def dependencies(self, pkgnames, repoids, recursive=0):
        params = {'repoids': repoids,
                   'pkgnames': pkgnames,
                   'recursive': recursive}
        path = "/services/dependencies/"
        return self.server.POST(path, params)[1]
    
    def search_file(self, filename=None, checksum_type=None, checksum=None):
        data = {}
        if filename:
            data["filename"] = filename
        if checksum_type:
            data["checksum_type"] = checksum_type
        if checksum:
            data["checksum"] = checksum
        path = "/services/search/files/"
        return self.server.POST(path, data)[1]
    
    def get_package_checksums(self, filenames=[]):
        path = "/services/search/packages/checksum/"
        return self.server.POST(path, filenames)[1]
    
    def get_file_checksums(self, filenames=[]):
        path = "/services/search/files/checksum/"
        return self.server.POST(path, filenames)[1]

    def associate_packages(self, package_info=[]):
        """
        Will associate a list of filename,checksums to mulitple repositories
        package_info: format of [((filename,checksum), [repo_id])]
        """
        path = "/services/associate/packages/"
        return self.server.POST(path,{"package_info":package_info})[1]

    def disassociate_packages(self, package_info=[]):
        """
        Will disassociate a list of filename,checksums to mulitple repositories
        package_info: format of [((filename,checksum), [repo_id])]
        """
        path = "/services/disassociate/packages/"
        return self.server.POST(path,{"package_info":package_info})[1]
    
    def agentstatus(self, filter=[]):
        path = "/services/agent/status/"
        d = dict(filter=filter)
        return self.server.POST(path, d)[1]

    def enable_global_repo_auth(self, cert_bundle):
        path = '/services/enable_global_repo_auth/'
        params = {'cert_bundle' : cert_bundle}
        return self.server.POST(path, params)[1]

    def disable_global_repo_auth(self):
        path = '/services/disable_global_repo_auth/'
        return self.server.POST(path)

    def repo_discovery(self, url, type, cert_data={}):
        """
        Will try to perform discovery on specified url and tye string
        @param url: url to perform discovery.
        @type url: string
        @param type: content type to discovery, eg:yum
        @type type: string
        @param cert_data: certificate info format: dict(ca=ca, cert=cert)
        @type type: dictionary
        @return: task id for the scheduled discovery task
        """
        params = {'url' : url,
                  'type' : type,
                  'cert_data' : cert_data}
        path = '/services/discovery/repo/'
        return self.server.POST(path, params)[1]

    def repo_export(self, repoid, target_location, generate_isos=False, overwrite=False):
        path = "/services/export/repository/"
        params = {"repoid" : repoid,
                  "target_location" : target_location,
                  "generate_isos" : generate_isos,
                  "overwrite" : overwrite, }
        return self.server.POST(path, params)[1]

    def repo_group_export(self, groupid, target_location, generate_isos=False, overwrite=False):
        path = "/services/export/repository_group/"
        params = {"groupid" : groupid,
                  "target_location" : target_location,
                  "generate_isos" : generate_isos,
                  "overwrite" : overwrite, }
        return self.server.POST(path, params)[1]