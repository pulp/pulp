# Copyright (c) 2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from urlparse import urlparse

from qpidtoollibs import BrokerAgent
from qpid.messaging import Connection

from pulp.server.config import config as pulp_conf
from pulp.server.agent.direct.services import Services
from pulp.server.db.model.consumer import Consumer


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
