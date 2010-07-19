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

from pulp import model
from pulp.agent import Agent
from pulp.api.base import BaseApi
from pulp.auditing import audit
from pulp.pexceptions import PulpException

# Pulp
from pulp.api.consumer import ConsumerApi
from pulp.api.repo import RepoApi


log = logging.getLogger('pulp.api.consumergroup')

class ConsumerGroupApi(BaseApi):

    def __init__(self, config):
        BaseApi.__init__(self, config)
        self.consumerApi = ConsumerApi(config)
        self.repoApi = RepoApi(config)

    def _getcollection(self):
        return self.db.consumergroups


    @audit('ConsumerGroupApi', params=['id', 'consumerids'])
    def create(self, id, description, consumerids=[]):
        """
        Create a new ConsumerGroup object and return it
        """
        consumergroup = self.consumergroup(id)
        if(consumergroup):
            raise PulpException("A Consumer Group with id %s already exists" % id)
        
        for consumerid in consumerids:
            consumer = self.consumerApi.consumer(consumerid)
            if (consumer == None):
                raise PulpException("No Consumer with id: %s found" % consumerid)
                
        c = model.ConsumerGroup(id, description, consumerids)
        self.insert(c)
        return c


    def consumergroups(self):
        """
        List all consumergroups.
        """
        consumergroups = list(self.objectdb.find())
        return consumergroups

    def consumergroup(self, id):
        """
        Return a single ConsumerGroup object
        """
        return self.objectdb.find_one({'id': id})


    def consumers(self, id):
        """
        Return consumer ids belonging to this ConsumerGroup
        """
        consumer = self.objectdb.find_one({'id': id})
        return consumer['consumerids']


    @audit('ConsumerGroupApi', params=['groupid', 'consumerid'])
    def add_consumer(self, groupid, consumerid):
        """
        Adds the passed in consumer to this group
        """
        consumergroup = self.consumergroup(groupid)
        if (consumergroup == None):
            raise PulpException("No Consumer Group with id: %s found" % groupid)
        consumer = self.consumerApi.consumer(consumerid)
        if (consumer == None):
            raise PulpException("No Consumer with id: %s found" % consumerid)
        self._add_consumer(consumergroup, consumer)
        self.update(consumergroup)

    def _add_consumer(self, consumergroup, consumer):
        """
        Responsible for properly associating a Consumer to a ConsumerGroup
        """
        consumerids = consumergroup['consumerids']
        if consumer["id"] in consumerids:
            return
        
        consumerids.append(consumer["id"])
        consumergroup["consumerids"] = consumerids

    @audit('ConsumerGroupApi', params=['groupid', 'consumerid'])
    def delete_consumer(self, groupid, consumerid):
        consumergroup = self.consumergroup(groupid)
        if (consumergroup == None):
            raise PulpException("No Consumer Group with id: %s found" % groupid)
        consumerids = consumergroup['consumerids']
        if consumerid not in consumerids:
            return
        consumerids.remove(consumerid)
        consumergroup["consumerids"] = consumerids
        self.update(consumergroup)

    @audit('ConsumerGroupApi', params=['id', 'repoid'])
    def bind(self, id, repoid):
        """
        Bind (subscribe) a consumer group to a repo.
        @param id: A consumer group id.
        @type id: str
        @param repoid: A repo id to bind.
        @type repoid: str
        @raise PulpException: When consumer group is not found.
        """
        consumergroup = self.consumergroup(id)
        if consumergroup is None:
            raise PulpException("No Consumer Group with id: %s found" % id)
        repo = self.repoApi.repository(repoid)
        if repo is None:
            raise PulpException("No Repository with id: %s found" % repoid)

        consumerids = consumergroup['consumerids']
        for consumerid in consumerids:
            self.consumerApi.bind(consumerid, repoid)

    @audit('ConsumerGroupApi', params=['id', 'repoid'])
    def unbind(self, id, repoid):
        """
        Unbind (unsubscribe) a consumer group from a repo.
        @param id: A consumer group id.
        @type id: str
        @param repoid: A repo id to unbind.
        @type repoid: str
        @raise PulpException: When consumer group not found.
        """
        consumergroup = self.consumergroup(id)
        if consumergroup is None:
            raise PulpException("No Consumer Group with id: %s found" % id)
        repo = self.repoApi.repository(repoid)
        if (repo == None):
            raise PulpException("No Repository with id: %s found" % repoid)

        consumerids = consumergroup['consumerids']
        for consumerid in consumerids:
            self.consumerApi.unbind(consumerid, repoid)
            
            
    @audit('ConsumerGroupApi', params=['id', 'packagenames'])
    def installpackages(self, id, packagenames=[]):
        """
        Install packages on the consumers in a consumer group.
        @param id: A consumer group id.
        @type id: str
        @param packagenames: The package names to install.
        @type packagenames: [str,..]
        """
        consumergroup = self.consumergroup(id)
        if consumergroup is None:   
            raise PulpException("No Consumer Group with id: %s found" % id)
        consumerids = consumergroup['consumerids']
        for consumerid in consumerids:
            agent = Agent(consumerid)
            agent.packages.install(packagenames)
        return packagenames
