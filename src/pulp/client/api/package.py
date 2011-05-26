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


class PackageAPI(PulpAPI):

    def clean(self):
        path = "/packages/"
        return self.server.DELETE(path)[1]

    def create(self, name, epoch, version, release, arch, description,
            checksum_type, checksum, filename):
        path = "/packages/"
        repodata = {"name"   : name,
                    "epoch" : epoch,
                    "version" : version,
                    "release" : release,
                    "arch" : arch,
                    "description" : description,
                    "checksum_type" : checksum_type,
                    "checksum": checksum,
                    "filename": filename, }
        return self.server.PUT(path, repodata)[1]

    def packages(self):
        path = "/packages/"
        return self.server.GET(path)[1]

    def package(self, id, filter=None):
        path = "/packages/%s/" % id
        return self.server.GET(path)[1]

    def delete(self, packageid):
        path = "/packages/%s/" % packageid
        return self.server.DELETE(path)[1]

    def package_by_ivera(self, name, version, release, epoch, arch):
        path = "/packages/%s/%s/%s/%s/%s/" % (name, version, release, epoch, arch)
        return self.server.GET(path)[1]
    
    def orphaned_packages(self):
        path = "/orphaned/packages/"
        return self.server.GET(path)[1]

