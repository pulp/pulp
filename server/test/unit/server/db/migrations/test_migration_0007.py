import os
import pickle
import unittest

import bson
import celery
import mock

from pulp.server.db.migrate.models import MigrationModule

PATH = 'pulp.server.db.migrations.0007_scheduled_task_conversion'
migration = MigrationModule(PATH)._module



consumer_install_path = os.path.join(os.path.dirname(__file__), '../../../../data/migration_0007/consumer_install.pickle')
consumer_install = open(consumer_install_path).read()


class TestConvert(unittest.TestCase):
    def test_bson_serialization(self):
        """
        Ensure that the resulting object can be serialized to BSON
        """
        original = pickle.loads(consumer_install)
        mock_save = mock.Mock()

        migration.convert_schedules(mock_save, original)

        self.assertEqual(mock_save.call_count, 1)
        call = mock_save.call_args[0][0]
        # ensure it can be encoded
        bson.BSON.encode(call)

    def test_values(self):
        original = pickle.loads(consumer_install)
        mock_save = mock.Mock()

        migration.convert_schedules(mock_save, original)

        new = mock_save.call_args[0][0]

        self.assertEqual(new['args'], ['con1'])
        self.assertEqual(new['consecutive_failures'], 0)
        self.assertTrue(new['enabled'])
        self.assertEqual(new['iso_schedule'], 'PT1M')
        self.assertEqual(new['kwargs'], {'options': {},
                                         'units': [{'type_id': 'rpm', 'unit_key': {'name': 'fakepackage'}}]})
        self.assertEqual(new['remaining_runs'], None)
        self.assertEqual(new['resource'], 'pulp:consumer:con1')
        self.assertEqual(new['task'], 'pulp.server.tasks.consumer.install_content')
        self.assertEqual(new['total_run_count'], 13)

        schedule = pickle.loads(new['schedule'])
        self.assertTrue(isinstance(schedule, celery.schedules.schedule))

