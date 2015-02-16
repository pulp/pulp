import unittest

import mock

from ... import base
from pulp.plugins.loader import api, exceptions
from pulp.plugins.types.model import TypeDefinition


CATALOGER_ID = 'test_cataloger'
DISTRIBUTOR_ID = 'test_distributor'
GRP_DISTRIBUTOR_ID = 'test_group_distributor'
GRP_IMPORTER_ID = 'test_group_importer'
IMPORTER_ID = 'test_importer'
TYPES = ['A', 'B']
METADATA = {'types': TYPES}
PROFILER_ID = 'test_profiler'


class MockCataloger:

    @classmethod
    def metadata(cls):
        return METADATA


class MockDistributor:

    @classmethod
    def metadata(cls):
        return METADATA


class MockGroupDistributor:

    @classmethod
    def metadata(cls):
        return METADATA


class MockGroupImporter:

    @classmethod
    def metadata(cls):
        return METADATA


class MockImporter:

    @classmethod
    def metadata(cls):
        return METADATA


class MockProfiler:

    @classmethod
    def metadata(cls):
        return METADATA


class LoaderApiTests(base.PulpServerTests):
    """
    This class tests the pulp.plugins.loader.api module.
    """

    @mock.patch('pulp.plugins.loader.api._load_type_definitions', autospec=True)
    @mock.patch('pulp.plugins.loader.api._check_content_definitions', autospec=True)
    def test_load_content_types_dry_run(self, mock_check_content, mock_load_type):
        """
        Test that calling load_content_types with dry_run=True results in checking the content types
         rather than loading them.
        """
        api.load_content_types(dry_run=True)
        self.assertEquals(1, mock_check_content.call_count)
        self.assertEquals(0, mock_load_type.call_count)

    @mock.patch('pulp.plugins.types.parser.parse', autospec=True)
    @mock.patch('pulp.plugins.types.database.type_definition', autospec=True)
    def test_check_content_definitions_nothing_old(self, mock_type_definition, mock_parser):
        """
        Test that when the content type from the database matches the TypeDefinition,
        an empty list is returned.
        """
        fake_type = {
            'id': 'steve_holt',
            'display_name': 'STEVE HOLT!',
            'description': 'STEVE HOLT!',
            'unit_key': ['STEVE HOLT!'],
            'search_indexes': ['STEVE HOLT!'],
            'referenced_types': ['STEVE HOLT!'],
        }
        mock_type_definition.return_value = fake_type
        type_definition = TypeDefinition('steve_holt', 'STEVE HOLT!', 'STEVE HOLT!', 'STEVE HOLT!',
                                         'STEVE HOLT!', 'STEVE HOLT!')
        mock_parser.return_value = [type_definition]

        result = api._check_content_definitions([])
        self.assertEquals(0, len(result))

    @mock.patch('pulp.plugins.types.parser.parse', autospec=True)
    @mock.patch('pulp.plugins.types.database.type_definition', autospec=True)
    def test_check_content_definitions_old(self, mock_type_definition, mock_parser):
        """
        Test that when the content type from the database doesn't match the TypeDefinition,
        the list contains that content type.
        """
        fake_type = {
            'id': 'gob',
            'display_name': 'Trickster',
            'description': 'Trickster',
            'unit_key': ['Trickster'],
            'search_indexes': ['Trickster'],
            'referenced_types': ['Trickster'],
        }
        mock_type_definition.return_value = fake_type
        type_definition = TypeDefinition('gob', 'STEVE HOLT!', 'STEVE HOLT!', 'STEVE HOLT!',
                                         'STEVE HOLT!', 'STEVE HOLT!')
        mock_parser.return_value = [type_definition]

        result = api._check_content_definitions([])
        self.assertEquals(1, len(result))
        self.assertEquals(result[0], type_definition)


class TestEntryPoint(base.PulpServerTests):

    @mock.patch('pulp.plugins.loader.loading.load_plugins_from_entry_point', autospec=True)
    def test_init_calls_entry_points(self, mock_load):
        api._MANAGER = None
        # This test is problematic, because it relies on the pulp_rpm package, which depends on this
        # package. We should really mock the type loading and test that the mocked types were loaded
        # For now, we can get around the problem by just calling load_content_types.
        api.load_content_types()
        api.initialize()
        # calls for 5 types of plugins
        self.assertEqual(mock_load.call_count, 6)


class TestAPI(unittest.TestCase):

    def setUp(self):
        super(TestAPI, self).setUp()
        api._MANAGER = None
        api._create_manager()
        api._MANAGER.importers.add_plugin(IMPORTER_ID, MockImporter, {})
        api._MANAGER.group_importers.add_plugin(GRP_IMPORTER_ID, MockGroupImporter, {})
        api._MANAGER.distributors.add_plugin(DISTRIBUTOR_ID, MockDistributor, {})
        api._MANAGER.group_distributors.add_plugin(GRP_DISTRIBUTOR_ID, MockGroupDistributor, {})
        api._MANAGER.profilers.add_plugin(PROFILER_ID, MockProfiler, {}, TYPES)
        api._MANAGER.catalogers.add_plugin(CATALOGER_ID, MockCataloger, {})

    def tearDown(self):
        super(TestAPI, self).tearDown()
        api._MANAGER = None

    def test_importers(self):
        # listing
        importers = api.list_importers()
        self.assertEqual(len(importers), 1)
        self.assertEqual(importers, {IMPORTER_ID: METADATA})
        # list types
        self.assertEqual(api.list_importer_types(IMPORTER_ID), METADATA)
        # by id
        importer = api.get_importer_by_id(IMPORTER_ID)
        self.assertFalse(importer is None)
        self.assertTrue(isinstance(importer[0], MockImporter))
        self.assertRaises(exceptions.PluginNotFound, api.get_importer_by_id, 'not-valid')
        # is_valid
        self.assertTrue(api.is_valid_importer(IMPORTER_ID))
        self.assertFalse(api.is_valid_importer('not-valid'))

    def test_group_importers(self):
        # listing
        importers = api.list_group_importers()
        self.assertEqual(len(importers), 1)
        self.assertEqual(importers, {GRP_IMPORTER_ID: METADATA})
        # by id
        importer = api.get_group_importer_by_id(GRP_IMPORTER_ID)
        self.assertFalse(importer is None)
        self.assertTrue(isinstance(importer[0], MockGroupImporter))
        self.assertRaises(exceptions.PluginNotFound, api.get_group_importer_by_id, 'not-valid')
        # is_valid
        self.assertTrue(api.is_valid_group_importer(GRP_IMPORTER_ID))
        self.assertFalse(api.is_valid_group_importer('not-valid'))

    def test_distributors(self):
        # listing
        distributors = api.list_distributors()
        self.assertEqual(len(distributors), 1)
        self.assertEqual(distributors, {DISTRIBUTOR_ID: METADATA})
        # list types
        self.assertEqual(api.list_distributor_types(DISTRIBUTOR_ID), METADATA)
        # by id
        distributor = api.get_distributor_by_id(DISTRIBUTOR_ID)
        self.assertFalse(distributor is None)
        self.assertTrue(isinstance(distributor[0], MockDistributor))
        self.assertRaises(exceptions.PluginNotFound, api.get_distributor_by_id, 'not-valid')
        # is_valid
        self.assertTrue(api.is_valid_distributor(DISTRIBUTOR_ID))
        self.assertFalse(api.is_valid_distributor('not-valid'))

    def test_group_distributors(self):
        # listing
        distributors = api.list_group_distributors()
        self.assertEqual(len(distributors), 1)
        self.assertEqual(distributors, {GRP_DISTRIBUTOR_ID: METADATA})
        # by id
        distributor = api.get_group_distributor_by_id(GRP_DISTRIBUTOR_ID)
        self.assertFalse(distributor is None)
        self.assertTrue(isinstance(distributor[0], MockGroupDistributor))
        self.assertRaises(exceptions.PluginNotFound, api.get_group_distributor_by_id, 'not-valid')
        # is_valid
        self.assertTrue(api.is_valid_group_distributor(GRP_DISTRIBUTOR_ID))
        self.assertFalse(api.is_valid_group_distributor('not-valid'))

    def test_profilers(self):
        # listing
        profilers = api.list_profilers()
        self.assertEqual(len(profilers), 1)
        self.assertEqual(profilers, {PROFILER_ID: METADATA})
        # list types
        self.assertEqual(api.list_profiler_types(PROFILER_ID), METADATA)
        # by id
        profiler = api.get_profiler_by_id(PROFILER_ID)
        self.assertFalse(profiler is None)
        self.assertTrue(isinstance(profiler[0], MockProfiler))
        self.assertRaises(exceptions.PluginNotFound, api.get_profiler_by_id, 'not-valid')
        # by type
        profiler = api.get_profiler_by_type(TYPES[0])
        self.assertFalse(profiler is None)
        self.assertTrue(isinstance(profiler[0], MockProfiler))
        self.assertRaises(exceptions.PluginNotFound, api.get_profiler_by_type, 'not-valid')
        # is_valid
        self.assertTrue(api.is_valid_profiler(PROFILER_ID))
        self.assertFalse(api.is_valid_profiler('not-valid'))

    def test_catalogers(self):
        # listing
        catalogers = api.list_catalogers()
        self.assertEqual(len(catalogers), 1)
        self.assertEqual(catalogers, {CATALOGER_ID: METADATA})
        # by id
        cataloger = api.get_cataloger_by_id(CATALOGER_ID)
        self.assertFalse(cataloger is None)
        self.assertTrue(isinstance(cataloger[0], MockCataloger))
        self.assertRaises(exceptions.PluginNotFound, api.get_cataloger_by_id, 'not-valid')
        # is_valid
        self.assertTrue(api.is_valid_cataloger(CATALOGER_ID))
        self.assertFalse(api.is_valid_cataloger('not-valid'))

    def test_finalize(self):
        api.finalize()
        self.assertEqual(api._MANAGER, None)
