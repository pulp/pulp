# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
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

from pulp.client.api.base import PulpAPI


class ServiceAPI(PulpAPI):
    '''
    Connection class to the services handler
    '''
    def search_packages(self, name=None, epoch=None, version=None, release=None,
                        arch=None, filename=None, checksum_type=None, checksum=None, regex=True):
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
        data["regex"] = regex
        path = "/services/search/packages/"
        return self.server.PUT(path, data)[1]

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
