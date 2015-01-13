from pulp.server.managers import factory


TYPE_ID = 'amqp'


def handle_event(notifier_config, event):
    """
    Send the event out to an AMQP broker.

    :param notifier_config: dictionary with keys 'subject', which defines the
                            subject of each email message, and 'addresses',
                            which is a list of strings that are email addresses
                            that should receive this notification.
    :type  notifier_config: dict
    :param event:   Event instance
    :type  event:   pulp.server.event.data.event
    :return: None
    """

    factory.topic_publish_manager().publish(event, notifier_config.get('exchange'))
