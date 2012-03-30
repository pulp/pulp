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
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

from pulp.server.managers import factory
from pulp.server.managers.consumer.cud import ConsumerManager
from pulp.server.managers.content.cud import ContentManager
from pulp.server.managers.content.query import ContentQueryManager
from pulp.server.managers.content.upload import ContentUploadManager
from pulp.server.managers.repo.cud import RepoManager
from pulp.server.managers.repo.unit_association import RepoUnitAssociationManager
from pulp.server.managers.repo.publish import RepoPublishManager
from pulp.server.managers.repo.query import RepoQueryManager
from pulp.server.managers.repo.sync import RepoSyncManager


# -- test cases --------------------------------------------------------------

class FactoryTests(testutil.PulpTest):

    def clean(self):
        super(FactoryTests, self).clean()
        factory.reset()

    def test_syntactic_sugar_methods(self):
        """
        Tests the syntactic sugar methods for retrieving specific managers.
        """

        # Test
        self.assertTrue(isinstance(factory.repo_manager(), RepoManager))
        self.assertTrue(isinstance(factory.repo_unit_association_manager(), RepoUnitAssociationManager))
        self.assertTrue(isinstance(factory.repo_publish_manager(), RepoPublishManager))
        self.assertTrue(isinstance(factory.repo_query_manager(), RepoQueryManager))
        self.assertTrue(isinstance(factory.repo_sync_manager(), RepoSyncManager))
        self.assertTrue(isinstance(factory.content_manager(), ContentManager))
        self.assertTrue(isinstance(factory.content_query_manager(), ContentQueryManager))
        self.assertTrue(isinstance(factory.content_upload_manager(), ContentUploadManager))
        self.assertTrue(isinstance(factory.consumer_manager(), ConsumerManager))

    def test_get_manager(self):
        """
        Tests retrieving a manager instance for a valid manager mapping.
        """

        # Test
        manager = factory.get_manager(factory.TYPE_REPO)

        # Verify
        self.assertTrue(manager is not None)
        self.assertTrue(isinstance(manager, RepoManager))

    def test_get_manager_invalid_type(self):
        """
        Tests retrieving a manager instance but passing a bad type ID.
        """

        # Test
        try:
            factory.get_manager('foo')
            self.fail('Invalid manager type did not raise an exception')
        except factory.InvalidType, e:
            self.assertEqual(e.type_key, 'foo')
            print(e)

    def test_register_and_reset(self):
        """
        Tests that registering a new class and resetting properly affects the
        class mappings.
        """

        # Setup
        class FakeManager:
            pass

        factory.register_manager(factory.TYPE_REPO, FakeManager)

        # Test Register
        manager = factory.get_manager(factory.TYPE_REPO)
        self.assertTrue(isinstance(manager, FakeManager))

        # Test Reset
        factory.reset()
        manager = factory.get_manager(factory.TYPE_REPO)
        self.assertTrue(isinstance(manager, RepoManager))