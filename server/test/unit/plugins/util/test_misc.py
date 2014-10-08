import inspect
import os
import unittest

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


class TestGetParentDirectory(unittest.TestCase):

    def test_relative_path_ends_in_slash(self):
        path = 'a/relative/path/'
        parent_dir = 'a/relative'
        result = misc.get_parent_directory(path)
        self.assertEqual(result, parent_dir)

    def test_relative_path_does_not_end_in_slash(self):
        path = 'a/relative/path'
        parent_dir = 'a/relative'
        result = misc.get_parent_directory(path)
        self.assertEqual(result, parent_dir)

    def test_absolute_path_ends_in_slash(self):
        path = '/an/absolute/path/'
        parent_dir = '/an/absolute'
        result = misc.get_parent_directory(path)
        self.assertEqual(result, parent_dir)

    def test_absolute_path_does_not_end_in_slash(self):
        path = '/an/absolute/path'
        parent_dir = '/an/absolute'
        result = misc.get_parent_directory(path)
        self.assertEqual(result, parent_dir)
