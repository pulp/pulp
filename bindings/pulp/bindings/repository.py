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

from pulp.bindings.base import PulpAPI
from pulp.bindings.search import SearchAPI
from pulp.common import constants

# Default for update APIs to differentiate between None and not updating the value
UNSPECIFIED = object()

class RepositoryAPI(PulpAPI):
    """
    Connection class to access repo specific calls
    """
    def __init__(self, pulp_connection):
        """
        @type:   pulp_connection: pulp.bindings.server.PulpConnection
        """
        super(RepositoryAPI, self).__init__(pulp_connection)
        self.base_path = "/v2/repositories/"

    def repositories(self, query_parameters=()):
        path = self.base_path
        return self.server.GET(path, query_parameters)

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

        Both importer and distributors are optional in this call. If distributors
        is specified, it must be a list that contains one or more distributor
        descriptions. Each distributor is specified as a dict containing the
        following keys:

          distributor_type_id - ID of the type of distributor being added
          distributor_config - values sent to the distributor when used by
                               this repository
          auto_publish - boolean indicating if the distributor should automatically
                         publish with every sync; defaults to False
          distributor_id - used to refer to the distributor later; if omitted,
                           one will be generated


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

    def update(self, id, delta, importer_config=None, distributor_configs=None):
        """
        Update the configuration for a repository and the associated importers & exporters

        :param id: The ID of the repository to update
        :type id: str
        :param delta: The updated configuration items for the repository object itself
        :type delta: dict
        :param importer_config: The updated configuration items for the importer associated with
                                the repository
        :type importer_config: dict
        :param distributor_configs: The updated configuration items for each distributor associated
                                    with the repository
        :type distributor_configs: dict
        :return:    Response object
        :rtype:     pulp.bindings.responses.Response

        :raises:    ConnectionException or one of the RequestExceptions
                    (depending on response codes) in case of unsuccessful
                    request
        """
        path = self.base_path + "%s/" % id
        body = {'delta': delta}
        if importer_config:
            body['importer_config'] = importer_config
        if distributor_configs:
            body['distributor_configs'] = distributor_configs

        return self.server.PUT(path, body)

    def update_repo_and_plugins(self, id, display_name, description, notes,
                                importer_config, distributor_configs):
        """
        :deprecated: 2.4
        Use :func:`update` instead.

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


class RepositorySearchAPI(SearchAPI):
    PATH = '/v2/repositories/search/'


class RepositoryImporterAPI(PulpAPI):
    """
    Connection class to access repo importer specific calls
    """
    def __init__(self, pulp_connection):
        """
        @type:   pulp_connection: pulp.bindings.server.PulpConnection
        """
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
        path = self.base_path % repo_id + ("%s/" % importer_id)
        return self.server.GET(path)

    def delete(self, repo_id, importer_id):
        path = self.base_path % repo_id + "%s/" % importer_id
        return self.server.DELETE(path)

    def update(self, repo_id, importer_id, importer_config):
        path = self.base_path % repo_id + "%s/" % importer_id
        data = {"importer_config": importer_config}
        return self.server.PUT(path, data)


class RepositoryDistributorAPI(PulpAPI):
    """
    Connection class to access repo distributor specific calls
    """
    def __init__(self, pulp_connection):
        """
        @type:   pulp_connection: pulp.bindings.server.PulpConnection
        """
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
        path = self.base_path % repo_id + ("%s/" % distributor_id)
        return self.server.GET(path)

    def delete(self, repo_id, distributor_id):
        path = self.base_path % repo_id + "%s/" % distributor_id
        return self.server.DELETE(path)

    def update(self, repo_id, distributor_id, distributor_config, delta=None):
        """
        Update a repository distributor configuration.

        :param repo_id:             The repository ID
        :type repo_id:              str
        :param distributor_id:      The unique distributor id
        :type distributor_id:       str
        :param distributor_config:  The distributor config dictionary. Supported values depend on the
                                    type of distributor
        :type distributor_config:   dict
        :param delta:               A dictionary with values to change in the distributor configuration.
                                    Currently, only 'auto_publish' is supported, and should be a
                                    boolean value
        :type  delta:               dict
        """
        path = self.base_path % repo_id + "%s/" % distributor_id
        body = dict(distributor_config=distributor_config, delta=delta)
        return self.server.PUT(path, body)


class RepositoryHistoryAPI(PulpAPI):
    """
    Connection class to access repo history specific calls
    """
    def __init__(self, pulp_connection):
        """
        @type:   pulp_connection: pulp.bindings.server.PulpConnection
        """
        super(RepositoryHistoryAPI, self).__init__(pulp_connection)
        self.base_path = "/v2/repositories/%s/history/"

    def sync_history(self, repo_id, limit=None, sort=None, start_date=None, end_date=None):
        """
        retrieve the sync history for a given repository

        :param repo_id: the repository id
        :type repo_id: str
        :param limit: the number of history entries to return
        :type limit: int
        :param sort: indicates the sort direction (options are "ascending" or "descending")
        :type sort: str
        :param start_date: only entries that occurred at or after the given iso8601 datetime are returned
        :type start_date: str
        :param end_date: only entries that occurred at or before the given iso8601 datetime are returned
        :type end_date: str
        :return: server response code and response body
        :rtype: pulp.bindings.responses.Response
        """
        path = self.base_path % repo_id + "/sync/"
        queries = {}
        if limit:
            queries[constants.REPO_HISTORY_FILTER_LIMIT] = limit
        if sort:
            queries[constants.REPO_HISTORY_FILTER_SORT] = sort
        if start_date:
            queries[constants.REPO_HISTORY_FILTER_START_DATE] = start_date
        if end_date:
            queries[constants.REPO_HISTORY_FILTER_END_DATE] = end_date
        return self.server.GET(path, queries)

    def publish_history(self, repo_id, distributor_id, limit=None, sort=None, start_date=None,
                        end_date=None):
        """
        retrieve the publish history for a given repository and distributor

        :param repo_id: the repository id
        :type repo_id: str
        :param distributor_id: the distributor id to retrieve the history for
        :type distributor_id: str
        :param limit: the number of history entries to return
        :type limit: int
        :param sort: indicates the sort direction (options are "ascending" or "descending")
        :type sort: str
        :param start_date: only entries that occurred at or after the given iso8601 datetime are returned
        :type start_date: str
        :param end_date: only entries that occurred at or before the given iso8601 datetime are returned
        :type end_date: str
        :return: server response code and response body
        :rtype: pulp.bindings.responses.Response
        """
        path = self.base_path % repo_id + "/publish/" + "%s/" % distributor_id
        queries = {}
        if limit:
            queries[constants.REPO_HISTORY_FILTER_LIMIT] = limit
        if sort:
            queries[constants.REPO_HISTORY_FILTER_SORT] = sort
        if start_date:
            queries[constants.REPO_HISTORY_FILTER_START_DATE] = start_date
        if end_date:
            queries[constants.REPO_HISTORY_FILTER_END_DATE] = end_date
        return self.server.GET(path, queries)


class RepositoryActionsAPI(PulpAPI):
    """
    Connection class to access repo actions specific calls
    """
    def __init__(self, pulp_connection):
        """
        @type:   pulp_connection: pulp.bindings.server.PulpConnection
        """
        super(RepositoryActionsAPI, self).__init__(pulp_connection)
        self.base_path = "/v2/repositories/%s/actions/"

    def sync(self, repo_id, override_config):
        path = self.base_path % repo_id + "sync/"
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

class RepositoryUnitAPI(PulpAPI):
    """
    Connection class to access repo unit specific calls
    """

    COPY_PATH = 'v2/repositories/%s/actions/associate/'
    REMOVE_PATH = 'v2/repositories/%s/actions/unassociate/'
    SEARCH_PATH = 'v2/repositories/%s/search/units/'

    def __init__(self, pulp_connection):
        """
        @type:   pulp_connection: pulp.bindings.server.PulpConnection
        """
        super(RepositoryUnitAPI, self).__init__(pulp_connection)

    @staticmethod
    def _generate_search_criteria(**kwargs):
        """
        This composes arguments to a UnitAssociationCriteria, which is different
        and more complex than a normal Criteria.

        :param kwargs:  options input by the user on the CLI and passed through
                        by okaara
        :type  kwargs:  dict
        :return:    dict of options that can be sent to the REST API
                    representing a UnitAssociationCriteria
        :rtype:     dict
        """
        criteria = {
            'filters': {'unit': SearchAPI.compose_filters(**kwargs)},
            'type_ids' : kwargs.get('type_ids', None),
        }
        # allow a caller with type-specific knowledge to limit the fields that
        # are retrieved. for copy purposes, we probably don't need all of the
        # unit's attributes, and limiting which fields are retrieved can save
        # a lot of RAM
        if kwargs.get('fields'):
            criteria['fields'] = {'unit': kwargs.pop('fields')}

        # build the association filters
        association_fake_kwargs = {}
        for arg, operator in (('after', 'str-gte'), ('before', 'str-lte')):
            value = kwargs.pop(arg, None)
            if value:
                association_fake_kwargs[operator] = [('created', value)]

        # use compose_filters() to create the actual mongo spec, which requires
        # simulating the **kwargs that okaara would pass in.
        if association_fake_kwargs:
            criteria['filters']['association'] = SearchAPI.compose_filters(**association_fake_kwargs)

        return criteria

    def search(self, repo_id, **kwargs):
        """
        Perform a search of RepoContentUnits

        :param repo_id: id of repo to search within
        :type  repo_id: basestring
        :param kwargs:  search options input by the user and passed in by okaara
        :type  kwargs:  dict

        :return:    server response
        """
        criteria = self._generate_search_criteria(**kwargs)

        sort = kwargs.pop('sort', None)
        if sort:
            criteria.setdefault('sort', {})['unit'] = sort

        fields = kwargs.pop('fields', None)
        if fields:
            criteria.setdefault('fields', {})['unit'] = fields

        limit = kwargs.pop('limit', None)
        if limit:
            criteria['limit'] = limit

        skip = kwargs.pop('skip', None)
        if skip:
            criteria['skip'] = skip

        path = self.SEARCH_PATH % repo_id
        data = {'criteria': criteria}
        return self.server.POST(path, data)

    def copy(self, source_repo_id, destination_repo_id, override_config=None, **kwargs):
        """
        Perform a search of RepoContentUnits in the source repo, and copy the
        results to the destination repo.

        :param source_repo_id:  id of repo to search within
        :type  source_repo_id:  basestring
        :param destination_repo_id: id of repo into which units should be copied
        :type  destination_repo_id: basestring
        :param kwargs:  search options input by the user and passed in by okaara
        :type  kwargs:  dict

        :return:    server response
        """
        override_config = override_config or {}

        criteria = self._generate_search_criteria(**kwargs)
        data = {
            'source_repo_id' : source_repo_id,
            'criteria' : criteria,
            'override_config' : override_config,
        }
        path = self.COPY_PATH % destination_repo_id
        return self.server.POST(path, data)

    def remove(self, repo_id, **kwargs):
        """
        Removes units from a repository. The units to remove are conveyed
        using criteria and are passed into this call through the kwargs
        argument.

        :param repo_id: identifies the repo to search
        :type  repo_id: str
        :param kwargs: search options input by the user
        :type  kwargs: dict

        :return: server response
        """
        criteria = self._generate_search_criteria(**kwargs)
        data = {'criteria' : criteria}

        path = self.REMOVE_PATH % repo_id
        return self.server.POST(path, data)


class RepositorySyncSchedulesAPI(PulpAPI):

    def __init__(self, pulp_connection):
        """
        @type:   pulp_connection: pulp.bindings.server.PulpConnection
        """
        super(RepositorySyncSchedulesAPI, self).__init__(pulp_connection)

    def list_schedules(self, repo_id, importer_id):
        url = '/v2/repositories/%s/importers/%s/schedules/sync/' % (repo_id, importer_id)
        return self.server.GET(url)

    def get_schedule(self, repo_id, importer_id, schedule_id):
        url = '/v2/repositories/%s/importers/%s/schedules/sync/%s/' % (repo_id, importer_id, schedule_id)
        return self.server.GET(url)

    def add_schedule(self, repo_id, importer_id, schedule, override_config, failure_threshold, enabled):
        url = '/pulp/api/v2/repositories/%s/importers/%s/schedules/sync/' % (repo_id, importer_id)
        body = {
            'schedule' : schedule,
            'override_config' : override_config,
            'failure_threshold' : failure_threshold,
            'enabled' : enabled,
        }
        return self.server.POST(url, body)

    def delete_schedule(self, repo_id, importer_id, schedule_id):
        url = '/pulp/api/v2/repositories/%s/importers/%s/schedules/sync/%s/' % (repo_id, importer_id, schedule_id)
        return self.server.DELETE(url)

    def update_schedule(self, repo_id, importer_id, schedule_id, schedule=UNSPECIFIED,
                        override_config=UNSPECIFIED, failure_threshold=UNSPECIFIED, enabled=UNSPECIFIED):
        url = '/pulp/api/v2/repositories/%s/importers/%s/schedules/sync/%s/' % (repo_id, importer_id, schedule_id)
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
        """
        @type:   pulp_connection: pulp.bindings.server.PulpConnection
        """
        super(RepositoryPublishSchedulesAPI, self).__init__(pulp_connection)

    def list_schedules(self, repo_id, distributor_id):
        url = '/v2/repositories/%s/distributors/%s/schedules/publish/' % (repo_id, distributor_id)
        return self.server.GET(url)

    def get_schedule(self, repo_id, distributor_id, schedule_id):
        url = '/v2/repositories/%s/distributors/%s/schedules/publish/%s/' % (repo_id, distributor_id, schedule_id)
        return self.server.GET(url)

    def add_schedule(self, repo_id, distributor_id, schedule, override_config, failure_threshold, enabled):
        url = '/pulp/api/v2/repositories/%s/distributors/%s/schedules/publish/' % (repo_id, distributor_id)
        body = {
            'schedule' : schedule,
            'override_config' : override_config,
            'failure_threshold' : failure_threshold,
            'enabled' : enabled,
            }
        return self.server.POST(url, body)

    def delete_schedule(self, repo_id, distributor_id, schedule_id):
        url = '/pulp/api/v2/repositories/%s/distributors/%s/schedules/publish/%s/' % (repo_id, distributor_id, schedule_id)
        return self.server.DELETE(url)

    def update_schedule(self, repo_id, distributor_id, schedule_id, schedule=UNSPECIFIED,
                        override_config=UNSPECIFIED, failure_threshold=UNSPECIFIED, enabled=UNSPECIFIED):
        url = '/pulp/api/v2/repositories/%s/distributors/%s/schedules/publish/%s/' % (repo_id, distributor_id, schedule_id)
        body = {
            'schedule' : schedule,
            'override_config' : override_config,
            'failure_threshold' : failure_threshold,
            'enabled' : enabled,
            }

        # Strip out anything that wasn't specified by the caller
        body = dict([(k, v) for k, v in body.items() if v is not UNSPECIFIED])
        self.server.PUT(url, body)
