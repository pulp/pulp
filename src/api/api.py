#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: Mike McCune
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
#
import pymongo
import model

from pymongo import Connection

class RepoApi(object):
    '''
    API for create/delete/syncing of Repo objects
    '''
    def __init__(self):
        ####### Mongo DB ########
        connection = Connection()
        self.db = connection._database
        self.collection = self.db.pulp_collection
        self.repos = self.db.repos

    
    def repositories(self):
        return list(self.repos.find())
        
    def repository(self, id):
        return
        
    def packages(self, id):
        return
    
    def create(self, id, name, arch, feed):
        r = model.Repo(id, name, arch, feed)
        self.repos.insert(r)
        return r
        

    def delete(self, id):
        return
        
    def clone(self, id, newid, newname):
        return
    
    def clone(self, id):
        return

        
        
