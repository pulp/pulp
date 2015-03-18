from unittest import TestCase

from mock import patch

from pulp.server.agent.connector import get_url, add_connector


messaging = {
    'url': 'atlantis',
    'cacert': '/path/ca',
    'clientcert': '/path/cert',
    'transport': 'monkey'
}

conf = {
    'messaging': messaging
}


class Config(object):

    @staticmethod
    def get(section, _property):
        return conf[section][_property]


class TestConnector(TestCase):

    @patch('pulp.server.agent.connector.config', Config)
    def test_get_url(self):
        url = messaging['url']
        adapter = messaging['transport']
        self.assertEqual('+'.join((adapter, url)), get_url())

    @patch('pulp.server.agent.connector.Connector')
    @patch('pulp.server.agent.connector.get_url')
    @patch('pulp.server.agent.connector.config', Config)
    def test_add_connector(self, _get_url, _connector):
        add_connector()
        _connector.assert_called_with(_get_url.return_value)
        _connector.return_value.add.assert_called_with()
        self.assertEqual(_connector.return_value.ssl.ca_certificate, messaging['cacert'])
        self.assertEqual(_connector.return_value.ssl.client_certificate, messaging['clientcert'])
