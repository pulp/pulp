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

import base64
import httplib
import logging
import mock
import okaara.prompt
import os
from paste.fixture import TestApp
import sys
import time
import web
import unittest

try:
    import json
except ImportError:
    import simplejson as json

srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src/"
sys.path.insert(0, srcdir)

from pulp.server.managers.auth.user import UserManager

from pulp.bindings.bindings import Bindings
from pulp.bindings.server import  PulpConnection

from pulp.client.extensions.core import ClientContext, PulpPrompt, PulpCli
from pulp.client.extensions.exceptions import ExceptionHandler

from pulp.common.config import Config

from pulp.server import constants
from pulp.server import config
from pulp.server.auth import authorization
from pulp.server.auth.cert_generator import SerialNumber
from pulp.server.db import connection
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.dispatch import factory as dispatch_factory
from pulp.server.logs import start_logging, stop_logging
from pulp.server.managers import factory as manager_factory
from pulp.server.webservices import http
from pulp.server.webservices.middleware.exception import ExceptionHandlerMiddleware
from pulp.server.webservices.middleware.postponed import PostponedOperationMiddleware

# test configuration -----------------------------------------------------------

SerialNumber.PATH = '/tmp/sn.dat'
constants.LOCAL_STORAGE = '/tmp/pulp/'
constants.CACHE_DIR = '/tmp/pulp/cache'


def load_test_config():
    if not os.path.exists('/tmp/pulp'):
        os.makedirs('/tmp/pulp')

    override_file = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data', 'test-override-pulp.conf')
    override_repo_file = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data', 'test-override-repoauth.conf')
    stop_logging()
    try:
        config.add_config_file(override_file)
        config.add_config_file(override_repo_file)
    except RuntimeError:
        pass
    start_logging()

    return config.config

# base unittest class ----------------------------------------------------------

class PulpServerTests(unittest.TestCase):
    """
    Base functionality for all Pulp server-side unit tests. This should be used
    in nearly all cases outside of the controllers.
    """

    CONFIG = None

    @classmethod
    def setUpClass(cls):
        PulpServerTests.CONFIG = load_test_config()
        connection.initialize()
        manager_factory.initialize()

    def setUp(self):
        super(PulpServerTests, self).setUp()

        self._mocks = {}
        self.config = PulpServerTests.CONFIG # shadow for simplicity

        self.setup_async() # deprecated; being removed

        self.clean()

    def tearDown(self):
        super(PulpServerTests, self).tearDown()
        self.unmock_all()
        self.teardown_async()

        self.clean()

    def clean(self):
        pass

    def setup_async(self):
        pass

    def teardown_async(self):
        pass

    def mock(self, parent, attribute, mock_object=None):
        self._mocks.setdefault(parent, {})[attribute] = getattr(parent, attribute)
        if mock_object is None:
            mock_object = mock.Mock()
        setattr(parent, attribute, mock_object)

    def unmock_all(self):
        for parent in self._mocks:
            for mocked_attr, original_attr in self._mocks[parent].items():
                setattr(parent, mocked_attr, original_attr)


class PulpWebserviceTests(PulpServerTests):
    """
    Base unit test class for all webservice controller tests.
    """

    TEST_APP = None
    ORIG_HTTP_REQUEST_INFO = None
    HEADERS = None

    @classmethod
    def setUpClass(cls):
        PulpServerTests.setUpClass()

        # The application setup is somewhat time consuming and really only needs
        # to be done once. We might be able to move it out to a single call for
        # the entire test suite, but for now I'm seeing performance improvements
        # by only doing it once per class instead of on every run.

        # Because our code is a tightly coupled mess, the test config has to be
        # loaded before we can import application
        load_test_config()
        from pulp.server.webservices import application

        pulp_app = web.subdir_application(application.URLS).wsgifunc()
        pulp_stack_components = [pulp_app, PostponedOperationMiddleware, ExceptionHandlerMiddleware]
        pulp_stack = reduce(lambda a, m: m(a), pulp_stack_components)
        PulpWebserviceTests.TEST_APP = TestApp(pulp_stack)

        def request_info(key):
            if key == "REQUEST_URI":
                key = "PATH_INFO"

            return web.ctx.environ.get(key, None)

        PulpWebserviceTests.ORIG_HTTP_REQUEST_INFO = http.request_info
        http.request_info = request_info

        base64string = base64.encodestring('%s:%s' % ('ws-user', 'ws-user'))[:-1]
        PulpWebserviceTests.HEADERS = {'Authorization' : 'Basic %s' % base64string}

    @classmethod
    def tearDownClass(cls):
        http.request_info = PulpWebserviceTests.ORIG_HTTP_REQUEST_INFO

    def setUp(self):
        super(PulpWebserviceTests, self).setUp()
        self.coordinator = dispatch_factory.coordinator()
        self.success_failure = None
        self.result = None
        self.exception = None
        self.traceback = None

        # The built in PulpTest clean will automatically delete users between
        # test runs, so we can't just create the user in the class level setup.
        user_manager = UserManager()
        roles = []
        roles.append(authorization.super_user_role)
        user_manager.create_user(login='ws-user', password='ws-user', roles=roles)

    def tearDown(self):
        super(PulpWebserviceTests, self).tearDown()

        user_manager = UserManager()
        user_manager.delete_user(login='ws-user')

    def setup_async(self):
        dispatch_factory.initialize()

    def teardown_async(self):
        dispatch_factory.finalize(clear_queued_calls=True)

    def get(self, uri, params=None, additional_headers=None):
        return self._do_request('get', uri, params, additional_headers)

    def post(self, uri, params=None, additional_headers=None):
        return self._do_request('post', uri, params, additional_headers)

    def delete(self, uri, params=None, additional_headers=None):
        return self._do_request('delete', uri, params, additional_headers)

    def put(self, uri, params=None, additional_headers=None, serialize_json=True):
        return self._do_request('put', uri, params, additional_headers, serialize_json=serialize_json)

    def _do_request(self, request_type, uri, params, additional_headers, serialize_json=True):
        """
        Override the base class controller to allow for less deterministic
        responses due to integration with the dispatch package.
        """

        def _is_not_error(status):
            return status in (httplib.OK, httplib.ACCEPTED)

        def _is_task_response(body):
            return body is not None and 'reasons' in body and 'state' in body

        def _is_not_finished(body):
            return body['state'] not in dispatch_constants.CALL_COMPLETE_STATES

        def _poll_async_request(status, body):
            if self.success_failure is not None and body['state'] == dispatch_constants.CALL_RUNNING_STATE:
                task_id = body['_href'].split('/')[-2]
                if self.success_failure == 'success':
                    self.coordinator.complete_call_success(task_id, self.result)
                else:
                    self.coordinator.complete_call_failure(task_id, self.exception, self.traceback)
                self._reset_success_failure()

            while _is_not_error(status) and _is_task_response(body) and _is_not_finished(body):
                uri = body['_href'][9:]
                status, body = self.get(uri) # cool recursive call

            if _is_task_response(body):
                if body['state'] == dispatch_constants.CALL_ERROR_STATE:
                    return status, body['exception']
                if _is_not_error(status):
                    return status, body['result']
            return status, body

        # Use the default headers established at setup and override/add any
        headers = dict(PulpWebserviceTests.HEADERS)
        if additional_headers is not None:
            headers.update(additional_headers)

        # Serialize the parameters if any are specified
        if params is None:
            params = {}

        if serialize_json:
            params = json.dumps(params)

        # Invoke the API
        f = getattr(PulpWebserviceTests.TEST_APP, request_type)
        response = f('http://localhost' + uri, params=params, headers=headers, expect_errors=True)

        # Collect return information and deserialize it
        status = response.status
        try:
            body = json.loads(response.body)
        except ValueError:
            body = None

        if _is_not_error(status) and _is_task_response(body):
            return _poll_async_request(status, body)
        return status, body

    def _reset_success_failure(self):
        self.success_failure = None
        self.result = None
        self.exception = None
        self.traceback = None

    def set_success(self, result=None):
        self.success_failure = 'success'
        self.result = result

    def set_failure(self, exception=None, traceback=None):
        self.success_failure = 'failure'
        self.exception = exception
        self.traceback = traceback


class PulpClientTests(unittest.TestCase):
    """
    Base unit test class for all extension unit tests.
    """

    def setUp(self):
        super(PulpClientTests, self).setUp()

        config_filename = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data', 'test-override-admin.conf')
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
