# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

# Python
import logging
import os
import shutil
from uuid import uuid4

# 3rd Party
from gofer.agent.plugin import Plugin
from gofer.decorators import remote, action
from gofer.messaging import Topic
from gofer.messaging.producer import Producer
from StringIO import StringIO
from iniparse import SafeConfigParser

# Pulp
from pulp.cds.cdslib import CdsLib, SecretFile

def tosafe(cfg):
    safe = SafeConfigParser()
    fp = StringIO(str(cfg))
    safe.readfp(fp)
    return safe

log = logging.getLogger(__name__)
plugin = Plugin.find(__name__)
config = tosafe(plugin.cfg())
cdslib = CdsLib(config)
producer = None

SECRET_FILE = config.get('messaging', 'secret_file')
HEARTBEAT = config.get('heartbeat', 'seconds')


def getproducer():
    '''
    Get a gofer message producer
    @return: A producer.
    @rtype: L{Producer}
    '''
    global producer
    if not producer:
        broker = plugin.getbroker()
        url = str(broker.url)
        producer = Producer(url=url)
    return producer

def getsecret():
    '''
    Used in gofer decorator to get the shared secret.
    @return: The shared secret.
    @rtype: str
    '''
    secret = SecretFile(SECRET_FILE)
    return secret.read()

@action(seconds=HEARTBEAT)
def heartbeat():
    '''
    Send heartbeat.
    '''
    topic = Topic('heartbeat')
    interval = int(HEARTBEAT)
    secret = SecretFile(SECRET_FILE)
    if secret.read():
        p = getproducer()
        uuid = plugin.getuuid()
        body = dict(
            uuid=uuid,
            next=interval,
            cds={})
        p.send(topic, ttl=interval, heartbeat=body)
    else:
        log.debug('Not registered')

@remote(secret=getsecret)
def initialize():
    '''
    Initialize CDS (forwarded to CdsLib).
    Update and return the auth: shared secret.
    @return: The shared secret
    @rtype: str
    '''
    log.info('Received initialize call')
    uuid = str(uuid4())
    secret = SecretFile(SECRET_FILE)
    secret.write(uuid)
    cdslib.initialize()
    return uuid

@remote(secret=getsecret)
def release():
    '''
    Release the CDS (forwarded to CdsLib).
    Clear the shared secret.
    '''
    log.info('Received release call')
    secret = SecretFile(SECRET_FILE)
    secret.delete()
    cdslib.release()

@remote(secret=getsecret)
def sync(sync_data):
    '''
    See cdslib.CdsLib.sync for details.
    '''
    log.info('Received sync call')
    cdslib.sync(sync_data)

@remote(secret=getsecret)
def update_cluster_membership(cluster_name, cds_hostnames):
    '''
    See cdslib.CdsLib.update_cluster_membership for details.
    '''
    if cds_hostnames is None:
        members = 'None'
    else:
        members = ', '.join(cds_hostnames)
    log.info('Received group membership update; Cluster [%s], Members [%s]' % (cluster_name, members))
    cdslib.update_cluster_membership(cluster_name, cds_hostnames)