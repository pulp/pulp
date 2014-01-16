#!/usr/bin/python
#
# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import logging
import os
import unittest

import mock
import okaara.prompt

from pulp.bindings.bindings import Bindings
from pulp.bindings.server import  PulpConnection

from pulp.client.extensions.core import ClientContext, PulpPrompt, PulpCli
from pulp.client.extensions.exceptions import ExceptionHandler

from pulp.common.config import Config

# base unittest class ----------------------------------------------------------


class PulpClientTests(unittest.TestCase):
    """
    Base unit test class for all extension unit tests.
    """

    def setUp(self):
        super(PulpClientTests, self).setUp()

        config_filename = os.path.join(os.path.abspath(os.path.dirname(__file__)), '../../../data/test-override-admin.conf')
        self.config = Config(config_filename)

        self.server_mock = mock.Mock()
        self.pulp_connection = PulpConnection('', server_wrapper=self.server_mock)
        self.bindings = Bindings(self.pulp_connection)

        # Disabling color makes it easier to grep results since the character codes aren't there
        self.recorder = okaara.prompt.Recorder()
        self.prompt = PulpPrompt(enable_color=False, output=self.recorder, record_tags=True)

        self.logger = logging.getLogger('pulp')
        self.exception_handler = ExceptionHandler(self.prompt, self.config)

        self.context = ClientContext(self.bindings, self.config, self.logger, self.prompt, self.exception_handler)

        self.cli = PulpCli(self.context)
        self.context.cli = self.cli


class PulpWebservicesTests(unittest.TestCase):
    """
    Base class for tests of webservice controllers.  This base is used to work around the
    authentication tests for each each method
    """

    def setUp(self):
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

    def get_mock_uri_path(self):
        """
        :param object_id: the id of the object to get the uri for
        :type object_id: str
        """
        return "/mock/"


class MockTaskResult():
    """
    Mock object for returning an async task result
    """
    def __init__(self, task_id, ):
        self.id = task_id