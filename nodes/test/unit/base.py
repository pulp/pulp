# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from ConfigParser import SafeConfigParser
from unittest import TestCase
import base64
import json
import logging
import mock
import os
import shutil

from paste.fixture import TestApp
import okaara
import web

from pulp.bindings.bindings import Bindings
from pulp.bindings.server import PulpConnection
from pulp.client.extensions.core import PulpCli, ClientContext, PulpPrompt
from pulp.client.extensions.exceptions import ExceptionHandler
from pulp.common.config import Config
from pulp.server.config import config as pulp_conf
from pulp.server.db import connection
from pulp.server.db.model.auth import User
from pulp.server.db.model.dispatch import QueuedCall
from pulp.server.dispatch import factory as dispatch_factory
from pulp.server.logs import start_logging, stop_logging
from pulp.server.managers import factory as managers
from pulp.server.managers.auth.cert.cert_generator import SerialNumber
from pulp.server.managers.auth.role.cud import SUPER_USER_ROLE
from pulp.server.webservices import http
from pulp.server.webservices.middleware.exception import ExceptionHandlerMiddleware
from pulp.server.webservices.middleware.postponed import PostponedOperationMiddleware


SerialNumber.PATH = '/tmp/sn.dat'


class ServerTests(TestCase):

    TMP_ROOT = '/tmp/pulp/nodes'

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(cls.TMP_ROOT):
            os.makedirs(cls.TMP_ROOT)
        stop_logging()
        path = os.path.join(
            os.path.abspath(os.path.dirname(__file__)),
            'data',
            'pulp.conf')
        pulp_conf.read(path)
        start_logging()
        storage_dir = pulp_conf.get('server', 'storage_dir')
        if not os.path.exists(storage_dir):
            os.makedirs(storage_dir)
        shutil.rmtree(storage_dir+'/*', ignore_errors=True)
        name = pulp_conf.get('database', 'name')
        connection.initialize(name)
        managers.initialize()

    @classmethod
    def tearDownClass(cls):
        name = pulp_conf.get('database', 'name')
        connection._CONNECTION.drop_database(name)

    def setUp(self):
        QueuedCall.get_collection().remove()
        dispatch_factory.initialize()

    def tearDown(self):
        dispatch_factory.finalize(True)


class WebTest(ServerTests):

    TEST_APP = None
    ORIG_HTTP_REQUEST_INFO = None
    HEADERS = None
    USER = ('elmer', 'fudd')

    @classmethod
    def setUpClass(cls):
        ServerTests.setUpClass()
        from pulp.server.webservices import application
        pulp_app = web.subdir_application(application.URLS).wsgifunc()
        pulp_stack_components = [
            pulp_app,
            PostponedOperationMiddleware,
            ExceptionHandlerMiddleware
        ]
        pulp_stack = reduce(lambda a, m: m(a), pulp_stack_components)
        cls.TEST_APP = TestApp(pulp_stack)
        def request_info(key):
            if key == "REQUEST_URI":
                key = "PATH_INFO"
            return web.ctx.environ.get(key, None)
        cls.ORIG_HTTP_REQUEST_INFO = http.request_info
        http.request_info = request_info
        base64string = base64.encodestring('%s:%s' % cls.USER)[:-1]
        cls.HEADERS = {'Authorization': 'Basic %s' % base64string}

    @classmethod
    def tearDownClass(cls):
        ServerTests.tearDownClass()
        http.request_info = cls.ORIG_HTTP_REQUEST_INFO

    def setUp(self):
        ServerTests.setUp(self)
        roles = []
        User.get_collection().remove()
        manager = managers.user_manager()
        roles.append(SUPER_USER_ROLE)
        manager.create_user(login=self.USER[0], password=self.USER[1], roles=roles)

    def tearDown(self):
        ServerTests.tearDown(self)
        User.get_collection().remove()

    def request(self, method, uri, params):
        v2_pos = uri.find('/v2')
        uri = uri[v2_pos:]
        headers = dict(self.HEADERS)
        if params is None:
            params = {}
        fn = getattr(self.TEST_APP, method.lower())
        response = fn('http://localhost'+uri, params=params, headers=headers, expect_errors=True)
        status = response.status
        try:
            body = json.loads(response.body)
        except ValueError:
            body = None
        return (status, body)


class ClientTests(TestCase):

    def setUp(self):
        TestCase.setUp(self)
        self.config = SafeConfigParser()
        path = os.path.join(
            os.path.abspath(os.path.dirname(__file__)),
            'data',
            'client.conf')
        self.config = Config(path)
        self.server_mock = mock.Mock()
        self.pulp_connection = \
            PulpConnection('', server_wrapper=self.server_mock)
        self.bindings = Bindings(self.pulp_connection)
        self.recorder = okaara.prompt.Recorder()
        self.prompt = PulpPrompt(enable_color=False, output=self.recorder, record_tags=True)
        self.logger = logging.getLogger('pulp')
        self.exception_handler = ExceptionHandler(self.prompt, self.config)
        self.context = ClientContext(
            self.bindings,
            self.config,
            self.logger,
            self.prompt,
            self.exception_handler)
        self.cli = PulpCli(self.context)
        self.context.cli = self.cli


class Response:

    def __init__(self, code, body):
        self.response_code = code
        self.response_body = body


class Task:

    def __init__(self, task_id=0):
        self.task_id = task_id
