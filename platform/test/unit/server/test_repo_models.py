# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import unittest

from pulp.server.db.model.repository import RepoContentUnit


class TestRepoContentUnit(unittest.TestCase):
    def setUp(self):
        self.unit = RepoContentUnit('repo1', 'unit1', 'rpm',
            RepoContentUnit.OWNER_TYPE_IMPORTER, 'owner1')

    def test_utc_in_iso8601(self):
        # make sure the ISO8601 serialization includes the UTC timezone
        self.assertTrue(
            self.unit.created.endswith('Z') or
            self.unit.created.endswith('+00:00'))
