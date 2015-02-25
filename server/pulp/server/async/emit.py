import logging
from kombu import Connection, Exchange, Producer

from pulp.server.config import config

DEFAULT_EXCHANGE_NAME = 'pulp.api.v2'
_logger = logging.getLogger(__name__)


def send(document, routing_key=None):
    """
    Attempt to send a message to the AMQP broker.

    If we cannot obtain a new connection then the message will be dropped. Note
    that we do not block when waiting for a connection.

    :param document: the taskstatus Document we want to send
    :type  document: mongoengine.Document
    :param routing_key: The routing key for the message
    :type  routing_key: str
    """

    # if the user has not enabled notifications, just bail
    event_notifications_enabled = config.getboolean('messaging', 'event_notifications_enabled')
    if not event_notifications_enabled:
        return

    try:
        payload = document.to_json()
    except TypeError:
        _logger.warn("unable to convert document to JSON; event message not sent")
        return

    broker_url = config.get('messaging', 'event_notification_url')

    notification_topic = Exchange(name=DEFAULT_EXCHANGE_NAME, type='topic')

    with Connection(broker_url) as connection:
        producer = Producer(connection)
        producer.maybe_declare(notification_topic)
        producer.publish(payload, exchange=notification_topic, routing_key=routing_key)
