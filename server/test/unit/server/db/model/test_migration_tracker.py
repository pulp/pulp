"""
Tests for the pulp.server.db.model.migration_tracker module.
"""
import unittest

from pulp.server.db.model.migration_tracker import MigrationTracker


class TestMigrationTracker(unittest.TestCase):

    def test_name_version(self):
        mt = MigrationTracker('meaning_of_life', 42)
        self.assertEquals(mt.name, 'meaning_of_life')
        self.assertEquals(mt.version, 42)

    def test_name_version_default(self):
        mt = MigrationTracker('meaning_of_life')
        self.assertEquals(mt.name, 'meaning_of_life')
        self.assertEquals(mt.version, 0)

    def test_presense_of_ns(self):
        mt = MigrationTracker('meaning_of_life')
        self.assertEquals(mt._ns, 'migration_trackers')
