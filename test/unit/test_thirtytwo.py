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

# Python
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

from pulp.server.db.model.resource import Repo
from pulp.server.db.migrate.versions import thirtytwo

class TestRepoApi(testutil.PulpAsyncTest):

    def test_success(self):
        # Setup
        r1 = Repo('r1', 'R1', 'noarch', relative_path='foo')
        r2 = Repo('r2', 'R2', 'noarch', relative_path='bar')

        Repo.get_collection().save(r1, safe=True)
        Repo.get_collection().save(r2, safe=True)

        # Test
        result = thirtytwo.migrate()

        # Verify
        self.assertTrue(result)

    def test_failure(self):
        # Setup
        r1 = Repo('r1', 'R1', 'noarch', relative_path='foo/bar')
        r2 = Repo('r2', 'R2', 'noarch', relative_path='foo/bar/baz')

        Repo.get_collection().save(r1, safe=True)
        Repo.get_collection().save(r2, safe=True)

        # Test
        result = thirtytwo.migrate()

        # Verify
        self.assertFalse(result)
