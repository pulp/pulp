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


class PulpDistributor(Distributor):

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
        pubdir = config.get('publishdir', PUBLISH_DIR)
        units = conduit.get_units()
        pub = Publisher(repo.id, pubdir)
        pub.publish([u.__dict__ for u in units])
    
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


class Publisher:

    def __init__(self, repo_id, root):
        self.root = os.path.join(root, repo_id)
        
    def publish(self, units):
        self.write(units)
        for u in units:
            self.link(u)
        
    def write(self, units):
        self.__mkdir()
        path = os.path.join(self.root, 'units.json')
        fp = open(path, 'w+')
        try:
            json.dump(units, fp)
        finally:
            fp.close()
            
    def link(self, unit):
        target_dir = self.__mkdir('content')
        source = unit.get('storage_path')
        m = hashlib.sha256()
        m.update(source)
        target = os.path.join(target_dir, m.hexdigest())
        if not os.path.islink(target):
            os.symlink(source, target)

    def __mkdir(self, subdir=None):
        if subdir:
            path = os.path.join(self.root, subdir)
        else:
            path = self.root
        if not os.path.exists(path):
            os.makedirs(path)
        return path