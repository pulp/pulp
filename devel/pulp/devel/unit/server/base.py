import os
import unittest
import mock
from pulp.server.db import connection


class PulpWebservicesTests(unittest.TestCase):
    """
    Base class for tests of webservice controllers.  This base is used to work around the
    authentication tests for each each method
    """

    def setUp(self):
        connection.initialize()
        self.patch1 = mock.patch('pulp.server.webservices.controllers.decorators.'
                                 'check_preauthenticated')
        self.patch2 = mock.patch('pulp.server.webservices.controllers.decorators.'
                                 'is_consumer_authorized')
        self.patch3 = mock.patch('pulp.server.webservices.http.resource_path')
        self.patch4 = mock.patch('pulp.server.webservices.http.header')
        self.patch5 = mock.patch('web.webapi.HTTPError')
        self.patch6 = mock.patch('pulp.server.managers.factory.principal_manager')
        self.patch7 = mock.patch('pulp.server.managers.factory.user_query_manager')

        self.patch8 = mock.patch('pulp.server.webservices.http.uri_path')
        self.mock_check_pre_auth = self.patch1.start()
        self.mock_check_pre_auth.return_value = 'ws-user'
        self.mock_check_auth = self.patch2.start()
        self.mock_check_auth.return_value = True
        self.mock_http_resource_path = self.patch3.start()
        self.patch4.start()
        self.patch5.start()
        self.patch6.start()
        self.mock_user_query_manager = self.patch7.start()
        self.mock_user_query_manager.return_value.is_superuser.return_value = False
        self.mock_user_query_manager.return_value.is_authorized.return_value = True
        self.mock_uri_path = self.patch8.start()
        self.mock_uri_path.return_value = "/mock/"

    def tearDown(self):
        self.patch1.stop()
        self.patch2.stop()
        self.patch3.stop()
        self.patch4.stop()
        self.patch5.stop()
        self.patch6.stop()
        self.patch7.stop()
        self.patch8.stop()

    def validate_auth(self, operation):
        """
        validate that a validation check was performed for a given operation
        :param operation: the operation to validate
        """
        self.mock_user_query_manager.return_value.is_authorized.assert_called_once_with(mock.ANY, mock.ANY, operation)

    def get_mock_uri_path(self, *args):
        """
        :param object_id: the id of the object to get the uri for
        :type object_id: str
        """
        return os.path.join('/mock', *args) + '/'