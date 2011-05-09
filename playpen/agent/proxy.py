#
# Functions for getting proxies for
# both consumer and CDS agents.  Proxies are
# configured with proper shared secret credentials.
#

from pulp.server.db import connection as db
from pulp.server.db.model import CDS
from pulp.server.api.consumer import ConsumerApi
from pulp.server.api.cds import CdsApi
from pulp.server.agent import Agent

db.initialize()

def agent(id, **options):
    """ get a consumer agent proxy """
    capi = ConsumerApi()
    consumer = capi.consumer(id)
    if consumer is None:
        print 'consumer (%s), not-found' % id
        return
    return capi._getagent(consumer, **options)

def cds(id, **options):
    """ get a CDS agent proxy """
    api = CdsApi()
    cds = api.cds(id)
    if cds is None:
        print 'cds (%s), not-found' % id
        return
    uuid = CDS.uuid(cds)
    opt = dict(secret=cds['secret'])
    opt.update(options)
    return Agent(uuid, **opt)
