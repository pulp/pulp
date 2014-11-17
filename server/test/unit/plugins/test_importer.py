# -*- coding: utf-8 -*-

import unittest

import mock

from pulp.plugins.importer import Importer


class TestImporter(unittest.TestCase):

    @mock.patch('pulp.plugins.importer.sys.exit', autospec=True)
    def test_cancel_sync_repo_calls_sys_exit(self, mock_sys_exit):
        Importer().cancel_sync_repo()
        mock_sys_exit.assert_called_once_with()
