from cStringIO import StringIO
import contextlib
import unittest

import mock

from pulp.plugins.util import manifest_writer


@contextlib.contextmanager
def make_fake_file(value):
    yield StringIO(value)


@contextlib.contextmanager
def giveitback(value):
    yield value


class TestGetSHA256Checksum(unittest.TestCase):
    @mock.patch('__builtin__.open', spec_set=True)
    def test_return_value(self, mock_open):
        fake_file = make_fake_file('hi there\n')
        expected_checksum = 'c641344867e9806fadfd219f25b62b97c94db0eed04a1d79e93676533cfb782b'

        mock_open.return_value = fake_file

        ret = manifest_writer.get_sha256_checksum('/foo')

        self.assertEqual(ret, expected_checksum)

    @mock.patch('__builtin__.open', spec_set=True)
    def test_empty_file(self, mock_open):
        fake_file = make_fake_file('')
        expected_checksum = 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'

        mock_open.return_value = fake_file

        ret = manifest_writer.get_sha256_checksum('/foo')

        self.assertEqual(ret, expected_checksum)


class TestMakeManifestForDir(unittest.TestCase):
    @mock.patch('os.listdir', return_value=tuple())
    @mock.patch('__builtin__.open', spec_set=True)
    def test_empty_dir(self, mock_open, mock_listdir):
        fake_file = StringIO()

        mock_open.return_value = giveitback(fake_file)

        manifest_writer.make_manifest_for_dir('/foo/')

        self.assertEqual(fake_file.getvalue(), '')

    @mock.patch('os.path.isfile', return_value=True)
    @mock.patch('os.path.getsize', return_value=17)
    @mock.patch('os.listdir', spec_set=True)
    @mock.patch('__builtin__.open', spec_set=True)
    @mock.patch.object(manifest_writer, 'get_sha256_checksum', spec_set=True)
    def test_value(self, mock_checksum, mock_open, mock_listdir, mock_getsize, mock_isfile):
        mock_listdir.return_value = ['a', 'b']
        mock_checksum.return_value = 'greatchecksum'
        fake_file = StringIO()
        mock_open.return_value = giveitback(fake_file)

        manifest_writer.make_manifest_for_dir(('/foo/'))

        mock_checksum.assert_any_call('/foo/a')
        mock_checksum.assert_any_call('/foo/b')
        self.assertEqual(mock_checksum.call_count, 2)

        expected = 'a,greatchecksum,17\r\nb,greatchecksum,17\r\n'

        self.assertEqual(fake_file.getvalue(), expected)

    @mock.patch('os.path.isfile', side_effect=(False, True))
    @mock.patch('os.path.getsize', return_value=17)
    @mock.patch('os.listdir', spec_set=True)
    @mock.patch('__builtin__.open', spec_set=True)
    @mock.patch.object(manifest_writer, 'get_sha256_checksum', spec_set=True)
    def test_skip_dirs(self, mock_checksum, mock_open, mock_listdir, mock_getsize, mock_isfile):
        mock_listdir.return_value = ['a', 'b']
        mock_checksum.return_value = 'greatchecksum'
        fake_file = StringIO()
        mock_open.return_value = giveitback(fake_file)

        manifest_writer.make_manifest_for_dir('/foo/')

        mock_checksum.assert_called_once_with('/foo/b')

        expected = 'b,greatchecksum,17'

        self.assertEqual(fake_file.getvalue().strip(), expected)
