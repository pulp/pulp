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
from pulp.client.api.server import ServerRequestError
from pulp.common import dateutils


repository_deferred_fields = ('packages',
                              'packagegroups',
                              'packagegroupcategories')


class RepositoryAPI(PulpAPI):
    """
    Connection class to access repo specific calls
    """
    def __init__(self):
        self.base_path = "/v2/repositories/"
        
    def repositories(self):
        path = self.base_path
        return self.server.GET(path)[1]
    
    def create(self, id, display_name, description, notes):
        path = self.base_path
        repodata = {"id": id,
                    "display_name": display_name,
                    "description": description,
                    "notes": notes,}
        return self.server.POST(path, repodata)[1]

    def repository(self, id):
        path = self.base_path + ("%s/" % id)
        return self.server.GET(path)[1]

    def delete(self, id):
        path = self.base_path + "%s/" % id
        return self.server.DELETE(path)[1]

    def update(self, id, delta):
        path = self.base_path + "%s/" % id
        return self.server.PUT(path, delta)[1]


class RepositoryImporterAPI(PulpAPI):
    """
    Connection class to access repo importer specific calls
    """
    def __init__(self):
        self.base_path = "/v2/repositories/%s/importers/"
    
    def importers(self, repo_id):
        path = self.base_path % repo_id
        return self.server.GET(path)[1]
    
    def create(self, repo_id, importer_type_id, importer_config):
        path = self.base_path % repo_id
        data = {"importer_type_id": importer_type_id,
                "importer_config": importer_config,}
        return self.server.POST(path, data)[1]

    def importer(self, repo_id, importer_id):
        path = self.base_path + ("%s/" % importer_id)
        return self.server.GET(path)[1]

    def delete(self, repo_id, importer_id):
        path = self.base_path + "%s/" % importer_id
        return self.server.DELETE(path)[1]

    def update(self, repo_id, importer_id, importer_config):
        path = self.base_path + "%s/" % importer_id
        return self.server.PUT(path, importer_config)[1]
    

class RepositoryDistributorAPI(PulpAPI):
    """
    Connection class to access repo distributor specific calls
    """
    def __init__(self):
        self.base_path = "/v2/repositories/%s/distributors/"
    
    def distributors(self, repo_id):
        path = self.base_path % repo_id
        return self.server.GET(path)[1]
    
    def create(self, repo_id, distributor_type_id, distributor_config, auto_publish, distributor_id):
        path = self.base_path % repo_id
        data = {"distributor_type_id": distributor_type_id,
                "distributor_config": distributor_config,
                "auto_publish": auto_publish,
                "distributor_id": distributor_id,}
        return self.server.POST(path, data)[1]

    def distributor(self, repo_id, distributor_id):
        path = self.base_path + ("%s/" % distributor_id)
        return self.server.GET(path)[1]

    def delete(self, repo_id, distributor_id):
        path = self.base_path + "%s/" % distributor_id
        return self.server.DELETE(path)[1]

    def update(self, repo_id, distributor_id, distributor_config):
        path = self.base_path + "%s/" % distributor_id
        return self.server.PUT(path, distributor_config)[1]

    
class RepositoryHistoryAPI(PulpAPI):
    """
    Connection class to access repo distributor specific calls
    """
    def __init__(self):
        self.base_path = "/v2/repositories/%s/"

