import unittest

from mock import patch

from pulp.server.webservices.application import wsgi_application
from pulp.server.initialization import InitializationException


class TestApplication(unittest.TestCase):

    @patch('pulp.server.webservices.application._initialize_pulp')
    def test_wsgi_application_exception(self, mock_initialize_pulp):
        mock_initialize_pulp.side_effect = Exception
        self.assertRaises(Exception, wsgi_application)

    @patch('pulp.server.webservices.application._initialize_pulp')
    def test_wsgi_application_initilization_exception(self, mock_initialize_pulp):
        mock_initialize_pulp.side_effect = InitializationException('blah')
        self.assertRaises(InitializationException, wsgi_application)
