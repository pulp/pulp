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


TROUBLESHOOTING_URL = 'http://pulp-user-guide.readthedocs.org/en/2.4-release/troubleshooting.html%s'
QPID_MESSAGING_URL = TROUBLESHOOTING_URL % '#qpid-messaging-is-not-installed'
QPIDTOOLLIBS_URL = TROUBLESHOOTING_URL % '#qpidtoollibs-is-not-installed'
CANNOT_DELETE_QUEUE_URL = TROUBLESHOOTING_URL % '#pulp-manage-db-gives-an-error-cannot-delete-queue'


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
                'installed. Please install qpid.messaging and rerun the migrations. See %s'
                'for more information.')
        msg = msg % QPID_MESSAGING_URL
        logger.error(msg)
        raise Exception(msg)

    if not QPIDTOOLLIBS_AVAILABLE:
        msg = _('Migration 0009 did not run because the python package qpidtoollibs is not '
                'installed. Please install qpidtoollibs and rerun the migrations. See %s for more '
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
        _del_queue_catch_queue_in_use_exception(broker, name)
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
        _del_queue_catch_queue_in_use_exception(broker, name)


def _del_queue_catch_queue_in_use_exception(broker, name):
    """
    Delete a queue, and catch a 'queue in use' exception. If the queue is in use, raise an exception.

    :param broker: The broker instance to delete the queue with.
    :type broker: BrokerAgent
    :param name: The name of the queue to delete
    :type name: basestring
    :return:
    """
    try:
        broker.delQueue(name)
    except Exception as exc:
        if 'Cannot delete queue' in exc.message and 'queue in use' in exc.message:
            msg_data = {'queue_name': name, 'cannot_delete_queue_url': CANNOT_DELETE_QUEUE_URL}
            msg = _(
                "Consumers are still bound to the queue '%(queue_name)s'. "
                "All consumers must be unregistered, upgraded, or off "
                "before you can continue. Read more about this issue "
                "here:\n\n%(cannot_delete_queue_url)s")
            msg = msg % msg_data
            logger.error(msg)
            raise Exception(msg)
        raise
