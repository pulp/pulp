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
import logging
import pymongo
import re

from pulp import model
from pulp.api.base import BaseApi
from pulp.pexceptions import PulpException
from pulp.util import chunks
from pulp.agent import Agent

# Pulp

log = logging.getLogger('pulp.api.consumer')

class ConsumerApi(BaseApi):

    def __init__(self, config):
        BaseApi.__init__(self, config)

    def _getcollection(self):
        return self.db.consumers

    def _get_unique_indexes(self):
        return ["id"]

    def _get_indexes(self):
        return ["package_profile.name", "repoids"]

    def create(self, id, description):
        """
        Create a new Consumer object and return it
        """
        c = model.Consumer(id, description)
        self.insert(c)
        return c
        
    def bulkcreate(self, consumers):
        """
        Create a set of Consumer objects in a bulk manner
        """
        ## Have to chunk this because of issue with PyMongo and network
        ## See: http://tinyurl.com/2eyumnc
        #chunksize = 500
        chunksize = 50
        chunked = chunks(consumers, chunksize)
        inserted = 0
        for chunk in chunked:
            self.objectdb.insert(chunk, check_keys=False, safe=False)
            inserted = inserted + chunksize
            print "Inserted: %s" % inserted

    def consumers(self):
        """
        List all consumers.  Can be quite large
        """
        consumers = list(self.objectdb.find({},['id', 'description', 'repoids']))
        munged = [] 
        for c in consumers:
            link = '/consumers/%s/packages/' % c['id']
            c['package_profile'] = {'href': link}
            munged.append(c)
        return munged

    def consumer(self, id):
        """
        Return a single Consumer object
        """
        return self.objectdb.find_one({'id': id})
    
    def packages(self, id):
        consumer = self.objectdb.find_one({'id': id}) 
        return consumer['package_profile']
    
    def consumers_with_package_name(self, name):
        """
        List consumers using passed in name
        """
        return list(self.objectdb.find({'package_profile.name': name},['id', 'description', 'repoids']))

    def bind(self, id, repoid):
        """
        Bind (subscribe) a consumer to a repo.
        @param id: A consumer id.
        @type id: str
        @param repoid: A repo id to bind.
        @type repoid: str
        @raise PulpException: When consumer not found.
        """
        consumer = self.consumer(id)
        if consumer is None:
            raise PulpException('consumer "%s", not-found', id)
        repoids = consumer['repoids']
        if repoid in repoids:
            return
        repoids.append(repoid)
        self.update(consumer)

    def unbind(self, id, repoid):
        """
        Unbind (unsubscribe) a consumer to a repo.
        @param id: A consumer id.
        @type id: str
        @param repoid: A repo id to unbind.
        @type repoid: str
        @raise PulpException: When consumer not found.
        """
        consumer = self.consumer(id)
        if consumer is None:
            raise PulpException('consumer "%s", not-found', id)
        repoids = consumer['repoids']
        if repoid not in repoids:
            return
        repoids.remove(repoid)
        self.update(consumer)
        
    def profile_update(self, id, package_profile):
        """
        Update the consumer information such as package profile
        """
        consumer = self.consumer(id)
        if consumer is None:
            raise PulpException('consumer "%s", not-found', id)
        consumer["package_profile"] =  package_profile
        self.update(consumer)

    def installpackages(self, id, packagenames=[]):
        """
        Install packages on the consumer.
        @param id: A consumer id.
        @type id: str
        @param packagenames: The package names to install.
        @type packagenames: [str,..]
        """
        agent = Agent(id)
        try:
            agent.packages.install(packagenames)
        finally:
            agent.close()
        return packagenames