# -*- coding: utf-8 -*-

import unittest

import mock

from pulp.plugins.distributor import Distributor, GroupDistributor


class TestDistributor(unittest.TestCase):

    @mock.patch('pulp.plugins.distributor.sys.exit', autospec=True)
    def test_cancel_publish_repo_calls_sys_exit(self, mock_sys_exit):
        Distributor().cancel_publish_repo()
        mock_sys_exit.assert_called_once_with()


class TestGroupDistributor(unittest.TestCase):

    @mock.patch('pulp.plugins.distributor.sys.exit', autospec=True)
    def test_cancel_publish_group_calls_sys_exit(self, mock_sys_exit):
        GroupDistributor().cancel_publish_group(mock.Mock(), mock.Mock())
        mock_sys_exit.assert_called_once_with()
