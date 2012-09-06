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

import os
import hashlib
from pulp.server.compat import json
from pulp.plugins.distributor import Distributor
from pulp.server.managers import factory
from logging import getLogger


_LOG = getLogger(__name__)

PUBLISH_DIR='/var/lib/pulp/published/http/citrus/repos'


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

        pubdir = config.get('publishdir', PUBLISH_DIR)
        units = conduit.get_units()
        pub = Publisher(repo.id, pubdir)
        pub.publish([u.__dict__ for u in units])
    
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
        self._add_distributors(repo.id, payload)
        return payload
    
    def _add_repository(self, repoid, payload):
        """
        Add repository information to the payload.
        @param repoid: The repository ID.
        @type repoid: str
        @param payload: The repository payload
        @type payload: dict
        """
        manager = factory.repo_query_manager()
        payload['repository'] = manager.get_repository(repoid)
        
    def _add_distributors(self, repoid, payload):
        """
        Add repository distributors information to the payload.
        @param repoid: The repository ID.
        @type repoid: str
        @param payload: The repository payload
        @type payload: dict
        """
        manager = factory.repo_distributor_manager()
        payload['distributors'] = manager.get_distributors(repoid)


class Publisher:
    """
    The HTTP publisher.
    @ivar root: The repository qualfied directory path.
    @type root: str
    """

    def __init__(self, repo_id, root):
        """
        @param repo_id: The repository ID.
        @type repo_id: str
        @param root: The root directory for all repositories.
        @type root: str
        """
        self.root = os.path.join(root, repo_id)
        
    def publish(self, units):
        """
        Publish the specified units.
        Writes the units.json file and symlinks each of the
        files associated to the unit's 'storage_path'.
        @param units: A list of units.
        @type units: list
        """
        self.write(units)
        for u in units:
            self.link(u)
        
    def write(self, units):
        """
        Write the units.json for the specified list of units.
        Steps:
          1. ensure the directory exists.
          2. write the units.json.
          3. link files assocated with each unit.
        @param units: A list of units.
        @type units: list 
        """
        self.__mkdir()
        path = os.path.join(self.root, 'units.json')
        fp = open(path, 'w+')
        try:
            json.dump(units, fp, indent=2)
        finally:
            fp.close()
            
    def link(self, unit):
        """
        Link file associated with the unit into the publish directory.
        The file name is the SHA256 of the 'storage_path'.
        @param unit: A content unit.
        @type unit: Unit
        """
        target_dir = self.__mkdir('content')
        source = unit.get('storage_path')
        m = hashlib.sha256()
        m.update(source)
        target = os.path.join(target_dir, m.hexdigest())
        if not os.path.islink(target):
            os.symlink(source, target)

    def __mkdir(self, subdir=None):
        """
        Ensure the I{root} directory exits.
        @param subdir: An optional sub directory to be created.
        @type str: 
        """
        if subdir:
            path = os.path.join(self.root, subdir)
        else:
            path = self.root
        if not os.path.exists(path):
            os.makedirs(path)
        return path