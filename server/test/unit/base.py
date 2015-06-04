from copy import deepcopy
import os
try:
    import unittest2 as unittest
except ImportError:
    import unittest

import mock

from pulp.server import config
from pulp.server.async import celery_instance
from pulp.server.db import connection
from pulp.server.db.model import TaskStatus, ReservedResource, Worker
from pulp.server.logs import start_logging, stop_logging
from pulp.server.managers import factory as manager_factory
from pulp.server.managers.auth.cert.cert_generator import SerialNumber


SerialNumber.PATH = '/tmp/sn.dat'

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/'))


def load_test_config():
    if not os.path.exists('/tmp/pulp'):
        os.makedirs('/tmp/pulp')

    override_file = os.path.join(DATA_DIR, 'test-override-pulp.conf')
    stop_logging()
    try:
        config.add_config_file(override_file)
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
        self.config = PulpServerTests.CONFIG  # shadow for simplicity
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


class ResourceReservationTests(PulpServerTests):
    def tearDown(self):
        Worker.objects().delete()
        ReservedResource.objects.delete()
        TaskStatus.objects().delete()
