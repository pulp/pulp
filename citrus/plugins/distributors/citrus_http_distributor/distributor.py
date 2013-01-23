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

from gettext import gettext as _
from pulp.plugins.distributor import Distributor
from pulp.citrus.http.publisher import HttpPublisher
from pulp.server.managers import factory
from pulp.server.config import config as pulp_conf
from logging import getLogger


_LOG = getLogger(__name__)


class CitrusHttpDistributor(Distributor):
    """
    The (citrus) distributor
    """

    @classmethod
    def metadata(cls):
        return {
            'id':'citrus_http_distributor',
            'display_name':'Pulp Citrus HTTP Distributor',
            'types':['repository',]
        }

    def validate_config(self, repo, config, related_repos):
        """
        Layout:
          {
            protocol : (http|https|file),
            http : {
              alias : [url, directory]
            },
            https : {
              alias : [url, directory],
              ssl (optional) : {
                ca_cert : <path>,
                client_cert : <path>
                verify : <bool>
              }
            }
          }
        """
        missing_msg = _('Missing required configuration property: %(p)s')
        invalid_msg = _('Property %(p)s must be: %(v)s')
        key = 'protocol'
        protocol = config.get(key)
        if not protocol:
            return (False, missing_msg % {'p':key})
        protocols = ('http', 'https', 'file')
        if protocol not in protocols:
            return (False, invalid_msg % {'p':key, 'v':protocols})
        for key in ('http', 'https'):
            section = config.get(key)
            if not section:
                return (False, missing_msg % {'p':key})
            key = (key, 'alias')
            alias = section.get(key[1])
            if not alias:
                return (False, missing_msg % {'p':'.'.join(key)})
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
        protocol = config.get('protocol')
        host = pulp_conf.get('server', 'server_name')
        section = config.get(protocol)
        alias = section.get('alias')
        base_url = '://'.join((protocol, host))
        return HttpPublisher(base_url, alias, repo.id)

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
        """
        Add the citrus importer.
        @param repo: A repo object.
        @type repo: L{pulp.plugins.model.Repository}
        @param config: plugin configuration
        @type  config: pulp.plugins.config.PluginCallConfiguration
        @param payload: The bind payload.
        @type payload: dict
        """
        conf = self._importer_conf(repo, config)
        importer = {
            'id':'citrus_http_importer',
            'importer_type_id':'citrus_http_importer',
            'config':conf,
        }
        payload['importers'] = [importer]

    def _importer_conf(self, repo, config):
        """
        Build the citrus importer configuration.
        @param repo: A repo object.
        @type repo: L{pulp.plugins.model.Repository}
        @param config: plugin configuration
        @type  config: pulp.plugins.config.PluginCallConfiguration
        @return: The importer configuration.
        @rtype: dict
        """
        publisher = self.publisher(repo, config)
        protocol =  config.get('protocol')
        manifest_url = '/'.join((publisher.base_url, publisher.manifest_path()))
        section = config.get(protocol)
        ssl = section.get('ssl', {})
        ca_cert = ssl.get('ca_cert')
        client_cert = ssl.get('client_cert')
        verify = ssl.get('verify', False)
        conf = {
            'manifest_url':manifest_url,
            'ssl':{
                'ca_cert':self._read(ca_cert),
                'client_cert':self._read(client_cert),
                'verify':verify,
            }
        }
        return conf

    def _read(self, path):
        """
        Read the file at the specified path unless the path is
        None or and empty string.
        @param path: A fully qualified path to a file.
        @type path: str
        @return: The file contents.
        @rtype: str
        """
        if path:
            fp = open(path)
            try:
                return fp.read()
            finally:
                fp.close()

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