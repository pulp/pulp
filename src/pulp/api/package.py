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

import pymongo

# Pulp
from pulp import model
from pulp.api.base import BaseApi

class PackageApi(BaseApi):

    def __init__(self, config):
        BaseApi.__init__(self, config)

    def _get_unique_indexes(self):
        return []

    def _get_indexes(self):
        return ["packageid"]
        
    def _getcollection(self):
        return self.db.packages
        
    def create(self, id, name):
        """
        Create a new Package object and return it
        """
        p = model.Package(id, name)
        self.objectdb.insert(p)
        return p
        
    def package(self, id, filter=None):
        """
        Return a single Package object
        """
        return self.objectdb.find_one({'id': id})

    def packages(self):
        """
        List all packages.  Can be quite large
        """
        return list(self.objectdb.find())
        
