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

# Pulp
from pulp.cds.cdslib import CdsLib, SecretFile

log = logging.getLogger(__name__)
plugin = Plugin.find(__name__)
config = plugin.cfg()
cdslib = CdsLib(config)
producer = None


SECRET_FILE = config.messaging.secret_file
HEARTBEAT = config.heartbeat.seconds


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
def sync(base_url, repos):
    '''
    See cdslib.CdsLib.sync for details.
    '''
    log.info('Received sync call')
    cdslib.sync(base_url, repos)

@remote(secret=getsecret)
def set_repo_auth(repo_id, repo_relative_path, bundle):
    '''
    See cdslib.CdsLib.set_repo_auth for details.
    '''
    log.info('Setting repo auth credentials for repo [%s]' % repo_id)
    cdslib.set_repo_auth(repo_id, repo_relative_path, bundle)

@remote(secret=getsecret)
def set_global_repo_auth(bundle):
    '''
    See cdslib.CdsLib.set_global_repo_auth for details.
    '''
    log.info('Setting global repo auth credentials')
    cdslib.set_global_repo_auth(bundle)
    