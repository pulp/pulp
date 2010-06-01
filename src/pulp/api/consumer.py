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
from pulp.util import chunks

class ConsumerApi(BaseApi):

    def __init__(self, config):
        BaseApi.__init__(self, config)
        # INDEXES
        self.objectdb.ensure_index([("packageids", pymongo.DESCENDING)])


    def _getcollection(self):
        return self.db.consumers

    
    def create(self, id, description):
        """
        Create a new Consumer object and return it
        """
        c = model.Consumer(id, description)
        self.objectdb.insert(c)
        return c
        
    def bulkcreate(self, consumers):
        """
        Create a set of Consumer objects in a bulk manner
        """
        ## Have to chunk this because of issue with PyMongo and network
        ## See: http://tinyurl.com/2eyumnc
        #chunksize = 500
        chunksize = 100
        chunked = chunks(consumers, chunksize)
        inserted = 0
        for chunk in chunked:
            self.objectdb.insert(chunk)
            inserted = inserted + chunksize
            print "Inserted: %s" % inserted

    def consumers(self):
        """
        List all consumers.  Can be quite large
        """
        return list(self.objectdb.find())

    def consumer(self, id):
        """
        Return a single Consumer object
        """
        return self.objectdb.find_one({'id': id})
    
    def consumerswithpackage(self, packageid):
        """
        List consumers using passed in packageid
        """
        return list(self.objectdb.find({"packageids":  packageid}))
