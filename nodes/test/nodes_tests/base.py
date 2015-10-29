from ConfigParser import SafeConfigParser
from unittest import TestCase
import logging
import mock
import os
import shutil
import unittest

import okaara
import pymongo
from pulp.bindings.bindings import Bindings
from pulp.bindings.server import PulpConnection
from pulp.client.extensions.core import PulpCli, ClientContext, PulpPrompt
from pulp.client.extensions.exceptions import ExceptionHandler
from pulp.common.config import Config
from pulp.server.async import celery_instance
from pulp.server.config import config as pulp_conf
from pulp.server.db import connection
from pulp.server.logs import start_logging, stop_logging
from pulp.server.managers import factory as managers
from pulp.server.managers.auth.cert.cert_generator import SerialNumber


SerialNumber.PATH = '/tmp/sn.dat'


class ServerTests(unittest.TestCase):

    TMP_ROOT = '/tmp/pulp/nodes'

    @classmethod
    def setUpClass(cls):
        # This will make Celery tasks run synchronously
        celery_instance.celery.conf.CELERY_ALWAYS_EAGER = True

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
        shutil.rmtree(storage_dir + '/*', ignore_errors=True)
        managers.initialize()

    @classmethod
    def tearDownClass(cls):
        name = pulp_conf.get('database', 'name')
        db = pymongo.database.Database(connection._CONNECTION, name)
        for name in db.collection_names():
            if name[:7] == 'system.':
                continue
            db.drop_collection(name)


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


class TaskResult:
    def __init__(self, task_id):
        self.spawned_tasks = [Task(task_id)]
