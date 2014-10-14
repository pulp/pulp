import errno
import inspect
import os
import unittest
import shutil
import tempfile

from mock import patch
from pulp.devel.unit.util import touch

from pulp.plugins.util import misc


class TestPaginate(unittest.TestCase):

    def test_list(self):
        iterable = list(range(10))
        ret = misc.paginate(iterable, 3)

        self.assertTrue(inspect.isgenerator(ret))

        pieces = list(ret)

        self.assertEqual(pieces, [(0, 1, 2), (3, 4, 5), (6, 7, 8), (9,)])

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

        self.assertEqual(pieces, [(0, 1, 2), (3, 4, 5), (6, 7, 8), (9,)])

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

        self.assertEqual(pieces, [(0, 1, 2), (3, 4, 5), (6, 7, 8), (9,)])

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


class TestClearDirectory(unittest.TestCase):

    def setUp(self):
        self.working_dir = tempfile.mkdtemp(prefix='working_')

    def tearDown(self):
        shutil.rmtree(self.working_dir)

    def test_clear_directory(self):

        for file_name in ('one', 'two', 'three'):
            touch(os.path.join(self.working_dir, file_name))

        os.makedirs(os.path.join(self.working_dir, 'four'))
        self.assertEqual(len(os.listdir(self.working_dir)), 4)

        misc.clear_directory(self.working_dir, ['two'])

        self.assertEqual(len(os.listdir(self.working_dir)), 1)

    def test_clear_directory_that_does_not_exist(self):
        # If this doesn't throw we are ok
        misc.clear_directory(os.path.join(self.working_dir, 'imaginary'))


class TestCreateSymlink(unittest.TestCase):

    def setUp(self):
        self.working_dir = tempfile.mkdtemp(prefix='working_')
        self.published_dir = tempfile.mkdtemp(prefix='published_')

    def tearDown(self):
        shutil.rmtree(self.working_dir)
        shutil.rmtree(self.published_dir)

    def test_create_symlink(self):
        source_path = os.path.join(self.working_dir, 'source')
        link_path = os.path.join(self.published_dir, 'link')

        touch(source_path)
        self.assertFalse(os.path.exists(link_path))

        misc.create_symlink(source_path, link_path)

    def test_create_symlink_no_source(self):
        source_path = os.path.join(self.working_dir, 'source')
        link_path = os.path.join(self.published_dir, 'link')

        self.assertRaises(RuntimeError, misc.create_symlink, source_path, link_path)

    @patch('pulp.plugins.util.misc.os.symlink')
    @patch('pulp.plugins.util.misc.os.makedirs')
    def test_create_symlink_no_link_parent(self, mock_makedirs, mock_symlink):
        source_path = os.path.join(self.working_dir, 'source')
        link_path = os.path.join(self.published_dir, 'foo/bar/baz/link')

        touch(source_path)
        self.assertFalse(os.path.exists(os.path.dirname(link_path)))

        misc.create_symlink(source_path, link_path)

        mock_makedirs.assert_called_once_with(os.path.dirname(link_path), mode=0770)
        mock_symlink.assert_called_once_with(source_path, link_path)

    @patch('pulp.plugins.util.misc.os.symlink')
    @patch('pulp.plugins.util.misc.os.makedirs')
    def test_create_symlink_no_link_parent_with_permissions(self, mock_makedirs, mock_symlink):
        source_path = os.path.join(self.working_dir, 'source')
        link_path = os.path.join(self.published_dir, 'foo/bar/baz/link')

        touch(source_path)
        self.assertFalse(os.path.exists(os.path.dirname(link_path)))

        misc.create_symlink(source_path, link_path, directory_permissions=0700)

        mock_makedirs.assert_called_once_with(os.path.dirname(link_path), mode=0700)
        mock_symlink.assert_called_once_with(source_path, link_path)

    def test_create_symlink_link_parent_bad_permissions(self):
        source_path = os.path.join(self.working_dir, 'source')
        link_path = os.path.join(self.published_dir, 'foo/bar/baz/link')

        touch(source_path)
        os.makedirs(os.path.dirname(link_path))
        os.chmod(os.path.dirname(link_path), 0000)

        self.assertRaises(OSError, misc.create_symlink, source_path, link_path)

        os.chmod(os.path.dirname(link_path), 0777)

    def test_create_symlink_link_exists(self):
        old_source_path = os.path.join(self.working_dir, 'old_source')
        new_source_path = os.path.join(self.working_dir, 'new_source')
        link_path = os.path.join(self.published_dir, 'link')

        touch(old_source_path)
        touch(new_source_path)

        os.symlink(old_source_path, link_path)

        self.assertEqual(os.readlink(link_path), old_source_path)

        link_path_with_slash = link_path + '/'

        misc.create_symlink(new_source_path, link_path_with_slash)

        self.assertEqual(os.readlink(link_path), new_source_path)

    def test_create_symlink_link_exists_and_is_correct(self):
        new_source_path = os.path.join(self.working_dir, 'new_source')
        link_path = os.path.join(self.published_dir, 'link')

        touch(new_source_path)

        os.symlink(new_source_path, link_path)

        self.assertEqual(os.readlink(link_path), new_source_path)

        misc.create_symlink(new_source_path, link_path)

        self.assertEqual(os.readlink(link_path), new_source_path)

    def test_create_symlink_link_exists_not_link(self):
        source_path = os.path.join(self.working_dir, 'source')
        link_path = os.path.join(self.published_dir, 'link')

        touch(source_path)
        touch(link_path)

        self.assertRaises(RuntimeError, misc.create_symlink, source_path, link_path)
