import mock
import unittest

from mock import patch

from pulp.server.webservices.application import SaveEnvironWSGIHandler, wsgi_application
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


class TestSaveEnvironWSGIHandler(unittest.TestCase):
    """
    Contains tests for pulp.server.webservices.middleware.application.SaveEnvironWSGIHandler
    """
    def setUp(self):
        self.mock_django = mock.Mock()
        self.mock_django.return_value = 'mock_return'
        self.handler = SaveEnvironWSGIHandler(self.mock_django)

    def test_environ_wsgi_handler(self):
        """
        Test that when no exception is raised, the app response is returned.
        """
        wsgi_return_value = self.handler('arg1', 'arg2')
        self.assertTrue(self.mock_django.return_value is wsgi_return_value)
        self.mock_django.assert_called_once_with('arg1', 'arg2')
