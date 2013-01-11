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

from pulp.plugins.distributor import Distributor
from pulp.citrus.http.publisher import HttpPublisher
from pulp.server.managers import factory
from pulp.server.config import config as pulp_conf
from logging import getLogger


_LOG = getLogger(__name__)

VIRTUAL_HOST = ('/pulp/citrus/repos', '/var/lib/pulp/citrus/published/http/repos')


class CitrusDistributor(Distributor):
    """
    The (citrus) distributor
    """

    @classmethod
    def metadata(cls):
        return {
            'id':'citrus_distributor',
            'display_name':'Pulp Citrus Distributor',
            'types':['repository',]
        }

    def validate_config(self, repo, config, related_repos):
        return (True, None)

    def publish_repo(self, repo, conduit, config):
        """
        Publishes the given repository.
        While this call may be implemented using multiple threads, its execution
        from the Pulp server's standpoint should be synchronous. This call should
        not return until the publish is complete.

        It is not expected that this call be atomic. Should an error occur, it
        is not the responsibility of the distributor to rollback any changes
        that have been made.

        @param repo: metadata describing the repository
        @type  repo: pulp.plugins.model.Repository
        @param publish_conduit: provides access to relevant Pulp functionality
        @type  publish_conduit: pulp.plugins.conduits.repo_publish.RepoPublishConduit
        @param config: plugin configuration
        @type  config: pulp.plugins.config.PluginConfiguration
        @return: report describing the publish run
        @rtype:  pulp.plugins.model.PublishReport
        """
        units = conduit.get_units()
        publisher = self.publisher(repo, config)
        units = self._prepare_units(units)
        manifest, links = publisher.publish(units)
        details = dict(manifest=manifest, links=links)
        return conduit.build_success_report('succeeded', details)

    def _prepare_units(self, units):
        """
        Prepare units to be published.
            - add _relative storage path.
        @param units: A list of units to be published.
        @type units: list
        """
        prepared = []
        storage_dir = pulp_conf.get('server', 'storage_dir')
        for unit in units:
            _unit = unit.__dict__
            storage_path = _unit['storage_path']
            if storage_path:
                relative_path = storage_path[len(storage_dir):]
                _unit['_relative_path'] = relative_path
            prepared.append(_unit)
        return prepared

    def publisher(self, repo, config):
        """
        Get a configured publisher.
        @param repo: A repository.
        @type repo: pulp.plugins.model.Repository
        @param config: plugin configuration
        @type  config: pulp.plugins.config.PluginConfiguration
        @return: The configured publisher.
        """
        base_url = config.get('base_url')
        if not base_url:
            host = pulp_conf.get('server', 'server_name')
            base_url = 'http://%s' % host
        virtual_host = config.get('virtual_host', VIRTUAL_HOST)
        return HttpPublisher(base_url, virtual_host, repo.id)

    def cancel_publish_repo(self, call_report, call_request):
        pass

    def create_consumer_payload(self, repo, config):
        """
        Called when a consumer binds to a repository using this distributor.
        This call should return a dictionary describing all data the consumer
        will need to access the repository. The contents will vary wildly
        depending on the method the repository is published, but examples
        of returned data includes authentication information, location of the
        repository (e.g. URL), and data required to verify the contents
        of the published repository.
        @param repo: metadata describing the repository
        @type  repo: pulp.plugins.model.Repository
        @param config: plugin configuration
        @type  config: pulp.plugins.config.PluginCallConfiguration
        @return: dictionary of relevant data
        @rtype:  dict
        """
        payload = {}
        self._add_repository(repo.id, payload)
        self._add_importers(repo, config, payload)
        self._add_distributors(repo.id, payload)
        return payload

    def _add_repository(self, repo_id, payload):
        """
        Add repository information to the payload.
        @param repo_id: The repository ID.
        @type repo_id: str
        @param payload: The repository payload
        @type payload: dict
        """
        manager = factory.repo_query_manager()
        payload['repository'] = manager.get_repository(repo_id)

    def _add_importers(self, repo, config, payload):
        publisher = self.publisher(repo, config)
        manifest_url = '/'.join((publisher.base_url, publisher.manifest_path()))
        importer = {
            'id':'citrus_importer',
            'importer_type_id':'citrus_importer',
            'config':{
                'manifest_url':manifest_url,
            }
        }
        payload['importers'] = [importer]

    def _add_distributors(self, repo_id, payload):
        """
        Add repository distributors information to the payload.
        @param repo_id: The repository ID.
        @type repo_id: str
        @param payload: The distributor(s) payload
        @type payload: dict
        """
        manager = factory.repo_distributor_manager()
        payload['distributors'] = manager.get_distributors(repo_id)