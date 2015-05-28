import pkg_resources
try:
    import unittest2 as unittest
except ImportError:
    import unittest

import mock
import mongoengine

from pulp.common import error_codes
from pulp.plugins.loader import manager
from pulp.server import exceptions
from pulp.server.db.model import ContentUnit


class ContentUnitHelper(ContentUnit):
    unit_type_id = mongoengine.StringField(default='foo')
    unit_key_fields = ('apple', 'pear')


class BadContentUnit(object):
    pass


class TestPluginManager(unittest.TestCase):

    @mock.patch.object(ContentUnitHelper, 'attach_signals')
    @mock.patch('pulp.plugins.loader.manager.pkg_resources.iter_entry_points')
    def test_load_unit_models(self, mock_entry_points_iter, mock_signals):
        """
        Test loading of the unit models entry points
        """
        req = pkg_resources.Requirement.parse('pulp-devel')
        dist = pkg_resources.working_set.find(req)
        entry_string = 'foo=unit.plugins.loader.test_manager:ContentUnitHelper'
        entry = pkg_resources.EntryPoint.parse(entry_string, dist=dist)
        mock_entry_points_iter.return_value = [entry]

        plugin_manager = manager.PluginManager()

        self.assertTrue('foo' in plugin_manager.unit_models)
        test_model = ContentUnitHelper
        found_model = plugin_manager.unit_models.get('foo')

        self.assertTrue(test_model == found_model)
        mock_signals.assert_called_once_with()

    @mock.patch('pulp.plugins.loader.manager.pkg_resources.iter_entry_points')
    def test_load_unit_models_id_reused(self, mock_entry_points_iter):
        """
        Test loading of the unit models when the same model id is used twice raises
        PLP0038
        """
        req = pkg_resources.Requirement.parse('pulp-devel')
        dist = pkg_resources.working_set.find(req)
        entry_string = 'foo=unit.plugins.loader.test_manager:ContentUnitHelper'
        entry1 = pkg_resources.EntryPoint.parse(entry_string, dist=dist)
        entry_string = 'foo=unit.plugins.loader.test_manager:ContentUnitHelper'
        entry2 = pkg_resources.EntryPoint.parse(entry_string, dist=dist)

        mock_entry_points_iter.return_value = [entry1, entry2]

        try:
            manager.PluginManager()
            self.fail("This should have raised PLP0038")
        except exceptions.PulpCodedException, e:
            self.assertEquals(e.error_code, error_codes.PLP0038)

    @mock.patch('pulp.plugins.loader.manager.pkg_resources.iter_entry_points')
    def test_load_unit_models_non_content_unit(self, mock_entry_points_iter):
        """
        Test loading of the unit models that don't subclass ContentUnit
        raise PLP0039
        """
        req = pkg_resources.Requirement.parse('pulp-devel')
        dist = pkg_resources.working_set.find(req)
        entry_string = 'foo=unit.plugins.loader.test_manager:BadContentUnit'
        entry1 = pkg_resources.EntryPoint.parse(entry_string, dist=dist)
        mock_entry_points_iter.return_value = [entry1]

        try:
            manager.PluginManager()
            self.fail("This should have raised PLP0039")
        except exceptions.PulpCodedException, e:
            self.assertEquals(e.error_code, error_codes.PLP0039)
