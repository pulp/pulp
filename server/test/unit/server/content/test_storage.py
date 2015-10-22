import os

from errno import EEXIST, EPERM
from unittest import TestCase
from subprocess import PIPE

from mock import Mock, patch

from pulp.server.content.storage import mkdir, cpdir, ContentStorage, FileStorage, SharedStorage


class TestMkdir(TestCase):

    @patch('os.makedirs')
    def test_succeeded(self, _mkdir):
        path = 'path-123'
        mkdir(path)
        _mkdir.assert_called_once_with(path)

    @patch('os.makedirs')
    def test_already_exists(self, _mkdir):
        path = 'path-123'
        mkdir(path)
        _mkdir.assert_called_once_with(path)
        _mkdir.side_effect = OSError(EEXIST, path)

    @patch('os.makedirs')
    def test_other_exception(self, _mkdir):
        path = 'path-123'
        mkdir(path)
        _mkdir.side_effect = OSError(EPERM, path)
        self.assertRaises(OSError, mkdir, path)


class TestCpDir(TestCase):

    @patch('os.environ')
    @patch('os.listdir')
    @patch('pulp.server.content.storage.Popen')
    def test_succeeded(self, popen, listdir, environ):
        popen.return_value.wait.return_value = os.EX_OK
        listdir.return_value = ['dpgs', 'cats']
        environ.copy.return_value = {'A': 1}
        source = '/tmp/source'
        destination = '/tmp/destination'

        # test
        cpdir(source, destination)

        # validation
        listdir.assert_called_once_with(source)
        content = [os.path.join(source, f) for f in listdir.return_value]
        popen.assert_called_once_with(
            [
                'cp',
                '-r',
            ] + content + [destination],
            stderr=PIPE,
            env=environ.copy.return_value)

    @patch('os.environ')
    @patch('os.listdir')
    @patch('pulp.server.content.storage.Popen')
    def test_failed(self, popen, listdir, environ):
        popen.return_value.wait.return_value = -1
        listdir.return_value = ['dpgs', 'cats']
        environ.copy.return_value = {'A': 1}
        source = '/tmp/source'
        destination = '/tmp/destination'

        # test
        self.assertRaises(OSError, cpdir, source, destination)

    @patch('os.listdir')
    @patch('pulp.server.content.storage.Popen')
    def test_empty(self, popen, listdir):
        listdir.return_value = []
        source = '/tmp/source'
        destination = '/tmp/destination'
        cpdir(source, destination)
        self.assertFalse(popen.called)


class TestContentStorage(TestCase):

    def test_abstract(self):
        storage = ContentStorage()
        self.assertRaises(NotImplementedError, storage.put, None, None)
        self.assertRaises(NotImplementedError, storage.get, None)

    def test_open(self):
        storage = ContentStorage()
        storage.open()

    def test_close(self):
        storage = ContentStorage()
        storage.close()

    def test_enter(self):
        storage = ContentStorage()
        storage.open = Mock()
        inst = storage.__enter__()
        storage.open.assert_called_once_with()
        self.assertEqual(inst, storage)

    def test_exit(self):
        storage = ContentStorage()
        storage.close = Mock()
        storage.__exit__()
        storage.close.assert_called_once_with()


class TestFileStorage(TestCase):

    @patch('pulp.server.content.storage.cpdir')
    @patch('pulp.server.content.storage.config')
    @patch('os.path.isdir', Mock(return_value=True))
    def test_put_dir(self, config, cpdir):
        path_in = '/tmp/test/'
        storage_dir = '/tmp/storage'
        unit = Mock(id='0123456789', unit_type_id='ABC')
        config.get = lambda s, p: {'server': {'storage_dir': storage_dir}}[s][p]
        storage = FileStorage()

        # test
        storage.put(unit, path_in)

        # validation
        destination = os.path.join(
            os.path.join(storage_dir, 'content', 'units', unit.unit_type_id),
            unit.id[0:4], unit.id)
        cpdir.assert_called_once_with(path_in, destination)
        self.assertEqual(unit.storage_path, destination)

    @patch('pulp.server.content.storage.shutil')
    @patch('pulp.server.content.storage.config')
    @patch('os.path.isdir', Mock(return_value=False))
    def test_put_file(self, config, shutil):
        path_in = '/tmp/test'
        storage_dir = '/tmp/storage'
        unit = Mock(id='0123456789', unit_type_id='ABC')
        config.get = lambda s, p: {'server': {'storage_dir': storage_dir}}[s][p]
        storage = FileStorage()

        # test
        storage.put(unit, path_in)

        # validation
        destination = os.path.join(
            os.path.join(storage_dir, 'content', 'units', unit.unit_type_id),
            unit.id[0:4], unit.id)
        shutil.copy.assert_called_once_with(path_in, destination)
        self.assertEqual(unit.storage_path, destination)

    def test_get(self):
        storage = FileStorage()
        storage.get(None)  # just for coverage


class TestSharedStorage(TestCase):

    @patch('pulp.server.content.storage.sha256')
    def test_init(self, sha256):
        provider = 'git'
        storage_id = '1234'
        storage = SharedStorage(provider, storage_id)
        sha256.assert_called_once_with(storage_id)
        self.assertEqual(storage.storage_id, sha256.return_value.hexdigest.return_value)
        self.assertEqual(storage.provider, provider)

    @patch('pulp.server.content.storage.mkdir')
    @patch('pulp.server.content.storage.SharedStorage.content_dir', 'abcd/')
    @patch('pulp.server.content.storage.SharedStorage.links_dir', 'xyz/')
    def test_open(self, _mkdir):
        storage = SharedStorage('git', '1234')
        storage.open()
        self.assertEqual(
            _mkdir.call_args_list,
            [
                ((storage.content_dir,), {}),
                ((storage.links_dir,), {}),
            ])

    @patch('pulp.server.content.storage.config')
    def test_shared_dir(self, config):
        storage_dir = '/tmp/storage'
        config.get = lambda s, p: {'server': {'storage_dir': storage_dir}}[s][p]
        storage = SharedStorage('git', '1234')
        self.assertEqual(
            storage.shared_dir,
            os.path.join(storage_dir, 'content', 'shared', storage.provider, storage.storage_id))

    @patch('pulp.server.content.storage.SharedStorage.shared_dir', 'abcd/')
    def test_content_dir(self):
        storage = SharedStorage('git', '1234')
        self.assertEqual(
            storage.content_dir,
            os.path.join(storage.shared_dir, 'content'))

    @patch('pulp.server.content.storage.SharedStorage.shared_dir', 'abcd/')
    def test_links_dir(self):
        storage = SharedStorage('git', '1234')
        self.assertEqual(
            storage.links_dir,
            os.path.join(storage.shared_dir, 'links'))

    def test_put(self):
        unit = Mock()
        storage = SharedStorage('git', '1234')
        storage.link = Mock()
        storage.put(unit)
        storage.link.assert_called_once_with(unit)

    def test_get(self):
        storage = SharedStorage('git', '1234')
        storage.get(None)  # just for coverage

    @patch('os.symlink')
    @patch('pulp.server.content.storage.SharedStorage.content_dir', 'abcd/')
    @patch('pulp.server.content.storage.SharedStorage.links_dir', 'xyz/')
    def test_link(self, symlink):
        unit = Mock(id='0123456789')
        storage = SharedStorage('git', '1234')

        # test
        storage.link(unit)

        # validation
        expected_path = os.path.join(storage.links_dir, unit.id)
        symlink.assert_called_once_with(storage.content_dir, expected_path)
        self.assertEqual(unit.storage_path, expected_path)

    @patch('os.symlink')
    @patch('os.readlink')
    @patch('os.path.islink')
    @patch('pulp.server.content.storage.SharedStorage.content_dir', 'abcd/')
    @patch('pulp.server.content.storage.SharedStorage.links_dir', 'xyz/')
    def test_duplicate_link(self, islink, readlink, symlink):
        unit = Mock(id='0123456789')
        storage = SharedStorage('git', '1234')

        islink.return_value = True
        symlink.side_effect = OSError()
        symlink.side_effect.errno = EEXIST
        readlink.return_value = storage.content_dir

        # test
        storage.link(unit)
        # note: not exception raised

        # validation
        expected_path = os.path.join(storage.links_dir, unit.id)
        symlink.assert_called_once_with(storage.content_dir, expected_path)
        self.assertEqual(unit.storage_path, expected_path)

    @patch('os.symlink')
    @patch('os.readlink')
    @patch('os.path.islink')
    @patch('pulp.server.content.storage.SharedStorage.content_dir', 'abcd/')
    @patch('pulp.server.content.storage.SharedStorage.links_dir', 'xyz/')
    def test_duplicate_nonlink(self, islink, readlink, symlink):
        unit = Mock(id='0123456789')
        storage = SharedStorage('git', '1234')

        islink.return_value = False  # not a link
        symlink.side_effect = OSError()
        symlink.side_effect.errno = EEXIST
        readlink.return_value = storage.content_dir

        # test
        self.assertRaises(OSError, storage.link, unit)

        # validation
        expected_path = os.path.join(storage.links_dir, unit.id)
        symlink.assert_called_once_with(storage.content_dir, expected_path)

    @patch('os.symlink')
    @patch('os.readlink')
    @patch('os.path.islink')
    @patch('pulp.server.content.storage.SharedStorage.content_dir', 'abcd/')
    @patch('pulp.server.content.storage.SharedStorage.links_dir', 'xyz/')
    def test_different_link_target(self, islink, readlink, symlink):
        unit = Mock(id='0123456789')
        storage = SharedStorage('git', '1234')

        islink.return_value = True
        symlink.side_effect = OSError()
        symlink.side_effect.errno = EEXIST
        readlink.return_value = 'different link target'

        # test
        self.assertRaises(OSError, storage.link, unit)

        # validation
        expected_path = os.path.join(storage.links_dir, unit.id)
        symlink.assert_called_once_with(storage.content_dir, expected_path)

    @patch('os.symlink')
    @patch('pulp.server.content.storage.SharedStorage.content_dir', 'abcd/')
    @patch('pulp.server.content.storage.SharedStorage.links_dir', 'xyz/')
    def test_link_failed(self, symlink):
        unit = Mock(id='0123456789')
        storage = SharedStorage('git', '1234')
        symlink.side_effect = OSError()
        symlink.side_effect.errno = EPERM
        self.assertRaises(OSError, storage.link, unit)
