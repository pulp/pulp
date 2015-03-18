from gofer.messaging import Connector

from pulp.server.config import config


def get_url():
    """
    This constructs a gofer 2.x URL and is intended to maintain
    configuration file backwards compatibility until pulp 3.0

    :return: A gofer 2.x broker URL.
    :rtype: str
    """
    url = config.get('messaging', 'url')
    adapter = config.get('messaging', 'transport')
    return '+'.join((adapter, url))


def add_connector():
    """
    Configure and add the gofer connector used to connect
    to the message broker.  This call is idempotent.
    """
    url = get_url()
    connector = Connector(url)
    connector.ssl.ca_certificate = config.get('messaging', 'cacert')
    connector.ssl.client_certificate = config.get('messaging', 'clientcert')
    connector.add()

