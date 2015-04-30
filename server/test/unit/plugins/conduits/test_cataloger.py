from uuid import uuid4

from ... import base
from pulp.plugins.conduits.cataloger import CatalogerConduit
from pulp.server.db.model.content import ContentCatalog


TYPE_ID = 'type_a'
SOURCE_ID = 'test'
EXPIRES = 3600


class TestCatalogerConduit(base.PulpServerTests):

    def setUp(self):
        super(TestCatalogerConduit, self).setUp()
        ContentCatalog.get_collection().remove()

    def tearDown(self):
        super(TestCatalogerConduit, self).tearDown()
        ContentCatalog.get_collection().remove()

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
        conduit = CatalogerConduit(SOURCE_ID, EXPIRES)
        for unit_key, url in units:
            conduit.add_entry(TYPE_ID, unit_key, url)
        collection = ContentCatalog.get_collection()
        self.assertEqual(conduit.source_id, SOURCE_ID)
        self.assertEqual(conduit.expires, EXPIRES)
        self.assertEqual(len(units), collection.find().count())
        self.assertEqual(conduit.added_count, len(units))
        self.assertEqual(conduit.deleted_count, 0)
        for unit_key, url in units:
            locator = ContentCatalog.get_locator(TYPE_ID, unit_key)
            entry = collection.find_one({'locator': locator})
            self.assertEqual(entry['type_id'], TYPE_ID)
            self.assertEqual(entry['unit_key'], unit_key)
            self.assertEqual(entry['url'], url)

    def test_delete(self):
        units = self.units(0, 10)
        conduit = CatalogerConduit(SOURCE_ID, EXPIRES)
        for unit_key, url in units:
            conduit.add_entry(TYPE_ID, unit_key, url)
        collection = ContentCatalog.get_collection()
        self.assertEqual(len(units), collection.find().count())
        unit_key, url = units[5]
        locator = ContentCatalog.get_locator(TYPE_ID, unit_key)
        entry = collection.find_one({'locator': locator})
        self.assertEqual(entry['type_id'], TYPE_ID)
        self.assertEqual(entry['unit_key'], unit_key)
        self.assertEqual(entry['url'], url)
        conduit.delete_entry(TYPE_ID, unit_key)
        self.assertEqual(len(units) - 1, collection.find().count())
        self.assertEqual(conduit.added_count, len(units))
        self.assertEqual(conduit.deleted_count, 1)
        entry = collection.find_one({'locator': locator})
        self.assertTrue(entry is None)

    def test_reset(self):
        conduit = CatalogerConduit(SOURCE_ID, EXPIRES)
        conduit.added_count = 10
        conduit.deleted_count = 10
        conduit.reset()
        self.assertEqual(conduit.added_count, 0)
        self.assertEqual(conduit.deleted_count, 0)
