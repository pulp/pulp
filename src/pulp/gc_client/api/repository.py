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

# Default for update APIs to differentiate between None and not updating the value
UNSPECIFIED = object()

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

    def create_and_configure(self, id, display_name, description, notes,
                             importer_type_id=None, importer_config=None, distributors=None):
        """
        Calls the server-side aggregate method for creating a repository and
        adding importers/distributors in a single transaction. If an error
        occurs during the importers/distributors step, all effects on the server
        from this call will be deleted.

        This call has the same effect as calling:
        * RepositoryAPI.create
        * RepositoryImporterAPI.create
        * RepositoryDistributorAPI.create (for each distributor passed in)

        Both importer and distributors are optional in this call.

        :param importer_type_id: type of importer to add
        :type  importer_type_id: str

        :param importer_config: configuration to pass the importer for this repo
        :type  importer_config: dict

        :param distributors: list of tuples containing distributor_type_id,
               repo_plugin_config, auto_publish, and distributor_id (the same
               that would be passed to the RepoDistributorAPI.create call).
        :type  distributors: list
        """
        path = self.base_path
        repo_data = {
            'id' : id,
            'display_name' : display_name,
            'description' : description,
            'notes' : notes,
            'importer_type_id' : importer_type_id,
            'importer_config' : importer_config,
            'distributors' : distributors,
        }
        return self.server.POST(path, repo_data)

    def repository(self, id):
        path = self.base_path + ("%s/" % id)
        return self.server.GET(path)

    def delete(self, id):
        path = self.base_path + "%s/" % id
        return self.server.DELETE(path)

    def update(self, id, delta):
        path = self.base_path + "%s/" % id
        body = {'delta' : delta}
        return self.server.PUT(path, body)

    def update_repo_and_plugins(self, id, display_name, description, notes,
                                importer_config, distributor_configs):
        """
        Calls the server-side aggregate method for updating a repository and
        its associated plugins in a single call. They will be updated in the
        following order:

        * Repository metadata
        * Importer configuration
        * Distributor configuration(s)

        The updates stop at the first error encountered. Any updates made prior
        to the error are not rolled back.

        The notes value is a dictionary of values to change. Any key with a
        value of None will be removed from the notes dictionary. There is no
        distinction between adding a new note and updating an existing one;
        any non-None values included within will be the values set for the
        repository.

        The distributor configurations are expressed as a dictionary of distributor
        ID to new configuration to use. Any distributors omitted from this
        dictionary are left untouched.

        :param id: identifies the repository to update
        :type  id: str

        :param display_name: new value to set; None to leave the value untouched
        :type  display_name: str, None

        :param description: new value to set; None to leave the value untouched
        :type  description: str, None

        :param notes: see above; None to skip editing notes values
        :type  notes: dict, None

        :param importer_config: new configuration to set for the importer; None
               to leave the value untouched or if there is no importer on the repo
        :type  importer_config: dict, None

        :param distributor_configs: see above; None to skip updating distributor configs
        :type  distributor_configs: dict, None
        """

        # Assemble the repo metadata
        delta = {}
        if display_name is not None: delta['display_name'] = display_name
        if description is not None: delta['description'] = description
        if notes is not None: delta['notes'] = notes

        path = self.base_path + "%s/" % id
        body = {'delta' : delta,
                'importer_config' : importer_config,
                'distributor_configs' : distributor_configs,}
        return self.server.PUT(path, body)

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
        data = {"importer_config": importer_config}
        return self.server.PUT(path, data)
    

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
        self.base_path = "/v2/repositories/%s/history/"

    def sync_history(self, repo_id):
        path = self.base_path % repo_id + "/sync/"
        return self.server.GET(path)

    def publish_history(self, repo_id, distributor_id):
        path = self.base_path % repo_id + "/publish/" + "%s/" % distributor_id
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

class RepositoryUnitAssociationAPI(PulpAPI):
    """
    Connection class to manipulate repository unit associations.
    """

    def __init__(self, pulp_connection):
        super(RepositoryUnitAssociationAPI, self).__init__(pulp_connection)

    def copy_units(self, source_repo_id, destination_repo_id, criteria):
        url = '/v2/repositories/%s/actions/associate/' % destination_repo_id
        body = {
            'source_repo_id' : source_repo_id,
            'criteria' : criteria
        }
        return self.server.POST(url, body)

class RepositorySyncSchedulesAPI(PulpAPI):

    def __init__(self, pulp_connection):
        super(RepositorySyncSchedulesAPI, self).__init__(pulp_connection)

    def list_schedules(self, repo_id, importer_id):
        url = '/v2/repositories/%s/importers/%s/sync_schedules/' % (repo_id, importer_id)
        return self.server.GET(url)

    def get_schedule(self, repo_id, importer_id, schedule_id):
        url = '/v2/repositories/%s/importers/%s/sync_schedules/%s/' % (repo_id, importer_id, schedule_id)
        return self.server.GET(url)

    def add_schedule(self, repo_id, importer_id, schedule, override_config, failure_threshold, enabled):
        url = '/pulp/api/v2/repositories/%s/importers/%s/sync_schedules/' % (repo_id, importer_id)
        body = {
            'schedule' : schedule,
            'override_config' : override_config,
            'failure_threshold' : failure_threshold,
            'enabled' : enabled,
        }
        return self.server.POST(url, body)

    def delete_schedule(self, repo_id, importer_id, schedule_id):
        url = '/pulp/api/v2/repositories/%s/importers/%s/sync_schedules/%s/' % (repo_id, importer_id, schedule_id)
        return self.server.DELETE(url)

    def update_schedule(self, repo_id, importer_id, schedule_id, schedule=UNSPECIFIED,
                        override_config=UNSPECIFIED, failure_threshold=UNSPECIFIED, enabled=UNSPECIFIED):
        url = '/pulp/api/v2/repositories/%s/importers/%s/sync_schedules/%s/' % (repo_id, importer_id, schedule_id)
        body = {
            'schedule' : schedule,
            'override_config' : override_config,
            'failure_threshold' : failure_threshold,
            'enabled' : enabled,
        }

        # Strip out anything that wasn't specified by the caller
        body = dict([(k, v) for k, v in body.items() if v is not UNSPECIFIED])
        self.server.PUT(url, body)

class RepositoryPublishSchedulesAPI(PulpAPI):

    def __init__(self, pulp_connection):
        super(RepositoryPublishSchedulesAPI, self).__init__(pulp_connection)

    def list_schedules(self, repo_id, distributor_id):
        url = '/v2/repositories/%s/distributors/%s/publish_schedules/' % (repo_id, distributor_id)
        return self.server.GET(url)

    def get_schedule(self, repo_id, distributor_id, schedule_id):
        url = '/v2/repositories/%s/distributors/%s/publish_schedules/%s/' % (repo_id, distributor_id, schedule_id)
        return self.server.GET(url)

    def add_schedule(self, repo_id, distributor_id, schedule, override_config, failure_threshold, enabled):
        url = '/pulp/api/v2/repositories/%s/distributors/%s/publish_schedules/' % (repo_id, distributor_id)
        body = {
            'schedule' : schedule,
            'override_config' : override_config,
            'failure_threshold' : failure_threshold,
            'enabled' : enabled,
            }
        return self.server.POST(url, body)

    def delete_schedule(self, repo_id, distributor_id, schedule_id):
        url = '/pulp/api/v2/repositories/%s/distributors/%s/publish_schedules/%s/' % (repo_id, distributor_id, schedule_id)
        return self.server.DELETE(url)

    def update_schedule(self, repo_id, distributor_id, schedule_id, schedule=UNSPECIFIED,
                        override_config=UNSPECIFIED, failure_threshold=UNSPECIFIED, enabled=UNSPECIFIED):
        url = '/pulp/api/v2/repositories/%s/distributors/%s/publish_schedules/%s/' % (repo_id, distributor_id, schedule_id)
        body = {
            'schedule' : schedule,
            'override_config' : override_config,
            'failure_threshold' : failure_threshold,
            'enabled' : enabled,
            }

        # Strip out anything that wasn't specified by the caller
        body = dict([(k, v) for k, v in body.items() if v is not UNSPECIFIED])
        self.server.PUT(url, body)
