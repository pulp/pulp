# -*- coding: utf-8 -*-


import mock

from pulp.common.compat import unittest
from pulp.common import error_codes
from pulp.plugins.distributor import Distributor, GroupDistributor
from pulp.plugins.model import RepositoryGroup
from pulp.server.exceptions import PulpCodedException


class TestDistributorCancel(unittest.TestCase):

    @mock.patch('pulp.plugins.distributor.sys.exit', autospec=True)
    def test_calls_sys_exit(self, mock_sys_exit):
        Distributor().cancel_publish_repo()
        mock_sys_exit.assert_called_once_with()


@mock.patch('pulp.server.controllers.repository.has_all_units_downloaded', return_value=True)
class TestDistributorEnsureUnitsDownloaded(unittest.TestCase):
    def test_files_not_downloaded(self, mock_has_all_units):
        """
        If all files have not been downloaded, make sure exception is raised.
        """
        mock_has_all_units.return_value = False

        with self.assertRaises(PulpCodedException) as assertion:
            Distributor().ensure_all_units_downloaded('repo1')

        self.assertEqual(assertion.exception.error_code, error_codes.PLP0045)

    def test_files_downloaded(self, mock_has_all_units):
        """
        If all files have been downloaded, make sure no exception is raised.
        """
        Distributor().ensure_all_units_downloaded('repo1')

    def test_calls_controller(self, mock_has_all_units):
        """
        Make sure it calls the controller with the right argument.
        """
        Distributor().ensure_all_units_downloaded('repo1')

        mock_has_all_units.assert_called_once_with('repo1')


class TestGroupDistributorCancel(unittest.TestCase):

    @mock.patch('pulp.plugins.distributor.sys.exit', autospec=True)
    def test_calls_sys_exit(self, mock_sys_exit):
        GroupDistributor().cancel_publish_group(mock.Mock(), mock.Mock())
        mock_sys_exit.assert_called_once_with()


@mock.patch('pulp.server.controllers.repository.has_all_units_downloaded', return_value=True)
class TestGroupDistributorEnsureUnitsDownloaded(unittest.TestCase):
    def setUp(self):
        super(TestGroupDistributorEnsureUnitsDownloaded, self).setUp()
        self.distributor = GroupDistributor()
        self.group = RepositoryGroup(id='g1', display_name='g1', description='g1', notes={},
                                     repo_ids=['repo1', 'repo2'])

    def test_all_false(self, mock_has_all_units):
        """
        If all repos are found to have un-downloaded units, make sure the exception is raised.
        """
        mock_has_all_units.return_value = False

        with self.assertRaises(PulpCodedException) as assertion:
            self.distributor.ensure_all_units_downloaded(self.group)

        self.assertEqual(assertion.exception.error_code, error_codes.PLP0046)

    def test_one_false(self, mock_has_all_units):
        """
        If only 1 repo is found to have un-downloaded units, make sure the exception is raised.
        """
        mock_has_all_units.side_effect = [False, True]

        with self.assertRaises(PulpCodedException) as assertion:
            self.distributor.ensure_all_units_downloaded(self.group)

        self.assertEqual(assertion.exception.error_code, error_codes.PLP0046)

    def test_does_not_raise_exception(self, mock_has_all_units):
        """
        If all units are found to be downloaded, make sure an exception is not raised.
        """
        self.distributor.ensure_all_units_downloaded(self.group)

    def test_repo_ids_none(self, mock_has_all_units):
        """
        It seems like repo_ids shouldn't be allowed to be None, but in case it happens, it's easy
        enough to handle.
        """
        self.group.repo_ids = None
        self.distributor.ensure_all_units_downloaded(self.group)

    def test_calls_controller(self, mock_has_all_units):
        """
        Make sure it calls the controller with the right argument.
        """
        self.distributor.ensure_all_units_downloaded(self.group)

        mock_has_all_units.assert_has_call('repo1')
        mock_has_all_units.assert_has_call('repo2')
        self.assertEqual(mock_has_all_units.call_count, 2)
