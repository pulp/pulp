# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from pulp.gc_client.api.base import PulpAPI


class RepositoryAPI(PulpAPI):
    """
    Connection class to access repo specific calls
    """
    def __init__(self, pulp_connection):
        super(RepositoryAPI, self).__init__(pulp_connection)
        self.base_path = "/v2/repositories/"
        
    def repositories(self):
        path = self.base_path
        return self.server.GET(path)
    
    def create(self, id, display_name, description, notes):
        path = self.base_path
        repodata = {"id": id,
                    "display_name": display_name,
                    "description": description,
                    "notes": notes,}
        return self.server.POST(path, repodata)

    def repository(self, id):
        path = self.base_path + ("%s/" % id)
        return self.server.GET(path)

    def delete(self, id):
        path = self.base_path + "%s/" % id
        return self.server.DELETE(path)

    def update(self, id, delta):
        path = self.base_path + "%s/" % id
        return self.server.PUT(path, delta)


class RepositoryImporterAPI(PulpAPI):
    """
    Connection class to access repo importer specific calls
    """
    def __init__(self, pulp_connection):
        super(RepositoryImporterAPI, self).__init__(pulp_connection)
        self.base_path = "/v2/repositories/%s/importers/"
    
    def importers(self, repo_id):
        path = self.base_path % repo_id
        return self.server.GET(path)
    
    def create(self, repo_id, importer_type_id, importer_config):
        path = self.base_path % repo_id
        data = {"importer_type_id": importer_type_id,
                "importer_config": importer_config,}
        return self.server.POST(path, data)

    def importer(self, repo_id, importer_id):
        path = self.base_path % repo_id + ("/%s/" % importer_id)
        return self.server.GET(path)

    def delete(self, repo_id, importer_id):
        path = self.base_path % repo_id + "/%s/" % importer_id
        return self.server.DELETE(path)

    def update(self, repo_id, importer_id, importer_config):
        path = self.base_path % repo_id + "/%s/" % importer_id
        return self.server.PUT(path, importer_config)
    

class RepositoryDistributorAPI(PulpAPI):
    """
    Connection class to access repo distributor specific calls
    """
    def __init__(self, pulp_connection):
        super(RepositoryDistributorAPI, self).__init__(pulp_connection)
        self.base_path = "/v2/repositories/%s/distributors/"
    
    def distributors(self, repo_id):
        path = self.base_path % repo_id
        return self.server.GET(path)
    
    def create(self, repo_id, distributor_type_id, distributor_config, auto_publish, distributor_id):
        path = self.base_path % repo_id
        data = {"distributor_type_id": distributor_type_id,
                "distributor_config": distributor_config,
                "auto_publish": auto_publish,
                "distributor_id": distributor_id,}
        return self.server.POST(path, data)

    def distributor(self, repo_id, distributor_id):
        path = self.base_path % repo_id + ("/%s/" % distributor_id)
        return self.server.GET(path)

    def delete(self, repo_id, distributor_id):
        path = self.base_path % repo_id + "/%s/" % distributor_id
        return self.server.DELETE(path)

    def update(self, repo_id, distributor_id, distributor_config):
        path = self.base_path % repo_id + "/%s/" % distributor_id
        return self.server.PUT(path, distributor_config)


class RepositoryHistoryAPI(PulpAPI):
    """
    Connection class to access repo history specific calls
    """
    def __init__(self, pulp_connection):
        super(RepositoryHistoryAPI, self).__init__(pulp_connection)
        self.base_path = "/v2/repositories/%s/"

    def sync_history(self, repo_id):
        path = self.base_path % repo_id + "/sync_history/"
        return self.server.GET(path)

    def publish_history(self, repo_id, distributor_id):
        path = self.base_path % repo_id + "/publish_history/" + "%s/" % distributor_id
        return self.server.GET(path)

class RepositoryActionsAPI(PulpAPI):
    """
    Connection class to access repo actions specific calls
    """
    def __init__(self, pulp_connection):
        super(RepositoryActionsAPI, self).__init__(pulp_connection)
        self.base_path = "/v2/repositories/%s/actions/"

    def sync(self, repo_id, override_config):
        path = self.base_path % repo_id + "/sync/"
        data = {'override_config' : override_config,}
        return self.server.POST(path, data)
    
    def publish(self, repo_id, distributor_id, override_config):
        path = self.base_path % repo_id + "/publish/"
        data = {'id' : distributor_id,
                'override_config' : override_config,}
        return self.server.POST(path, data)

    def associate(self, repo_id, source_repo_id):
        path = self.base_path % repo_id + "/associate/"
        data = {'source_repo_id' : source_repo_id,}
        return self.server.POST(path, data)

class RepositoryUnitSearchAPI(PulpAPI):
    """
    Connection class to access repo search specific calls
    """
    def __init__(self, pulp_connection):
        super(RepositoryUnitSearchAPI, self).__init__(pulp_connection)
        self.base_path = "/v2/repositories/%s/search/units/"

    def search(self, repo_id, query):
        path = self.base_path % repo_id
        data = {'query': query,}
        return self.server.POST(path, data)
