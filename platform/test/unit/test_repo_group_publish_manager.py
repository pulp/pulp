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

import base
import datetime
import mock_plugins

from pulp.common import dateutils
from pulp.plugins.conduits.repo_publish import RepoGroupPublishConduit
from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.model import RepositoryGroup, PublishReport
from pulp.server.db.model.repo_group import RepoGroup, RepoGroupDistributor, RepoGroupPublishResult
from pulp.server.exceptions import PulpExecutionException
from pulp.server.managers import factory as manager_factory

# -- test cases ---------------------------------------------------------------

class RepoGroupPublishManagerTests(base.PulpServerTests):
    def setUp(self):
        super(RepoGroupPublishManagerTests, self).setUp()
        mock_plugins.install()

        self.group_manager = manager_factory.repo_group_manager()
        self.distributor_manager = manager_factory.repo_group_distributor_manager()
        self.publish_manager = manager_factory.repo_group_publish_manager()

        self.group_id = 'publish-group'
        self.group_manager.create_repo_group(self.group_id)

        self.distributor_id = 'publish-dist'
        self.distributor_manager.add_distributor(self.group_id, 'mock-group-distributor', {}, distributor_id=self.distributor_id)

    def tearDown(self):
        super(RepoGroupPublishManagerTests, self).tearDown()
        mock_plugins.reset()

    def clean(self):
        super(RepoGroupPublishManagerTests, self).clean()

        RepoGroup.get_collection().remove()
        RepoGroupDistributor.get_collection().remove()
        RepoGroupPublishResult.get_collection().remove()

    def test_publish(self):
        # Setup
        summary = 'summary'
        details = 'details'
        mock_plugins.MOCK_GROUP_DISTRIBUTOR.publish_group.return_value = PublishReport(True, summary, details)

        # Test
        override_config = {'o' : 'o'}
        self.publish_manager.publish(self.group_id, self.distributor_id, publish_config_override=override_config)

        # Verify

        # Plugin Call
        self.assertEqual(1, mock_plugins.MOCK_GROUP_DISTRIBUTOR.publish_group.call_count)
        call_args = mock_plugins.MOCK_GROUP_DISTRIBUTOR.publish_group.call_args[0]

        self.assertTrue(isinstance(call_args[0], RepositoryGroup))
        self.assertEqual(call_args[0].id, self.group_id)

        self.assertTrue(isinstance(call_args[1], RepoGroupPublishConduit))
        self.assertEqual(call_args[1].group_id, self.group_id)
        self.assertEqual(call_args[1].distributor_id, self.distributor_id)

        self.assertTrue(isinstance(call_args[2], PluginCallConfiguration))
        self.assertEqual(call_args[2].override_config, override_config)

        # History Entry
        history_entries = list(RepoGroupPublishResult.get_collection().find())
        self.assertEqual(1, len(history_entries))
        self.assertEqual(history_entries[0]['group_id'], self.group_id)
        self.assertEqual(history_entries[0]['distributor_id'], self.distributor_id)
        self.assertEqual(history_entries[0]['distributor_type_id'], 'mock-group-distributor')
        self.assertTrue(history_entries[0]['started'] is not None)
        self.assertTrue(history_entries[0]['completed'] is not None)
        self.assertEqual(history_entries[0]['result'], RepoGroupPublishResult.RESULT_SUCCESS)
        self.assertTrue(history_entries[0]['error_message'] is None)
        self.assertTrue(history_entries[0]['exception'] is None)
        self.assertTrue(history_entries[0]['traceback'] is None)
        self.assertEqual(history_entries[0]['summary'], summary)
        self.assertEqual(history_entries[0]['details'], details)

        # Distributor Update
        distributor = self.distributor_manager.get_distributor(self.group_id, self.distributor_id)
        self.assertTrue(distributor['last_publish'] is not None)

        # Clean Up
        mock_plugins.MOCK_GROUP_DISTRIBUTOR.publish_group.return_value = None

    def test_publish_with_plugin_exception(self):
        # Setup
        mock_plugins.MOCK_GROUP_DISTRIBUTOR.publish_group.side_effect = Exception()

        # Test
        self.assertRaises(PulpExecutionException, self.publish_manager.publish, self.group_id, self.distributor_id)

        # Verify
        history_entries = list(RepoGroupPublishResult.get_collection().find())
        self.assertEqual(1, len(history_entries))
        self.assertEqual(history_entries[0]['result'], RepoGroupPublishResult.RESULT_ERROR)
        self.assertTrue(history_entries[0]['error_message'] is not None)
        self.assertTrue(history_entries[0]['exception'] is not None)
        self.assertTrue(history_entries[0]['traceback'] is not None)
        self.assertTrue(history_entries[0]['summary'] is None)
        self.assertTrue(history_entries[0]['details'] is None)

        # Clean Up
        mock_plugins.MOCK_GROUP_DISTRIBUTOR.publish_group.side_effect = None

    def test_publish_with_plugin_failure_report(self):
        # Setup
        summary = 'summary'
        details = 'details'
        mock_plugins.MOCK_GROUP_DISTRIBUTOR.publish_group.return_value = PublishReport(False, summary, details)

        # Test
        self.publish_manager.publish(self.group_id, self.distributor_id)

        # Verify
        history_entries = list(RepoGroupPublishResult.get_collection().find())
        self.assertEqual(1, len(history_entries))
        self.assertEqual(history_entries[0]['result'], RepoGroupPublishResult.RESULT_FAILED)
        self.assertEqual(history_entries[0]['summary'], summary)
        self.assertEqual(history_entries[0]['details'], details)

        # Clean Up
        mock_plugins.MOCK_GROUP_DISTRIBUTOR.publish_group.return_value = None

    def test_publish_with_plugin_no_report(self):
        # Test
        self.publish_manager.publish(self.group_id, self.distributor_id)

        # Verify
        history_entries = list(RepoGroupPublishResult.get_collection().find())
        self.assertEqual(1, len(history_entries))
        self.assertEqual(history_entries[0]['result'], RepoGroupPublishResult.RESULT_SUCCESS)

    def test_last_publish(self):
        # Setup
        self.publish_manager.publish(self.group_id, self.distributor_id)

        # Test
        last_publish = self.publish_manager.last_publish(self.group_id, self.distributor_id)

        # Verify
        now = datetime.datetime.now(dateutils.local_tz())
        difference = now - last_publish
        self.assertTrue(difference.seconds < 2)
