import inspect
import unittest
import errno

from mock import patch

from pulp.plugins.util import misc


class TestPaginate(unittest.TestCase):
    def test_list(self):
        iterable = list(range(10))
        ret = misc.paginate(iterable, 3)

        self.assertTrue(inspect.isgenerator(ret))

        pieces = list(ret)

        self.assertEqual(pieces, [(0,1,2), (3,4,5), (6,7,8), (9,)])

    def test_list_one_page(self):
        iterable = list(range(10))
        ret = misc.paginate(iterable, 100)

        self.assertTrue(inspect.isgenerator(ret))

        pieces = list(ret)

        self.assertEqual(pieces, [tuple(range(10))])

    def test_empty_list(self):
        ret = misc.paginate([], 3)

        self.assertTrue(inspect.isgenerator(ret))

        pieces = list(ret)

        self.assertEqual(pieces, [])

    def test_tuple(self):
        iterable = tuple(range(10))
        ret = misc.paginate(iterable, 3)

        self.assertTrue(inspect.isgenerator(ret))

        pieces = list(ret)

        self.assertEqual(pieces, [(0,1,2), (3,4,5), (6,7,8), (9,)])

    def test_tuple_one_page(self):
        iterable = tuple(range(10))
        ret = misc.paginate(iterable, 100)

        self.assertTrue(inspect.isgenerator(ret))

        pieces = list(ret)

        self.assertEqual(pieces, [tuple(range(10))])

    def test_generator(self):
        iterable = (x for x in range(10))
        ret = misc.paginate(iterable, 3)

        self.assertTrue(inspect.isgenerator(ret))

        pieces = list(ret)

        self.assertEqual(pieces, [(0,1,2), (3,4,5), (6,7,8), (9,)])

    def test_generator_one_page(self):
        iterable = (x for x in range(10))
        ret = misc.paginate(iterable, 100)

        self.assertTrue(inspect.isgenerator(ret))

        pieces = list(ret)

        self.assertEqual(pieces, [tuple(range(10))])


class TestMkdir(unittest.TestCase):

    @patch('os.makedirs')
    def test_succeeded(self, fake_mkdir):
        path = 'path-123'
        misc.mkdir(path)
        fake_mkdir.assert_called_once_with(path)

    @patch('os.makedirs')
    def test_already_exists(self, fake_mkdir):
        path = 'path-123'
        misc.mkdir(path)
        fake_mkdir.assert_called_once_with(path)
        fake_mkdir.side_effect = OSError(errno.EEXIST, path)

    @patch('os.makedirs')
    def test_other_exception(self, fake_mkdir):
        path = 'path-123'
        misc.mkdir(path)
        fake_mkdir.side_effect = OSError(errno.EPERM, path)
        self.assertRaises(OSError, misc.mkdir, path)
