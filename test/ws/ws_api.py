#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

import httplib
import locale
import simplejson as json
import sys

sys.path.append('../../src/pulp')
import api
import model

sys.path.append('../../client/src')
from connection import RepoConnection

class WsRestApi(RepoConnection):
    
    def __init__(self):
        RepoConnection.__init__(self)
        self.localStoragePath = "/tmp/pulp/"

    def clean(self):
        api.RepoApi().clean()

    def create(self, id, name, arch, feed):
        params = {'id' : id,
                  'name' : name,
                  'arch' : arch,
                  'feed' : feed}
        data = RepoConnection.create(self, params)
        return self._repo(data)

    def update(self, repo):
        data = self._repo_to_dict(repo)
        return RepoConnection.update(self, None, data)

    def _repo(self, data):
        r = model.Repo(data['id'], data['name'], data['arch'], data['source'])
        r.packages = data['packages']
        r.packagegroups = data['packagegroups']
        r.packagegroupcategories = data['packagegroupcategories']
        r.comps_xml_path = data['comps_xml_path']

        return r

    def _repo_to_dict(self, repo):
        return {'id' : repo.id,
                'name' : repo.name,
                'arch' : repo.arch,
                'packages' : repo.packages,
                'packagegroups' : repo.packagegroups,
                'packagegroupcategories' : repo.packagegroupcategories,
                'comps_xml_path' : repo.comps_xml_path}
