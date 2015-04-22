import errno
import inspect
import os
import unittest

import mock

from pulp.server.managers.content.query import ContentQueryManager


class TestContentQueryManager(unittest.TestCase):

    @mock.patch('pulp.server.managers.content.upload.os.makedirs')
    @mock.patch.object(ContentQueryManager, 'get_root_content_dir')
    def test_request_content_unit_file_path_exists(self, mock_root_dir, mock_makedirs):
        mock_root_dir.return_value = '/var/lib/pulp/content/rpm/'
        mock_makedirs.side_effect = OSError(errno.EEXIST, os.strerror(errno.EEXIST))
        ContentQueryManager().request_content_unit_file_path('rpm', '/name/blah')
        mock_makedirs.assert_called_once_with('/var/lib/pulp/content/rpm/name')

    @mock.patch('pulp.server.managers.content.upload.os.makedirs')
    @mock.patch.object(ContentQueryManager, 'get_root_content_dir')
    def test_request_content_unit_file_path_random_os_error(self, mock_root_dir, mock_makedirs):
        mock_root_dir.return_value = '/var/lib/pulp/content/rpm/'
        mock_makedirs.side_effect = OSError(errno.EACCES, os.strerror(errno.EACCES))
        self.assertRaises(OSError, ContentQueryManager().request_content_unit_file_path, 'rpm', '/name/blah')
        mock_makedirs.assert_called_once_with('/var/lib/pulp/content/rpm/name')
        
    @mock.patch('pulp.server.managers.content.upload.os.makedirs')
    @mock.patch.object(ContentQueryManager, 'get_root_content_dir')
    def test_request_content_unit_file_path_no_error(self, mock_root_dir, mock_makedirs):
        mock_root_dir.return_value = '/var/lib/pulp/content/rpm/'
        mock_makedirs.return_value= '/var/lib/pulp/content/rpm/name'
        ContentQueryManager().request_content_unit_file_path('rpm', '/name/blah')
        mock_makedirs.assert_called_once_with('/var/lib/pulp/content/rpm/name')