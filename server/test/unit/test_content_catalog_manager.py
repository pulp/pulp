# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from uuid import uuid4

from base import PulpServerTests

from pulp.server.db.model.content import ContentCatalog
from pulp.server.managers.content.catalog import ContentCatalogManager
from pulp.server.managers import factory


TYPE_ID = 'type_a'
SOURCE_ID = 'test'
EXPIRATION = 3600


class TestCatalogManager(PulpServerTests):

    def setUp(self):
        super(TestCatalogManager, self).setUp()
        ContentCatalog.get_collection().remove()

    def tearDown(self):
        super(TestCatalogManager, self).tearDown()
        ContentCatalog.get_collection().remove()

    def test_locator(self):
        key_1 = {'a': 1, 'b': 2, 'c': 3}
        key_2 = {'c': 3, 'b': 2, 'a': 1}
        key_3 = {'c': 1, 'b': 2, 'a': 3}
        locator_1 = ContentCatalog.get_locator(TYPE_ID, key_1)  # eq
        locator_2 = ContentCatalog.get_locator(TYPE_ID, key_2)  # eq
        locator_3 = ContentCatalog.get_locator(TYPE_ID, key_3)  # neq
        locator_4 = ContentCatalog.get_locator(TYPE_ID[1:], key_1)  # neq
        self.assertTrue(isinstance(locator_1, str))
        self.assertTrue(isinstance(locator_2, str))
        self.assertEqual(locator_1, locator_2)
        self.assertNotEqual(locator_1, locator_3)
        self.assertNotEqual(locator_1, locator_4)

    def units(self, start_n, end_n):
        units = []
        for n in range(start_n, start_n + end_n):
            unit_key = {
                'name': 'unit_%d' % n,
                'version': '1.0.%d' % n,
                'release': '1',
                'checksum': str(uuid4())
            }
            url = 'file://redhat.com/unit_%d' % n
            units.append((unit_key, url))
        return units

    def test_add(self):
        units = self.units(0, 10)
        manager = ContentCatalogManager()
        for unit_key, url in units:
            manager.add_entry(SOURCE_ID, EXPIRATION, TYPE_ID, unit_key, url)
        collection = ContentCatalog.get_collection()
        self.assertEqual(len(units), collection.find().count())
        for unit_key, url in units:
            locator = ContentCatalog.get_locator(TYPE_ID, unit_key)
            entry = collection.find_one({'locator': locator})
            self.assertEqual(entry['type_id'], TYPE_ID)
            self.assertEqual(entry['unit_key'], unit_key)
            self.assertEqual(entry['url'], url)

    def test_delete(self):
        units = self.units(0, 10)
        manager = ContentCatalogManager()
        for unit_key, url in units:
            manager.add_entry(SOURCE_ID, EXPIRATION, TYPE_ID, unit_key, url)
        collection = ContentCatalog.get_collection()
        self.assertEqual(len(units), collection.find().count())
        unit_key, url = units[5]
        locator = ContentCatalog.get_locator(TYPE_ID, unit_key)
        entry = collection.find_one({'locator': locator})
        self.assertEqual(entry['type_id'], TYPE_ID)
        self.assertEqual(entry['unit_key'], unit_key)
        self.assertEqual(entry['url'], url)
        manager.delete_entry(SOURCE_ID, TYPE_ID, unit_key)
        self.assertEqual(len(units) - 1, collection.find().count())
        entry = collection.find_one({'locator': locator})
        self.assertTrue(entry is None)

    def test_purge(self):
        source_a = 'A'
        source_b = 'B'
        manager = ContentCatalogManager()
        for unit_key, url in self.units(0, 10):
            manager.add_entry(source_a, EXPIRATION, TYPE_ID, unit_key, url)
        for unit_key, url in self.units(0, 10):
            manager.add_entry(source_b, EXPIRATION, TYPE_ID, unit_key, url)
        collection = ContentCatalog.get_collection()
        self.assertEqual(20, collection.find().count())
        manager = ContentCatalogManager()
        purged = manager.purge(source_a)
        self.assertEqual(purged, 10)
        self.assertEqual(collection.find({'source_id': source_a}).count(), 0)
        self.assertEqual(collection.find({'source_id': source_b}).count(), 10)

    def test_has_entries(self):
        source_a = 'A'
        source_b = 'B'
        source_c = 'C'
        manager = ContentCatalogManager()
        for unit_key, url in self.units(0, 10):
            manager.add_entry(source_a, EXPIRATION, TYPE_ID, unit_key, url)
        for unit_key, url in self.units(0, 10):
            manager.add_entry(source_b, -1, TYPE_ID, unit_key, url)
        for unit_key, url in self.units(0, 10):
            manager.add_entry(source_c, EXPIRATION, TYPE_ID, unit_key, url)
        collection = ContentCatalog.get_collection()
        self.assertEqual(30, collection.find().count())
        manager = ContentCatalogManager()
        self.assertTrue(manager.has_entries(source_a))
        self.assertFalse(manager.has_entries(source_b))
        self.assertTrue(manager.has_entries(source_c))
        manager.purge(source_c)
        self.assertTrue(manager.has_entries(source_a))
        self.assertFalse(manager.has_entries(source_b))
        self.assertFalse(manager.has_entries(source_c))

    def test_purge_expired(self):
        source_a = 'A'
        source_b = 'B'
        manager = ContentCatalogManager()
        for unit_key, url in self.units(0, 10):
            manager.add_entry(source_a, EXPIRATION, TYPE_ID, unit_key, url)
        for unit_key, url in self.units(0, 10):
            manager.add_entry(source_b, -1, TYPE_ID, unit_key, url)
        collection = ContentCatalog.get_collection()
        self.assertEqual(20, collection.find().count())
        manager = ContentCatalogManager()
        purged = manager.purge_expired(0)
        self.assertEqual(purged, 10)
        self.assertEqual(collection.find({'source_id': source_a}).count(), 10)
        self.assertEqual(collection.find({'source_id': source_b}).count(), 0)

    def test_purge_orphans(self):
        source_a = 'A'
        source_b = 'B'
        manager = ContentCatalogManager()
        for unit_key, url in self.units(0, 10):
            manager.add_entry(source_a, EXPIRATION, TYPE_ID, unit_key, url)
        for unit_key, url in self.units(0, 10):
            manager.add_entry(source_b, 1, TYPE_ID, unit_key, url)
        collection = ContentCatalog.get_collection()
        self.assertEqual(20, collection.find().count())
        manager = ContentCatalogManager()
        purged = manager.purge_orphans([source_b])
        self.assertEqual(purged, 10)
        self.assertEqual(collection.find({'source_id': source_a}).count(), 0)
        self.assertEqual(collection.find({'source_id': source_b}).count(), 10)

    def test_find(self):
        units = self.units(0, 10)
        manager = ContentCatalogManager()
        for unit_key, url in units:
            manager.add_entry(SOURCE_ID, EXPIRATION, TYPE_ID, unit_key, url)
        collection = ContentCatalog.get_collection()
        self.assertEqual(len(units), collection.find().count())
        for unit_key, url in units:
            locator = ContentCatalog.get_locator(TYPE_ID, unit_key)
            entry = collection.find_one({'locator': locator})
            self.assertEqual(entry['type_id'], TYPE_ID)
            self.assertEqual(entry['unit_key'], unit_key)
            self.assertEqual(entry['url'], url)
        for unit_key, url in units:
            entries = manager.find(TYPE_ID, unit_key)
            self.assertEqual(len(entries), 1)
            entry = entries[0]
            self.assertEqual(entry['type_id'], TYPE_ID)
            self.assertEqual(entry['unit_key'], unit_key)
            self.assertEqual(entry['url'], url)

    def test_expired(self):
        units = self.units(0, 10)
        manager = ContentCatalogManager()
        for unit_key, url in units:
            manager.add_entry(SOURCE_ID, -1, TYPE_ID, unit_key, url)
        collection = ContentCatalog.get_collection()
        self.assertEqual(len(units), collection.find().count())
        for unit_key, url in units:
            locator = ContentCatalog.get_locator(TYPE_ID, unit_key)
            entry = collection.find_one({'locator': locator})
            self.assertEqual(entry['type_id'], TYPE_ID)
            self.assertEqual(entry['unit_key'], unit_key)
            self.assertEqual(entry['url'], url)
        for unit_key, url in units:
            entries = manager.find(TYPE_ID, unit_key)
            self.assertEqual(len(entries), 0)

    def test_factory(self):
        manager = factory.content_catalog_manager()
        self.assertTrue(isinstance(manager, ContentCatalogManager))