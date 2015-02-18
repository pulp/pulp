from .... import base
from pulp.plugins.types import database, model
from pulp.server.managers.content.cud import ContentManager
from pulp.server.managers.content.query import ContentQueryManager


TYPE_1_DEF = model.TypeDefinition('type-1', 'Type 1', 'Test Definition One',
                                  ['key-1'], ['search-1'], [])

TYPE_2_DEF = model.TypeDefinition('type-2', 'Type 2', 'Test Definition Two',
                                  ['key-2a', 'key-2b'], [], ['type-1'])

TYPE_1_UNITS = [
    {'key-1': 'A',
     'search-1': 'one'},
    {'key-1': 'B',
     'search-1': 'one'},
    {'key-1': 'C',
     'search-1': 'two'}]

TYPE_2_UNITS = [
    {'key-2a': 'A',
     'key-2b': 'A'},
    {'key-2a': 'A',
     'key-2b': 'B'},
    {'key-2a': 'B',
     'key-2b': 'A'},
    {'key-2a': 'A',
     'key-2b': 'C'},
    {'key-2a': 'B',
     'key-2b': 'C'}]


class PulpContentTests(base.PulpServerTests):

    def setUp(self):
        super(PulpContentTests, self).setUp()
        database.update_database([TYPE_1_DEF, TYPE_2_DEF])
        self.cud_manager = ContentManager()
        self.query_manager = ContentQueryManager()

    def clean(self):
        super(PulpContentTests, self).clean()
        database.clean()


class PulpContentCUDTests(PulpContentTests):

    def test_add_content_unit(self):
        unit_id = self.cud_manager.add_content_unit(TYPE_1_DEF.id, None, TYPE_1_UNITS[0])
        self.assertNotEqual(unit_id, None)
        units = self.query_manager.list_content_units(TYPE_1_DEF.id)
        self.assertEqual(len(units), 1)
        self.assertTrue('_last_updated' in units[0])

    def test_update_content_unit(self):
        unit_id = self.cud_manager.add_content_unit(TYPE_1_DEF.id, None, TYPE_1_UNITS[0])
        unit = self.query_manager.get_content_unit_by_id(TYPE_1_DEF.id, unit_id)
        self.assertTrue(unit['search-1'] == 'one')
        self.cud_manager.update_content_unit(TYPE_1_DEF.id, unit_id, {'search-1': 'two'})
        unit = self.query_manager.get_content_unit_by_id(TYPE_1_DEF.id, unit_id)
        self.assertTrue(unit['search-1'] == 'two')
        self.assertTrue('_last_updated' in unit)

    def test_delete_content_unit(self):
        unit_id = self.cud_manager.add_content_unit(TYPE_1_DEF.id, None, TYPE_1_UNITS[0])
        units = self.query_manager.list_content_units(TYPE_1_DEF.id)
        self.assertEqual(len(units), 1)
        self.cud_manager.remove_content_unit(TYPE_1_DEF.id, unit_id)
        units = self.query_manager.list_content_units(TYPE_1_DEF.id)
        self.assertEqual(len(units), 0)

    def test_link_child_unit(self):
        parent_id = self.cud_manager.add_content_unit(TYPE_2_DEF.id, None, TYPE_2_UNITS[0])
        child_id = self.cud_manager.add_content_unit(TYPE_1_DEF.id, None, TYPE_1_UNITS[0])
        self.cud_manager.link_referenced_content_units(TYPE_2_DEF.id, parent_id, TYPE_1_DEF.id,
                                                       [child_id])
        parent = self.query_manager.get_content_unit_by_id(TYPE_2_DEF.id, parent_id)
        self.assertEqual(parent['_%s_references' % TYPE_1_DEF.id][0], child_id)

    def test_unlink_child_unit(self):
        parent_id = self.cud_manager.add_content_unit(TYPE_2_DEF.id, None, TYPE_2_UNITS[0])
        child_id = self.cud_manager.add_content_unit(TYPE_1_DEF.id, None, TYPE_1_UNITS[0])
        self.cud_manager.link_referenced_content_units(TYPE_2_DEF.id, parent_id, TYPE_1_DEF.id,
                                                       [child_id])
        parent = self.query_manager.get_content_unit_by_id(TYPE_2_DEF.id, parent_id)
        self.assertEqual(len(parent['_%s_references' % TYPE_1_DEF.id]), 1)
        self.cud_manager.unlink_referenced_content_units(TYPE_2_DEF.id, parent_id, TYPE_1_DEF.id,
                                                         [child_id])
        parent = self.query_manager.get_content_unit_by_id(TYPE_2_DEF.id, parent_id)
        self.assertEqual(len(parent['_%s_references' % TYPE_1_DEF.id]), 0)
