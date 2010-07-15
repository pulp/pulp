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
import itertools
import logging

from pulp import model
from pulp.api.base import BaseApi
from pulp.auditing import audit
from pulp.pexceptions import PulpException
from pulp.util import chunks
from pulp.agent import Agent

# Pulp

log = logging.getLogger(__name__)
    
consumer_fields = model.Consumer(None, None).keys()


class ConsumerApi(BaseApi):

    def __init__(self, config):
        BaseApi.__init__(self, config)
        log.setLevel(config.get('logs', 'level'))

    def _getcollection(self):
        return self.db.consumers

    def _get_unique_indexes(self):
        return ["id"]

    def _get_indexes(self):
        return ["package_profile.name", "repoids"]

    @audit
    def create(self, id, description):
        """
        Create a new Consumer object and return it
        """
        consumer = self.consumer(id)
        if(consumer):
            raise PulpException("A Consumer with id %s already exists" % id)
        c = model.Consumer(id, description)
        self.insert(c)
        return c
        
    @audit
    def bulkcreate(self, consumers):
        """
        Create a set of Consumer objects in a bulk manner
        @type consumers: list of dictionaries
        @param consumers: dictionaries representing new consumers
        """
        ## Have to chunk this because of issue with PyMongo and network
        ## See: http://tinyurl.com/2eyumnc
        chunksize = 50
        chunked = chunks(consumers, chunksize)
        inserted = 0
        for chunk in chunked:
            self.objectdb.insert(chunk, check_keys=False, safe=False)
            inserted = inserted + chunksize

    def consumers(self, spec=None, fields=None):
        """
        List all consumers.  Can be quite large
        """
        return list(self.objectdb.find(spec=spec, fields=fields))

    def consumer(self, id, fields=None):
        """
        Return a single Consumer object
        """
        consumers = self.consumers({'id': id}, fields)
        if not consumers:
            return None
        return consumers[0]
    
    def packages(self, id):
        consumer = self.consumer(id)
        if consumer is None:
            raise PulpException('consumer "%s", not-found', id)
        return consumer.get('package_profile', [])
    
    def consumers_with_package_names(self, names, fields=None):
        """
        List consumers using passed in names
        """
        log.debug("consumers_with_package_names : %s" % names)
        consumers = []
        for name in names:
            #consumers.extend(self.objectdb.find({'package_profile.name': name}, fields))
            consumers.extend(self.consumers({'package_profile.name': name}, fields))
        return consumers

    @audit
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
        repoids = consumer.setdefault('repoids', [])
        if repoid in repoids:
            return
        repoids.append(repoid)
        self.update(consumer)

    @audit
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
        repoids = consumer.setdefault('repoids', [])
        if repoid not in repoids:
            return
        repoids.remove(repoid)
        self.update(consumer)
        
    @audit
    def profile_update(self, id, package_profile):
        """
        Update the consumer information such as package profile
        """
        consumer = self.consumer(id)
        if consumer is None:
            raise PulpException('consumer "%s", not-found', id)
        consumer["package_profile"] =  package_profile
        self.update(consumer)

    @audit
    def installpackages(self, id, packagenames=[]):
        """
        Install packages on the consumer.
        @param id: A consumer id.
        @type id: str
        @param packagenames: The package names to install.
        @type packagenames: [str,..]
        """
        agent = Agent(id)
        agent.packages.install(packagenames)
        return packagenames
    
    @audit
    def installpackagegroups(self, id, packageids=[]):
        """
        Install package groups on the consumer.
        @param id: A consumer id.
        @type id: str
        @param packageids: The package ids to install.
        @type packageids: [str,..]
        """
        agent = Agent(id)
        agent.packagegroups.install(packageids)
        return packageids
