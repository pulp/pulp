#!/usr/bin/python
#
# Copyright (c) 2012 Red Hat, Inc.
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

import mock

import base
from pulp.server.db.model.criteria import Criteria
from pulp.server.managers.repo.group import query

class RepoGroupQueryManagerTests(base.PulpServerTests):
    def setUp(self):
        base.PulpServerTests.setUp(self)

        self.query_manager = query.RepoGroupQueryManager()

    @mock.patch('pulp.server.db.connection.PulpCollection.query')
    def test_find_by_criteria(self, mock_query):
        criteria = Criteria()
        self.query_manager.find_by_criteria(criteria)
        mock_query.assert_called_once_with(criteria)

