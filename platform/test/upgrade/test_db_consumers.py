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

from pymongo.objectid import ObjectId

from base_db_upgrade import BaseDbUpgradeTests
from pulp.server.upgrade.model import UpgradeStepReport
from pulp.server.upgrade.db import consumers


class ConsumersUpgradeTests(BaseDbUpgradeTests):

    def test_consumers(self):
        # Test
        report = consumers.upgrade(self.v1_test_db.database, self.tmp_test_db.database)

        # Verify
        self.assertTrue(isinstance(report, UpgradeStepReport))
        self.assertTrue(report.success)

        # - Consumer History -
        v1_entries = list(self.v1_test_db.database.consumer_history.find())
        v2_entries = list(self.tmp_test_db.database.consumer_history.find())
        self.assertEqual(len(v1_entries), len(v2_entries))

        for v1_entry, v2_entry in zip(v1_entries, v2_entries):
            self.assertEqual(v1_entry.pop('type_name'), v2_entry.pop('type'))
            self.assertEqual(v1_entry, v2_entry)

        # - Consumers -
        v1_consumers = list(self.v1_test_db.database.consumers.find())
        v2_consumers = list(self.tmp_test_db.database.consumers.find())
        self.assertEqual(len(v1_consumers), len(v2_consumers))

        for v1_consumer, v2_consumer in zip(v1_consumers, v2_consumers):
            self.assertTrue(isinstance(v2_consumer['_id'], ObjectId))
            self.assertEqual(v1_consumer['id'], v2_consumer['id'])
            self.assertEqual(v1_consumer['id'], v2_consumer['display_name'])
            self.assertEqual(v1_consumer['key_value_pairs'], v2_consumer['notes'])
            self.assertEqual(v1_consumer['capabilities'], v2_consumer['capabilities'])
            self.assertEqual(v1_consumer['certificate'], v2_consumer['certificate'])

        # - Consumer Bindings -
        binding_coll = self.tmp_test_db.database.consumer_bindings
        for v1_consumer in v1_consumers:
            for repo_id in v1_consumer['repoids']:
                binding = binding_coll.find_one({'consumer_id' : v1_consumer['id'],
                                                 'repo_id' : repo_id})
                self.assertTrue(binding is not None)
                self.assertEqual(binding['distributor_id'], consumers.YUM_DISTRIBUTOR_ID)

        # - Unit Profile -
        profile_coll = self.tmp_test_db.database.consumer_unit_profiles
        for v1_consumer in v1_consumers:
            if v1_consumer['package_profile']:
                profile = profile_coll.find_one({'consumer_id' : v1_consumer['id']})
                self.assertEqual(profile['consumer_id'], v1_consumer['id'])
                self.assertEqual(profile['content_type'], consumers.RPM_TYPE)
                self.assertEqual(profile['profile'], v1_consumer['package_profile'])

    def test_consumers_resumed(self):
        # Setup
        consumers.upgrade(self.v1_test_db.database, self.tmp_test_db.database)
        new_consumer = {
            'id' : 'fake-consumer',
            'description' : 'fake-description',
            'key_value_pairs' : {'a' : 'a'},
            'capabilities' : {},
            'certificate' : 'ABCDE',
            'repoids' : ['repo-1', 'repo-2'],
            'package_profile' : ['some RPMs and stuff']
        }
        self.v1_test_db.database.consumers.insert(new_consumer)

        new_consumer_history = {
            'consumer_id' : 'fake-consumer',
            'originator' : 'admin',
            'type_name' : 'install',
            'details' : 'installed stuff',
            'timestamp' : '10-23-2012',
        }
        self.v1_test_db.database.consumer_history.insert(new_consumer_history)

        # Test
        report = consumers.upgrade(self.v1_test_db.database, self.tmp_test_db.database)

        # Verify
        self.assertTrue(isinstance(report, UpgradeStepReport))
        self.assertTrue(report.success)

        v1_entries = list(self.v1_test_db.database.consumer_history.find())
        v2_entries = list(self.tmp_test_db.database.consumer_history.find())
        self.assertEqual(len(v1_entries), len(v2_entries))

        v1_consumers = list(self.v1_test_db.database.consumers.find())
        v2_consumers = list(self.tmp_test_db.database.consumers.find())
        self.assertEqual(len(v1_consumers), len(v2_consumers))

        binding_coll = self.tmp_test_db.database.consumer_bindings
        for v1_consumer in v1_consumers:
            for repo_id in v1_consumer['repoids']:
                binding = binding_coll.find_one({'consumer_id' : v1_consumer['id'],
                                                 'repo_id' : repo_id})
                self.assertTrue(binding is not None)
                self.assertEqual(binding['distributor_id'], consumers.YUM_DISTRIBUTOR_ID)

        profile_coll = self.tmp_test_db.database.consumer_unit_profiles
        for v1_consumer in v1_consumers:
            if v1_consumer['package_profile']:
                profile = profile_coll.find_one({'consumer_id' : v1_consumer['id']})
                self.assertTrue(profile is not None)

    def test_consumers_idempotency(self):
        # Setup
        consumers.upgrade(self.v1_test_db.database, self.tmp_test_db.database)

        # Test
        report = consumers.upgrade(self.v1_test_db.database, self.tmp_test_db.database)

        # Verify
        self.assertTrue(isinstance(report, UpgradeStepReport))
        self.assertTrue(report.success)

        v1_entries = list(self.v1_test_db.database.consumer_history.find())
        v2_entries = list(self.tmp_test_db.database.consumer_history.find())
        self.assertEqual(len(v1_entries), len(v2_entries))

        v1_consumers = list(self.v1_test_db.database.consumers.find())
        v2_consumers = list(self.tmp_test_db.database.consumers.find())
        self.assertEqual(len(v1_consumers), len(v2_consumers))

        binding_coll = self.tmp_test_db.database.consumer_bindings
        for v1_consumer in v1_consumers:
            for repo_id in v1_consumer['repoids']:
                binding = binding_coll.find_one({'consumer_id' : v1_consumer['id'],
                                                 'repo_id' : repo_id})
                self.assertTrue(binding is not None)
                self.assertEqual(binding['distributor_id'], consumers.YUM_DISTRIBUTOR_ID)

        profile_coll = self.tmp_test_db.database.consumer_unit_profiles
        for v1_consumer in v1_consumers:
            if v1_consumer['package_profile']:
                profile = profile_coll.find_one({'consumer_id' : v1_consumer['id']})
                self.assertTrue(profile is not None)

