# -*- coding: utf-8 -*-
# Copyright (c) 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import logging
import os
import unittest

import mock

from pulp.server.upgrade import main
from pulp.server.upgrade.model import UpgradeStepReport


V1_DB_NAME = 'pulp_upgrade_db_v1'
TMP_DB_NAME = 'pulp_upgrade_db_tmp'

LOG_FILENAME = '/tmp/pulp-upgrate-unit-tests.log'
STREAM_FILENAME = '/tmp/pulp-upgrade-stream'


class MainTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super(MainTests, cls).setUpClass()

        logging.getLogger('pulp').addHandler(logging.FileHandler(LOG_FILENAME, mode='w'))

    def setUp(self):
        super(MainTests, self).setUp()

        # Mock out the DB upgrade calls
        self.mock_db_upgrade_call_1 = mock.MagicMock().upgrade
        self.mock_db_upgrade_call_1.return_value = UpgradeStepReport()
        self.mock_db_upgrade_call_1.return_value.succeeded()
        self.mock_db_upgrade_call_1.return_value.message('Upgrading collection 1')
        self.mock_db_upgrade_call_1.return_value.warning('Small problem with collection 3')

        self.mock_db_upgrade_calls = [(self.mock_db_upgrade_call_1, 'Mock 1')]

        # Mock out the filesystem upgrade calls
        self.mock_fs_upgrade_call_1 = mock.MagicMock().upgrade
        self.mock_fs_upgrade_call_1.return_value = UpgradeStepReport()
        self.mock_fs_upgrade_call_1.return_value.succeeded()
        self.mock_fs_upgrade_call_1.return_value.message('Upgrading filesystem')
        self.mock_fs_upgrade_call_1.return_value.warning('File not found')

        self.mock_fs_upgrade_calls = [(self.mock_fs_upgrade_call_1, 'Mock 1')]

        # Assemble the upgrader with the mock calls
        self.upgrader = main.Upgrader(stream_file=STREAM_FILENAME,
                                      prod_db_name=V1_DB_NAME,
                                      tmp_db_name=TMP_DB_NAME,
                                      db_upgrade_calls=self.mock_db_upgrade_calls,
                                      files_upgrade_calls=self.mock_fs_upgrade_calls)

    def tearDown(self):
        super(MainTests, self).tearDown()

        if os.path.exists(STREAM_FILENAME):
            os.remove(STREAM_FILENAME)

    def test_main(self):
        # Test
        self.upgrader.upgrade()

        # Verify
        self.assertTrue(os.path.exists(LOG_FILENAME))

        #   DB Upgrade Calls
        self.assertEqual(1, self.mock_db_upgrade_call_1.call_count)
        call_args = self.mock_db_upgrade_call_1.call_args[0]
        self.assertEqual(call_args[0].name, V1_DB_NAME)
        self.assertEqual(call_args[1].name, TMP_DB_NAME)

        #   Filesystem Upgrade Calls
        self.assertEqual(1, self.mock_fs_upgrade_call_1.call_count)
        call_args = self.mock_fs_upgrade_call_1.call_args[0]
        self.assertEqual(call_args[0].name, V1_DB_NAME)
        self.assertEqual(call_args[1].name, TMP_DB_NAME)

        #   Assert the new production database remained
        connection = self.upgrader._connection()
        self.assertTrue(V1_DB_NAME in connection.database_names())

        #   Assert the temporary was cleaned up
        self.assertTrue(not TMP_DB_NAME in connection.database_names())

        self.assertTrue(os.path.exists(STREAM_FILENAME))

    def test_main_with_error(self):
        # Setup
        self.mock_db_upgrade_call_1.return_value.failed()

        # Test
        try:
            self.upgrader.upgrade()
            self.fail()
        except main.StepException, e:
            self.assertEqual('Mock 1', e[0])

        # Verify
        self.assertEqual(1, self.mock_db_upgrade_call_1.call_count)

    def test_main_with_partial_error(self):
        # Setup
        m = mock.MagicMock()
        m.call_1.return_value = UpgradeStepReport()
        m.call_1.return_value.succeeded()
        m.call_2.return_value = UpgradeStepReport()
        m.call_2.return_value.failed()
        m.call_3.return_value = UpgradeStepReport()
        m.call_3.return_value.succeeded()

        self.upgrader.db_upgrade_calls = (
            (m.call_1, 'Mock 1'),
            (m.call_2, 'Mock 2'),
            (m.call_3, 'Mock 3'),
        )

        # Test
        try:
            self.upgrader.upgrade()
            self.fail()
        except main.StepException, e:
            self.assertEqual('Mock 2', e[0])

        # Verify
        self.assertEqual(1, m.call_1.call_count)
        self.assertEqual(1, m.call_2.call_count)
        self.assertEqual(0, m.call_3.call_count)

    def test_already_upgraded(self):
        # Setup
        f = open(STREAM_FILENAME, 'w')
        f.write('2')
        f.close()
        self.upgrader.stream_file = STREAM_FILENAME

        # Test
        self.upgrader.upgrade()

        # Verify
        self.assertEqual(0, self.mock_db_upgrade_call_1.call_count)

    @mock.patch('pulp.server.upgrade.main.Upgrader._upgrade_database')
    @mock.patch('pulp.server.upgrade.main.Upgrader._upgrade_files')
    def test_no_db_upgrade(self, mock_files_call, mock_db_call):
        # Setup
        self.upgrader = main.Upgrader(stream_file=STREAM_FILENAME,
                                      prod_db_name=V1_DB_NAME,
                                      tmp_db_name=TMP_DB_NAME,
                                      db_upgrade_calls=self.mock_db_upgrade_calls,
                                      upgrade_db=False)

        # Test
        self.upgrader.upgrade()

        # Verify
        self.assertEqual(1, mock_files_call.call_count)
        self.assertEqual(0, mock_db_call.call_count)

    @mock.patch('pulp.server.upgrade.main.Upgrader._upgrade_database')
    @mock.patch('pulp.server.upgrade.main.Upgrader._upgrade_files')
    def test_no_files_upgrade(self, mock_files_call, mock_db_call):
        # Setup
        self.upgrader = main.Upgrader(stream_file=STREAM_FILENAME,
                                      prod_db_name=V1_DB_NAME,
                                      tmp_db_name=TMP_DB_NAME,
                                      db_upgrade_calls=self.mock_db_upgrade_calls,
                                      upgrade_files=False)

        # Test
        self.upgrader.upgrade()

        # Verify
        self.assertEqual(0, mock_files_call.call_count)
        self.assertEqual(1, mock_db_call.call_count)
