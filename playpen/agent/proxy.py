#
# Functions for getting proxies for
# both consumer and CDS agents.  Proxies are
# configured with proper shared secret credentials.
#

from pulp.server.db import connection as db
from pulp.server.api.consumer import ConsumerApi
from pulp.server.api.cds import CdsApi
from pulp.server.agent import CdsAgent, PulpAgent

db.initialize()

def agent(id, **options):
    """ get a consumer agent proxy """
    capi = ConsumerApi()
    consumer = capi.consumer(id)
    if consumer is None:
        print 'consumer (%s), not-found' % id
        return
    return PulpAgent(consumer, **options)

def cds(id, **options):
    """ get a CDS agent proxy """
    api = CdsApi()
    cds = api.cds(id)
    if cds is None:
        print 'cds (%s), not-found' % id
        return
    return CdsAgent(cds, **options)
