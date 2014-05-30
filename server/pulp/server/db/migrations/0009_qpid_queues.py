from gettext import gettext as _
import logging
from urlparse import urlparse

try:
    from qpidtoollibs import BrokerAgent
    QPIDTOOLLIBS_AVAILABLE = True
except ImportError:
    QPIDTOOLLIBS_AVAILABLE = False

try:
    from qpid.messaging import Connection
    QPID_MESSAGING_AVAILABLE = True
except ImportError:
    QPID_MESSAGING_AVAILABLE = False

from pulp.server.config import config as pulp_conf
from pulp.server.agent.direct.services import Services
from pulp.server.db.model.consumer import Consumer


TROUBLESHOOTING_URL = 'http://pulp-user-guide.readthedocs.org/en/pulp-2.4/troubleshooting.html%s'
QPID_MESSAGING_URL = TROUBLESHOOTING_URL % '#qpid-messaging-is-not-installed'
QPIDTOOLLIBS_URL = TROUBLESHOOTING_URL % '#qpidtoollibs-is-not-installed'


logger = logging.getLogger(__name__)


def migrate(*args, **kwargs):
    """
    Migrate qpid queues:
    - Ensure pulp.task is no longer *exclusive*.
    - Rename agent queues: consumer_id> => pulp.agent.<consumer_id>
    """
    transport = pulp_conf.get('messaging', 'transport')
    if transport != 'qpid':
        # not using qpid
        return

    if not QPID_MESSAGING_AVAILABLE:
        msg = _('Migration 0009 did not run because the python package qpid.messaging is not '
                'installed.  Please install qpid.messaging and rerun the migrations. See %s'
                'for more information.')
        msg = msg % QPID_MESSAGING_URL
        logger.error(msg)
        raise Exception(msg)

    if not QPIDTOOLLIBS_AVAILABLE:
        msg = _('Migration 0009 did not run because the python package qpidtoollibs is not '
                'installed.  Please install qpidtoollibs and rerun the migrations. See %s for more '
                'information.')
        msg = msg % QPIDTOOLLIBS_URL
        logger.error(msg)
        raise Exception(msg)

    url = urlparse(pulp_conf.get('messaging', 'url'))
    connection = Connection(
        host=url.hostname,
        port=url.port,
        transport=url.scheme,
        reconnect=False,
        ssl_certfile=pulp_conf.get('messaging', 'clientcert'),
        ssl_skip_hostname_check=True)

    connection.attach()
    broker = BrokerAgent(connection)
    _migrate_reply_queue(broker)
    _migrate_agent_queues(broker)
    connection.detach()


def _migrate_reply_queue(broker):
    """
    Ensure pulp.task is no longer *exclusive*.
    :param broker: A qpidtools broker.
    :type broker: BrokerAgent
    """
    name = Services.REPLY_QUEUE
    queue = broker.getQueue(name)
    if not queue:
        # nothing to migrate
        return
    if queue.values['exclusive'] or queue.values['arguments'].get('exclusive', False):
        broker.delQueue(name)
        broker.addQueue(name, durable=True)


def _migrate_agent_queues(broker):
    """
    Rename agent queues: consumer_id> => pulp.agent.<consumer_id>
    :param broker: A qpidtools broker.
    :type broker: BrokerAgent
    """
    _add_agent_queues(broker)
    _del_agent_queues(broker)


def _add_agent_queues(broker):
    """
    Add queues named: pulp.agent.<consumer_id> foreach consumer.
    :param broker: A qpidtools broker.
    :type broker: BrokerAgent
    """
    collection = Consumer.get_collection()
    for consumer in collection.find():
        name = 'pulp.agent.%s' % consumer['id']
        queue = broker.getQueue(name)
        if queue:
            # already created
            continue
        broker.addQueue(name, durable=True)


def _del_agent_queues(broker):
    """
    Delete queues named: <consumer_id> foreach consumer.
    :param broker: A qpidtools broker.
    :type broker: BrokerAgent
    """
    collection = Consumer.get_collection()
    for consumer in collection.find():
        name = consumer['id']
        queue = broker.getQueue(name)
        if not queue:
            # nothing to delete
            continue
        broker.delQueue(name)
