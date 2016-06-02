from cStringIO import StringIO
import hashlib
import shutil

from mock import Mock, patch, call

from pulp.common.compat import unittest
from pulp.server import util
from pulp.server.exceptions import PulpCodedException


class TestCopyTree(unittest.TestCase):

    @patch('pulp.server.util.copy')
    @patch('pulp.server.util.os.path.isdir')
    @patch('pulp.server.util.os.path.islink')
    @patch('pulp.server.util.os.makedirs')
    @patch('pulp.server.util.os.listdir')
    def test_recursion(self, mock_list_dir, mock_makedirs, mock_islink, mock_isdir, mock_copy):
        """
        Check that copytree is called recursively on all directories within a tree

        The mock 'src' directory has following structure:
            - src
               - dir1
                  - file1
               - dir2
                  - file2
               - file3
        """
        mock_list_dir.side_effect = [['dir1', 'dir2', 'file3'], ['file1'], ['file2']]
        mock_isdir.side_effect = [True, False, True, False, False]
        util.copytree('src', 'dst')
        mock_list_dir.assert_has_calls([call('src'), call('src/dir1'), call('src/dir2')])
        mock_isdir.assert_has_calls([call('src/dir1'), call('src/dir1/file1'), call('src/dir2'),
                                     call('src/dir2/file2'), call('src/file3')])
        # Assert files are copied using copy()
        mock_copy.assert_has_calls([call('src/dir1/file1', 'dst/dir1/file1'),
                                    call('src/dir2/file2', 'dst/dir2/file2'),
                                    call('src/file3', 'dst/file3')])
        # Assert that directories are created using makedirs()
        mock_makedirs.assert_has_calls([call('dst'), call('dst/dir1'), call('dst/dir2')])

    @patch('shutil.copystat', autospec=True)
    @patch('shutil.copy2', autospec=True)
    @patch('pulp.server.util.copy')
    @patch('pulp.server.util.os.path.isdir')
    @patch('pulp.server.util.os.path.islink')
    @patch('pulp.server.util.os.makedirs')
    @patch('pulp.server.util.os.listdir')
    def test_copy2_copystat_not_used(self, mock_list_dir, mock_makedirs, mock_islink, mock_isdir,
                                     mock_copy, mock_copy2, mock_copystat):
        """
        Test that only copy is used and copy2 and copystat are never called

        The mock 'src' directory has following structure:
            - src
               - file
        """
        mock_list_dir.side_effect = [['file'], []]
        mock_isdir.side_effect = [False]
        util.copytree('src', 'dst')
        mock_copy.assert_called_with('src/file', 'dst/file')
        self.assertFalse(mock_copy2.called)
        self.assertFalse(mock_copystat.called)

    @patch('pulp.server.util.os.makedirs')
    @patch('pulp.server.util.copy', autospec=True)
    @patch('pulp.server.util.os.path.isdir')
    @patch('pulp.server.util.os.listdir')
    def test_error_limit(self, mock_list_dir, mock_isdir, mock_copy, mock_makedirs):
        """
        Make sure it doesn't collect an unbounded number of errors. 100 is the defined limit
        after which it gives up.

        https://pulp.plan.io/issues/1808
        """
        mock_list_dir.return_value = (str(x) for x in range(110))
        mock_isdir.return_value = False
        mock_copy.side_effect = OSError('oops')

        with self.assertRaises(shutil.Error) as assertion:
            util.copytree('src', 'dst')

        errors = assertion.exception.args[0]
        # there should be 100 errors exactly, because that is the limit
        self.assertEqual(len(errors), 100)
        # ensure each error has the correct data
        for i, error in enumerate(errors):
            src, dst, why = error
            self.assertEqual('src/%d' % i, src)
            self.assertEqual('dst/%d' % i, dst)
            self.assertEqual('oops', why)
        # make sure there are 10 more in the iterator, thus those copy operations were definitely
        # not attempted.
        self.assertEqual(len(list(mock_list_dir.return_value)), 10)

    @patch('pulp.server.util.copy', autospec=True)
    @patch('pulp.server.util.os.path.isdir')
    @patch('pulp.server.util.os.path.islink')
    @patch('pulp.server.util.os.makedirs')
    @patch('pulp.server.util.os.listdir')
    def test_ignore(self, mock_list_dir, mock_makedirs, mock_islink, mock_isdir, mock_copy):
        """
        Test that passing an ignore callable causes files to be ignored

        The mock 'src' directory has following structure:
            - src
               - dir1
                  - file1
               - dir2
                  - file2
               - file3
        """
        mock_list_dir.side_effect = [['dir1', 'dir2', 'file3'], ['file2']]
        mock_isdir.side_effect = [True, True]
        mock_ignore = Mock()

        # Ignore dir1 and file3
        mock_ignore.side_effect = [['dir1', 'file3'], ['file2'], []]
        util.copytree('src', 'dst', ignore=mock_ignore)

        # Assert only 'src' and 'src/dir2' directories are visited
        mock_list_dir.assert_has_calls([call('src'), call('src/dir2')])

        # Assert only the not ignored files are checked with os.path.isdir()
        mock_isdir.assert_has_calls([call('src/dir2')])

        # Assert files are copied using copy()
        self.assertFalse(mock_copy.called)

        # Assert that only dst and dir2 directories are created using makedirs()
        mock_makedirs.assert_has_calls([call('dst'), call('dst/dir2')])

    @patch('pulp.server.util.os.readlink')
    @patch('pulp.server.util.os.symlink')
    @patch('pulp.server.util.copy')
    @patch('pulp.server.util.os.path.isdir')
    @patch('pulp.server.util.os.path.islink')
    @patch('pulp.server.util.os.makedirs')
    @patch('pulp.server.util.os.listdir')
    def test_symlinks(self, mock_list_dir, mock_makedirs, mock_islink, mock_isdir, mock_copy,
                      mock_symlink, mock_readlink):
        """
        Test that symlinks are created as symlinks

        The mock 'src' directory has following structure:
            - src
               - dir1
                  - file1 <symlink to file3>
               - dir2
                  - file2
               - file3
        """
        mock_list_dir.side_effect = [['dir1', 'dir2', 'file3'], ['file1'], ['file2']]
        mock_isdir.side_effect = [True, True, False, False]
        mock_islink.side_effect = [False, True, False, False, False]
        mock_readlink.side_effect = ['src/file3']
        util.copytree('src', 'dst', symlinks=True)

        # Assert that 'src/dir1/file1' is treated as symlink
        mock_readlink.assert_has_calls([call('src/dir1/file1')])
        mock_symlink.assert_has_calls([call('src/file3', 'dst/dir1/file1')])

        # Assert that all directories are visited
        mock_list_dir.assert_has_calls([call('src'), call('src/dir1'), call('src/dir2')])

        # Assert everything except for symlink is checked if it is a directory
        mock_isdir.assert_has_calls([call('src/dir1'), call('src/dir2'), call('src/dir2/file2'),
                                     call('src/file3')])


class TestPackageListenerDeleting(unittest.TestCase):
    @patch('os.remove')
    def test_removes_path(self, mock_remove):
        path = '/a/b/c'

        with util.deleting(path):
            pass

        mock_remove.assert_called_once_with(path)

    @patch('os.remove', side_effect=IOError)
    def test_squashes_exception(self, mock_remove):
        path = '/a/b/c'

        # this should not raise any exceptions
        with util.deleting(path):
            pass

        mock_remove.assert_called_once_with(path)


class TestSanitizeChecksumType(unittest.TestCase):
    """
    This class contains tests for the sanitize_checksum_type() function.
    """

    def test_sha_to_sha1(self):
        """
        Assert that "sha" is converted to "sha1".
        """
        checksum_type = util.sanitize_checksum_type('sha')

        self.assertEqual(checksum_type, 'sha1')

    def test_ShA_to_sha1(self):
        """
        Assert that "ShA" is converted to "sha1".
        """
        checksum_type = util.sanitize_checksum_type('ShA')

        self.assertEqual(checksum_type, 'sha1')

    def test_SHA256_to_sha256(self):
        """
        Assert that "SHA256" is converted to "sha256".
        """
        checksum_type = util.sanitize_checksum_type('SHA256')

        self.assertEqual(checksum_type, 'sha256')

    def test_invalid_type_raises_coded_exception(self):
        self.assertRaises(PulpCodedException,
                          util.sanitize_checksum_type, 'not_a_real_checksum')


class TestGlobal(unittest.TestCase):
    def test_checksum_algorithm_mappings(self):
        self.assertEqual(4, len(util.CHECKSUM_FUNCTIONS))
        self.assertEqual(util.CHECKSUM_FUNCTIONS[util.TYPE_MD5], hashlib.md5)
        self.assertEqual(util.CHECKSUM_FUNCTIONS[util.TYPE_SHA1], hashlib.sha1)
        self.assertEqual(util.CHECKSUM_FUNCTIONS[util.TYPE_SHA], hashlib.sha1)
        self.assertEqual(util.CHECKSUM_FUNCTIONS[util.TYPE_SHA256], hashlib.sha256)


class TestCalculateChecksums(unittest.TestCase):
    def setUp(self):
        super(TestCalculateChecksums, self).setUp()
        self.f = StringIO('sometext')
        self.sha1_sum = 'd22a158c8ead99dbd7eddb86104496f3ee087049'
        self.sha256_sum = '5fb2054478353fd8d514056d1745b3a9eef066deadda4b90967af7ca65ce6505'

    def test_invalid_type(self):
        self.assertRaises(util.InvalidChecksumType, util.calculate_checksums, self.f, ['sha0'])

    def test_with_data(self):
        ret = util.calculate_checksums(self.f, ['sha1', 'sha256'])

        self.assertEqual(ret['sha1'], self.sha1_sum)
        self.assertEqual(ret['sha256'], self.sha256_sum)

    def test_one(self):
        ret = util.calculate_checksums(self.f, ['sha256'])

        self.assertEqual(ret['sha256'], self.sha256_sum)
        self.assertTrue(len(ret), 1)
