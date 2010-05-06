#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © 2010 Red Hat, Inc.
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

__author__ = 'Jason L Connor <jconnor@redhat.com>'

import web

from juicer.controllers.base import JSONController
from pulp.api import RepoApi

# api JSONController ------------------------------------------------------------------

API = RepoApi()

# controllers -----------------------------------------------------------------

class Repositories(JSONController):
    
    def GET(self):
        return self.output(API.repositories())
    
    
class Repository(JSONController):
    
    def DELETE(self, id):
        API.delete(id)
        return self.output(True)

    def GET(self, id):
        return self.output(API.repository(id))
    
    
class Packages(JSONController):
    
    def GET(self, id):
        return self.output(API.packages(id))
    
    
class Update(JSONController):
    
    def POST(self):
        repo = self.input()
        API.update(repo)
        return self.output(True)
    
    
class Create(JSONController):
    
    def POST(self):
        repo_data = self.input()
        repo = API.create(repo_data['id'],
                          repo_data['name'],
                          repo_data['arch'],
                          repo_data['feed'])
        return self.output(repo)
    
    
class Sync(JSONController):
    
    def GET(self, id):
        API.sync(id)
        return self.output(True)
    
    
# web.py application ----------------------------------------------------------

URLS = (
    '/', 'Repositories',
    '/(\d+)', 'Repository',
    '/packages/(\d+)', 'Packages',
    '/update', 'Update',
    '/create', 'Create',
    '/sync/(\d+)', 'Sync',
)

application = web.application(URLS, globals())