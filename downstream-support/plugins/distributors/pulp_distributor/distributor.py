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
from pulp.server.compat import json
from pulp.plugins.distributor import Distributor
from pulp.server.managers import factory


class PulpDistributor(Distributor):

    @classmethod
    def metadata(cls):
        return {
            'id':'pulp_distributor',
            'display_name':'Pulp Distributor',
            'types':['repository',]
        }

    def validate_config(self, repo, config, related_repos):
        return (True, None)

    def publish_repo(self, repo, publish_conduit, config):
        units = publish_conduit.get_units()
        pub = PublishedContent()
        pub.write(repo.id, [u.__dict__ for u in units])
    
    def cancel_publish_repo(self, call_report, call_request):
        pass
    
    def create_consumer_payload(self, repo, config):
        payload = {}
        self._add_repository(repo.id, payload)
        self._add_distributors(repo.id, payload)
        return payload
    
    def _add_repository(self, repoid, payload):
        manager = factory.repo_query_manager()
        payload['repository'] = manager.get_repository(repoid)
        
    def _add_distributors(self, repoid, payload):
        manager = factory.repo_distributor_manager()
        payload['distributors'] = manager.get_distributors(repoid)


class PublishedContent:
    
    PUBLISH_DIR='/var/lib/pulp/published/http/downstream/repos'

    def __init__(self, root=PUBLISH_DIR):
        self.root = root
        
    def write(self, repo_id, content):
        self.__mkdir()
        path = self.__path(repo_id)
        fp = open(path, 'w+')
        try:
            json.dump(content, fp)
        finally:
            fp.close()
    
    def read(self, repo_id):
        path = self.__path(repo_id)
        fp = open(path)
        try:
            return json.load(fp)
        finally:
            fp.close()

    def __path(self, repo_id):
        fn = '.'.join((repo_id, 'json'))
        return os.path.join(self.root, fn)

    def __mkdir(self):
        if not os.path.exists(self.root):
            os.makedirs(self.root)