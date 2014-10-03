#!/usr/bin/python
#
# Copyright (c) 2011 Red Hat, Inc.
#
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from ... import base
import unittest

from mock import patch

from pulp.server import config
from pulp.server.db import connection


class TestDatabase(base.PulpServerTests):

    def test_database_name(self):
        self.assertEquals(connection._DATABASE.name, self.config.get("database", "name"))


class TestDatabaseVersion(base.PulpServerTests):

    """
    test DB version parsing. Info on expected versions is at
    https://github.com/mongodb/mongo/blob/master/src/mongo/util/version.cpp#L39-45
    """
    @patch("pymongo.MongoClient")
    @patch("pulp.server.db.connection._end_request_decorator")
    def _test_initialize(self, version_str, mock_end, mock_mongoclient):
        mock_mongoclient_instance = mock_mongoclient.return_value
        mock_mongoclient_instance.server_info.return_value = {"version": version_str}
        connection.initialize()

    def test_database_version_bad_version(self):
        try:
            self._test_initialize('1.2.3')
            self.fail("RuntimeError not raised")
        except RuntimeError:
            pass  # expected exception

    def test_database_version_good_version(self):
        # the version check succeeded if no exception was raised
        self._test_initialize('2.6.0')

    def test_database_version_good_equal_version(self):
        # the version check succeeded if no exception was raised
        self._test_initialize('2.4.0')

    def test_database_version_good_rc_version(self):
        # the version check succeeded if no exception was raised
        self._test_initialize('2.8.0-rc1')

    def test_database_version_bad_rc_version(self):
        try:
            self._test_initialize('2.3.0-rc1')
            self.fail("RuntimeError not raised")
        except RuntimeError:
            pass  # expected exception


class TestDatabaseAuthentication(base.PulpServerTests):

    def tearDown(self):
        # Reload the configuration so that things are cleaned up properly
        config.load_configuration()
        super(TestDatabaseAuthentication, self).tearDown()

    @patch("pymongo.MongoClient")
    @patch("pulp.server.db.connection._end_request_decorator")
    def test_initialize_username_and_password(self, mock_end, mock_mongoclient):
        mock_mongoclient_instance = mock_mongoclient.return_value
        mock_mongoclient_instance.server_info.return_value = {"version":
                                                              connection.MONGO_MINIMUM_VERSION}
        config.config.set('database', 'username', 'admin')
        config.config.set('database', 'password', 'admin')
        connection.initialize()
        self.assertTrue(connection._DATABASE.authenticate.called)

    @patch("pymongo.MongoClient")
    @patch("pulp.server.db.connection._end_request_decorator")
    def test_initialize_no_username_or_password(self, mock_end, mock_mongoclient):
        mock_mongoclient_instance = mock_mongoclient.return_value
        mock_mongoclient_instance.server_info.return_value = {"version":
                                                              connection.MONGO_MINIMUM_VERSION}
        config.config.set('database', 'username', '')
        config.config.set('database', 'password', '')
        connection.initialize()
        self.assertFalse(connection._DATABASE.authenticate.called)

    @patch("pymongo.MongoClient")
    @patch("pulp.server.db.connection._end_request_decorator")
    def test_initialize_username_no_password(self, mock_end, mock_mongoclient):
        mock_mongoclient_instance = mock_mongoclient.return_value
        mock_mongoclient_instance.server_info.return_value = {"version":
                                                              connection.MONGO_MINIMUM_VERSION}
        config.config.set('database', 'username', 'admin')
        config.config.set('database', 'password', '')
        self.assertRaises(Exception, connection.initialize)

    @patch("pymongo.MongoClient")
    @patch("pulp.server.db.connection._end_request_decorator")
    def test_initialize_password_no_username(self, mock_end, mock_mongoclient):
        mock_mongoclient_instance = mock_mongoclient.return_value
        mock_mongoclient_instance.server_info.return_value = {"version":
                                                              connection.MONGO_MINIMUM_VERSION}
        config.config.set('database', 'username', '')
        config.config.set('database', 'password', 'foo')
        self.assertRaises(Exception, connection.initialize)
