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

"""
Contains (proxy) classes that represent the pulp agent.
"""

import hashlib
from agenthub.rest import Rest
from agenthub.client import Agent
from pulp.server.exceptions import PulpDataException
from logging import getLogger


log = getLogger(__name__)

#
# Constants
#

HOST = 'localhost'
PORT = 443


#
# Main Agent
#

class PulpAgent(Agent):
    """
    Represents a remote pulp agent.
    """
    
    @classmethod
    def status(cls, uuids=[]):
        rest = Rest(HOST, PORT)
        path = '/agenthub/agent/%s/' % uuids[0]
        reply = rest.get(path)
        return reply[1]

    @classmethod
    def getsecret(cls, consumer):
        secret = None
        certificate = consumer.get('certificate')
        if certificate:
            hash = hashlib.sha256()
            hash.update(certificate.strip())
            secret = hash.hexdigest()
        return secret

    def __init__(self, consumer):
        self.uuid = consumer['id']
        self.secret = self.getsecret(consumer)
        
    def replyto(self):
        return dict(
            systemid='pulp',
            method='POST',
            path='/agent/%s/reply/' % self.uuid)
        
    def unregistered(self):
        agent = Agent(self.uuid, Rest(HOST, PORT), secret=self.secret)
        consumer = agent.Consumer()
        consumer.unregistered()
    
    def bind(self, repoid):
        pass
    
    def unbind(self, repoid):
        pass
    
    def send_profile(self):
        pass
        
    def install_units(self, units, options):
        taskid = options.get('taskid')
        if not taskid:
            raise PulpDataException('taskid required')
        agent = Agent(
            self.uuid,
            Rest(HOST, PORT),
            timeout=(10, 90),
            secret=self.secret,
            replyto=self.replyto(),
            any=taskid)
        content = Agent.Content()
        result = content.install(units, options)
        # TODO: process 
    
    def update_units(self, units, options):
        taskid = options.get('taskid')
        if not taskid:
            raise PulpDataException('taskid required')
        agent = Agent(
            self.uuid,
            Rest(HOST, PORT),
            timeout=(10, 90),
            secret=self.secret,
            replyto=self.replyto(),
            any=taskid)
        content = Agent.Content()
        result = content.update(units, options)
        # TODO: process 
    
    def uninstall_units(self, units, options):
        taskid = options.get('taskid')
        if not taskid:
            raise PulpDataException('taskid required')
        agent = Agent(
            self.uuid,
            Rest(HOST, PORT),
            timeout=(10, 90),
            secret=self.secret,
            replyto=self.replyto(),
            any=taskid)
        content = Agent.Content()
        result = content.uninstall(units, options)
        # TODO: process 


#
# CDS
#

class CdsAgent(Agent):
    """
    Represents a remote CDS agent.
    """

    @classmethod
    def uuid(cls, cds):
        return 'cds-%s' % cds['hostname']

    def __init__(self, cds, **options):
        uuid = self.uuid(cds)
        options['secret'] = cds.get('secret')
        # TBD
        
    def register(self):
        pass
    
    def unregister(self):
        pass
    
    def sync(self, data):
        pass
    
    def update_cluster_membership(self, cluster_name, member_cds_hostnames):
        pass
