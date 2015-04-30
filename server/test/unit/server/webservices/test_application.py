"""
This module contains tests for the pulp.server.webservices.application module.
"""
import unittest

import mock

from pulp.server.initialization import InitializationException
from pulp.server.webservices import application


class InitializeWebServicesTestCase(unittest.TestCase):
    """
    This class contains tests for the _initialize_web_services() function.
    """
    @mock.patch('pulp.server.webservices.application._IS_INITIALIZED', False)
    @mock.patch('pulp.server.webservices.application.AgentServices.start')
    @mock.patch('pulp.server.webservices.application.initialization.initialize')
    @mock.patch('pulp.server.webservices.application.migration_models.check_package_versions')
    def test_calls_common_initialization(self, check_package_versions, initialize, start):
        """
        Assert that _initialize_web_services() calls the common initialization code.
        """
        application._initialize_web_services()

        check_package_versions.assert_called_once_with()
        initialize.assert_called_once_with()
        start.assert_called_once_with()

    @mock.patch('pulp.server.webservices.application._IS_INITIALIZED', False)
    @mock.patch('pulp.server.webservices.application.AgentServices.start')
    @mock.patch('pulp.server.webservices.application.initialization.initialize')
    @mock.patch('pulp.server.webservices.application.logs.start_logging')
    @mock.patch('pulp.server.webservices.application.migration_models.check_package_versions')
    def test_starts_logging(self, check_package_versions, start_logging, initialize, start):
        """
        Assert that _initialize_web_services() starts logging.
        """
        application._initialize_web_services()

        check_package_versions.assert_called_once_with()
        start_logging.assert_called_once_with()
        initialize.assert_called_once_with()
        start.assert_called_once_with()


class TestApplication(unittest.TestCase):

    @mock.patch('pulp.server.webservices.application._initialize_web_services')
    def test_wsgi_application_exception(self, mock_initialize_web_services):
        mock_initialize_web_services.side_effect = Exception
        self.assertRaises(Exception, application.wsgi_application)

    @mock.patch('pulp.server.webservices.application._initialize_web_services')
    def test_wsgi_application_initilization_exception(self, mock_initialize_web_services):
        mock_initialize_web_services.side_effect = InitializationException('blah')
        self.assertRaises(InitializationException, application.wsgi_application)


class TestSaveEnvironWSGIHandler(unittest.TestCase):
    """
    Contains tests for pulp.server.webservices.middleware.application.SaveEnvironWSGIHandler
    """
    def setUp(self):
        self.mock_django = mock.Mock()
        self.mock_django.return_value = 'mock_return'
        self.handler = application.SaveEnvironWSGIHandler(self.mock_django)

    def test_environ_wsgi_handler(self):
        """
        Test that when no exception is raised, the app response is returned.
        """
        wsgi_return_value = self.handler('arg1', 'arg2')
        self.assertTrue(self.mock_django.return_value is wsgi_return_value)
        self.mock_django.assert_called_once_with('arg1', 'arg2')
