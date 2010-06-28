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
from pulp.api.consumer import ConsumerApi


log = logging.getLogger('pulp.api.consumergroup')

class ConsumerGroupApi(BaseApi):

    def __init__(self, config):
        BaseApi.__init__(self, config)
        self.consumerApi = ConsumerApi(config)

    def _getcollection(self):
        return self.db.consumergroups


    def create(self, id, description, consumerids = []):
        """
        Create a new ConsumerGroup object and return it
        """
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

    def delete_consumer(self, groupid, consumerid):
        consumergroup = self.consumergroup(groupid)
        if (consumergroup == None):
            raise PulpException("No Consumer Group with id: %s found" % groupid)
        consumerids = consumergroup['consumerids']
        if consumerid not in consumerids:
            return
        consumerids.remove(consumerid)
        self.update(consumergroup)
