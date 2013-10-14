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

from copy import deepcopy
import base64
import os
import unittest

from paste.fixture import TestApp
import mock
import web

from pulp.common.compat import json
from pulp.server import config
from pulp.server.async import celery_instance
from pulp.server.db import connection
from pulp.server.db.model.auth import User
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.dispatch import factory as dispatch_factory
from pulp.server.logs import start_logging, stop_logging
from pulp.server.managers import factory as manager_factory
from pulp.server.managers.auth.cert.cert_generator import SerialNumber
from pulp.server.managers.auth.role.cud import SUPER_USER_ROLE
from pulp.server.webservices import http
from pulp.server.webservices.middleware.exception import ExceptionHandlerMiddleware
from pulp.server.webservices.middleware.postponed import PostponedOperationMiddleware


SerialNumber.PATH = '/tmp/sn.dat'


def load_test_config():
    if not os.path.exists('/tmp/pulp'):
        os.makedirs('/tmp/pulp')

    override_file = os.path.join(os.path.abspath(os.path.dirname(__file__)), '../data',
                                 'test-override-pulp.conf')
    override_repo_file = os.path.join(os.path.abspath(os.path.dirname(__file__)), '../data',
                                      'test-override-repoauth.conf')
    stop_logging()
    try:
        config.add_config_file(override_file)
        config.add_config_file(override_repo_file)
    except RuntimeError:
        pass
    start_logging()

    return config.config


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
        # This will make Celery tasks run synchronously
        celery_instance.celery.conf.CELERY_ALWAYS_EAGER = True

    def setUp(self):
        super(PulpServerTests, self).setUp()
        self._mocks = {}
        self.config = PulpServerTests.CONFIG # shadow for simplicity
        self.clean()

    def tearDown(self):
        super(PulpServerTests, self).tearDown()
        self.unmock_all()
        self.clean()

    def clean(self):
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


class PulpAsyncServerTests(PulpServerTests):
    """
    Intermediate test suite that starts and stops the asynchronous dispatch
    system, but doesn't setup the webservices.
    """

    def setUp(self):
        super(PulpAsyncServerTests, self).setUp()
        dispatch_factory.initialize()

    def tearDown(self):
        super(PulpAsyncServerTests, self).tearDown()
        dispatch_factory.finalize(clear_queued_calls=True)


class PulpWebserviceTests(PulpAsyncServerTests):
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
        user_manager = manager_factory.user_manager()
        roles = []
        roles.append(SUPER_USER_ROLE)
        user_manager.create_user(login='ws-user', password='ws-user', roles=roles)

    def tearDown(self):
        super(PulpWebserviceTests, self).tearDown()
        User.get_collection().remove()

    def get(self, uri, params=None, additional_headers=None):
        return self._do_request('get', uri, params, additional_headers, serialize_json=False)

    def post(self, uri, params=None, additional_headers=None):
        return self._do_request('post', uri, params, additional_headers)

    def delete(self, uri, params=None, additional_headers=None):
        return self._do_request('delete', uri, params, additional_headers)

    def put(self, uri, params=None, additional_headers=None, serialize_json=True):
        return self._do_request('put', uri, params, additional_headers,
                                serialize_json=serialize_json)

    def _do_request(self, request_type, uri, params, additional_headers, serialize_json=True):
        """
        Override the base class controller to allow for less deterministic
        responses due to integration with the dispatch package.
        """

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

        return status, body


class PulpItineraryTests(PulpAsyncServerTests):

    def setUp(self):
        PulpAsyncServerTests.setUp(self)
        TaskQueue.install()
        self.coordinator = dispatch_factory.coordinator()

    def tearDown(self):
        TaskQueue.uninstall()
        PulpAsyncServerTests.tearDown(self)

    def run_next(self):
        TaskQueue.run_next()

    def cancel(self, request_id):
        self.coordinator.cancel_call(request_id)


class RecursiveUnorderedListComparisonMixin(object):
    """
    This mixin adds an assert_equal_ignoring_list_order, which is handy for comparing data
    structures that are or contain lists wherein the ordering of the lists is not
    significant.
    """
    def assert_equal_ignoring_list_order(self, a, b):
        """
        This method will compare items a and b recursively for equality, without taking
        into consideration ther ordering of any lists found inside them. For example, the
        following objects would be considered equal:


            a = {'a_list': ['a', 'b', 'c']}
            b = {'a_list': ['b', 'a', 'c']}

        :param a: An object you wish to compare to b
        :type  a: object
        :param b: An object you wish to compare to a
        :type  b: object
        """
        def _sort_lists(a):
            """
            Traverse the given object, a, and sort all lists and tuples found in the
            structure.

            :param a: A structure to traverse for lists, sorting them
            :type  a: object
            :return:  A representation of a that has all lists sorted
            :rtype:   object
            """
            if isinstance(a, (list, tuple)):
                # We don't want to alter the original a, so make a deepcopy
                a = list(deepcopy(a))
                for index, item in enumerate(a):
                    a[index] = _sort_lists(item)
                a = sorted(a)
            elif isinstance(a, dict):
                for key, value in a.items():
                    a[key] = _sort_lists(value)
            return a
        self.assertEqual(_sort_lists(a), _sort_lists(b))

    def test_assert_equal_ignoring_list_order(self):
        """
        Quick test to make sure our new assertion works. How meta.
        """
        self.assert_equal_ignoring_list_order([1, 2, 3], [2, 1, 3])
        # Test lists embedded in dictionaries
        self.assert_equal_ignoring_list_order({'a_list': [1, 2, 3]}, {'a_list': [2, 1, 3]})
        # Test lists of lists
        self.assert_equal_ignoring_list_order([[1, 2], [3]], [[3], [2, 1]])

        # These should fail
        # The second list has an extra element
        self.assertRaises(AssertionError, self.assert_equal_ignoring_list_order,
                          [1, 2, 3], [2, 1, 3, 3])
        self.assertRaises(AssertionError, self.assert_equal_ignoring_list_order,
                          {'a_list': [1, 2, 3]}, {'a_list': [2, 1]})
        self.assertRaises(AssertionError, self.assert_equal_ignoring_list_order,
                          [[1, 2], [3]], [[3, 3], [2, 1]])


class TaskQueue:

    @classmethod
    def install(cls):
        existing = dispatch_factory._task_queue()
        if existing:
            existing.stop()
        queue = cls()
        dispatch_factory._TASK_QUEUE = queue
        return queue

    @classmethod
    def uninstall(cls):
        pass

    @classmethod
    def run_next(cls):
        queue = dispatch_factory._task_queue()
        if isinstance(queue, cls):
            queue.__run_next()
        else:
            raise Exception, '%s not installed' % cls

    def __init__(self):
        self.__next = 0
        self.__queue = []

    def start(self):
        pass

    def stop(self, *args, **kwargs):
        pass

    def enqueue(self, task):
        self.__queue.append(task)

    def cancel(self, task):
        return task.cancel()

    def __run_next(self):
        if self.__next < len(self.__queue):
            task = self.__queue[self.__next]
            self.__run(task)
            self.__next += 1
        else:
            raise Exception, 'No tasks pending'

    def __run(self, task):
        finished = \
            [t.call_request.id for t in self.__queue[:self.__next]
                if t.call_report.state == dispatch_constants.CALL_FINISHED_STATE]
        for request_id in task.call_request.dependencies.keys():
            if request_id not in finished:
                task.skip()
                return
        task.call_report.state = dispatch_constants.CALL_RUNNING_STATE
        task._run()

    def get(self, task_id):
        for task in self.__queue:
            if task.call_report.call_request_id == task_id:
                return task

    def all_tasks(self):
        return list(self.__queue)

    def lock(self):
        pass

    def unlock(self):
        pass
