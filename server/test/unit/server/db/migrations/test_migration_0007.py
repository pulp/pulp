# -*- coding: utf-8 -*-
#
# Copyright © 2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import os
import pickle
import time
import unittest

import bson
import celery
import mock

from pulp.server.db.migrate.models import MigrationModule


PATH = 'pulp.server.db.migrations.0007_scheduled_task_conversion'
migration = MigrationModule(PATH)._module


consumer_install_path = os.path.join(os.path.dirname(__file__),
                                     '../../../../data/migration_0007/consumer_install.pickle')
consumer_install = open(consumer_install_path).read()
publish_path = os.path.join(os.path.dirname(__file__),
                                     '../../../../data/migration_0007/publish.pickle')
publish = open(publish_path).read()


@mock.patch('pulp.server.db.connection.get_collection')
class TestMigrate(unittest.TestCase):
    def fake_get_collection(self, name):
        mocks = {
            'scheduled_calls': self.mock_sched_collection,
            'repo_importers': self.mock_importer_collection,
            'repo_distributors': self.mock_distributor_collection,
        }
        return mocks.get(name, None)

    def setUp(self):
        self.mock_sched_collection = mock.MagicMock()
        self.mock_importer_collection = mock.MagicMock()
        self.mock_distributor_collection = mock.MagicMock()

    def test_calls_convert(self, mock_get_collection):
        # make one mock call available for migration
        scheduled_call = pickle.loads(consumer_install)
        self.mock_sched_collection.find.return_value = [scheduled_call]
        mock_get_collection.side_effect = [
            self.mock_sched_collection,
            self.mock_importer_collection,
            self.mock_distributor_collection,
        ]

        # do it
        migration.migrate()

        # make sure we tried to save the converted call
        self.mock_sched_collection.save.assert_called_once_with(scheduled_call)

    @mock.patch.object(migration, 'move_scheduled_syncs')
    def test_calls_move_syncs(self, mock_move, mock_get_collection):
        mock_get_collection.side_effect = self.fake_get_collection

        migration.migrate()

        # make sure we called the move function
        mock_move.assert_called_once_with(self.mock_importer_collection, self.mock_sched_collection)

    @mock.patch.object(migration, 'move_scheduled_publishes')
    def test_calls_move_publishes(self, mock_move, mock_get_collection):
        mock_get_collection.side_effect = self.fake_get_collection

        migration.migrate()

        # make sure we called the move function
        mock_move.assert_called_once_with(self.mock_distributor_collection, self.mock_sched_collection)


class TestMoveScheduledSyncs(unittest.TestCase):
    def test_removes_all_schedule_ids(self):
        mock_imp_collection = mock.Mock()
        mock_imp_collection.find.return_value = []
        mock_update = mock_imp_collection.update

        migration.move_scheduled_syncs(mock_imp_collection, mock.Mock())

        self.assertEqual(mock_update.call_count, 1)
        self.assertEqual(mock_update.call_args[0][0], {})
        self.assertTrue('$unset' in mock_update.call_args[0][1])
        self.assertTrue('scheduled_syncs' in mock_update.call_args[0][1]['$unset'])
        self.assertTrue(mock_update.call_args[1]['multi'])

    def test_moves_schedule_reference(self):
        fake_sched_id = str(bson.ObjectId())
        mock_imp_collection = mock.Mock()
        mock_imp_collection.find.return_value = [{'id': 'importer1', 'repo_id': 'repo1',
                                                  'scheduled_syncs': [fake_sched_id]}]
        mock_sched_collection = mock.Mock()

        migration.move_scheduled_syncs(mock_imp_collection, mock_sched_collection)

        # confirm that it called update with the right args
        self.assertEqual(mock_sched_collection.update.call_count, 1)
        args = mock_sched_collection.update.call_args[0]
        self.assertEqual(args[0], {'_id': bson.ObjectId(fake_sched_id)})
        self.assertEqual(args[1]['$set']['resource'], 'pulp:importer:repo1:importer1')

    def test_no_scheduled_syncs(self):
        mock_imp_collection = mock.Mock()
        mock_imp_collection.find.return_value = [{'id': 'imorter1', 'repo_id': 'repo1',
                                                  'scheduled_syncs': None}]
        mock_sched_collection = mock.Mock()

        migration.move_scheduled_syncs(mock_imp_collection, mock_sched_collection)

        # make sure it gracefully handles this by not calling update()
        self.assertEqual(mock_sched_collection.update.call_count, 0)


class TestMoveScheduledPublishes(unittest.TestCase):
    def test_removes_all_schedule_ids(self):
        mock_dist_collection = mock.Mock()
        mock_dist_collection.find.return_value = []
        mock_update = mock_dist_collection.update

        migration.move_scheduled_publishes(mock_dist_collection, mock.Mock())

        self.assertEqual(mock_update.call_count, 1)
        self.assertEqual(mock_update.call_args[0][0], {})
        self.assertTrue('$unset' in mock_update.call_args[0][1])
        self.assertTrue('scheduled_publishes' in mock_update.call_args[0][1]['$unset'])
        self.assertTrue(mock_update.call_args[1]['multi'])

    def test_moves_schedule_reference(self):
        fake_sched_id = str(bson.ObjectId())
        mock_dist_collection = mock.Mock()
        mock_dist_collection.find.return_value = [{'id': 'distributor1', 'repo_id': 'repo1',
                                                  'scheduled_publishes': [fake_sched_id]}]
        mock_sched_collection = mock.Mock()

        migration.move_scheduled_publishes(mock_dist_collection, mock_sched_collection)

        # confirm that it called update with the right args
        self.assertEqual(mock_sched_collection.update.call_count, 1)
        args = mock_sched_collection.update.call_args[0]
        self.assertEqual(args[0], {'_id': bson.ObjectId(fake_sched_id)})
        self.assertEqual(args[1]['$set']['resource'], 'pulp:distributor:repo1:distributor1')

    def test_no_scheduled_publishes(self):
        mock_dist_collection = mock.Mock()
        mock_dist_collection.find.return_value = [{'id': 'distributor1', 'repo_id': 'repo1',
                                                  'scheduled_publishes': None}]
        mock_sched_collection = mock.Mock()

        migration.move_scheduled_publishes(mock_dist_collection, mock_sched_collection)

        # make sure it gracefully handles this by not calling update()
        self.assertEqual(mock_sched_collection.update.call_count, 0)


class TestConvert(unittest.TestCase):
    def test_bson_serialization(self):
        """
        Ensure that the resulting object can be serialized to BSON
        """
        original = pickle.loads(consumer_install)
        mock_save = mock.Mock()

        migration.convert_schedule(mock_save, original)

        self.assertEqual(mock_save.call_count, 1)
        call = mock_save.call_args[0][0]
        # ensure it can be encoded
        bson.BSON.encode(call)

    def test_values_consumer(self):
        original = pickle.loads(consumer_install)
        mock_save = mock.Mock()

        migration.convert_schedule(mock_save, original)

        new = mock_save.call_args[0][0]

        self.assertEqual(new['args'], ['con1'])
        self.assertEqual(new['consecutive_failures'], 0)
        self.assertTrue(new['enabled'])
        self.assertEqual(new['first_run'], '2014-01-21T16:02:06Z')
        self.assertEqual(new['iso_schedule'], 'PT1M')
        self.assertEqual(new['kwargs'], {'options': {},
                                         'units': [{'type_id': 'rpm', 'unit_key': {'name': 'fakepackage'}}]})
        self.assertEqual(new['last_run_at'], '2014-01-21T16:03:06Z')
        self.assertEqual(new['remaining_runs'], None)
        self.assertEqual(new['resource'], 'pulp:consumer:con1')
        self.assertEqual(new['task'], 'pulp.server.tasks.consumer.install_content')
        self.assertEqual(new['total_run_count'], 13)

        schedule = pickle.loads(new['schedule'])
        self.assertTrue(isinstance(schedule, celery.schedules.schedule))

        # generously make sure no more than one second has elapsed from the
        # last_updated timestamp
        self.assertTrue(time.time() - new['last_updated'] < 1)

        for key in (
            'serialized_call_request',
            'control_hooks',
            'weight',
            'tags',
            'archive',
            'group_id',
            'resources',
            'next_run',
            'call_exit_states',
        ):
            self.assertTrue(key not in new)

    def test_values_publish(self):
        original = pickle.loads(publish)
        mock_save = mock.Mock()

        migration.convert_schedule(mock_save, original)

        new = mock_save.call_args[0][0]

        self.assertEqual(new['args'], ['bar', 'puppet_distributor'])
        self.assertEqual(new['consecutive_failures'], 0)
        self.assertTrue(new['enabled'])
        self.assertEqual(new['first_run'], '2014-01-24T22:53:00Z')
        self.assertEqual(new['iso_schedule'], '2014-01-24T12:00:00Z/PT1M')
        self.assertEqual(new['kwargs'], {'overrides': {}})
        self.assertEqual(new['last_run_at'], None)
        self.assertEqual(new['remaining_runs'], None)
        self.assertEqual(new['task'], 'pulp.server.tasks.repository.publish')
        self.assertEqual(new['total_run_count'], 0)

        schedule = pickle.loads(new['schedule'])
        self.assertTrue(isinstance(schedule, celery.schedules.schedule))

        # generously make sure no more than one second has elapsed from the
        # last_updated timestamp
        self.assertTrue(time.time() - new['last_updated'] < 1)

        for key in (
            'serialized_call_request',
            'control_hooks',
            'weight',
            'tags',
            'archive',
            'group_id',
            'resources',
            'next_run',
            'call_exit_states',
        ):
            self.assertTrue(key not in new)
