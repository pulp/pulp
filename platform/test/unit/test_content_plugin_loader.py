# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import atexit
import os
import shutil
import string
import sys
import traceback
import tempfile
from pprint import pprint

import base

from pulp.plugins.loader import exceptions, loading, manager
from pulp.plugins.distributor import Distributor
from pulp.plugins.importer import Importer
from pulp.plugins.profiler import Profiler

# test data and data generation api --------------------------------------------

_generated_paths = []

def _delete_generated_paths():
    for p in _generated_paths:
        if p in sys.path:
            sys.path.remove(p)
        shutil.rmtree(p)


atexit.register(_delete_generated_paths)

# test file(s) generation

def gen_plugin_root():
    path = tempfile.mkdtemp()
    sys.path.insert(0, path)
    _generated_paths.append(path)
    return path


_PLUGIN_TEMPLATE = string.Template('''
from pulp.plugins.$BASE_NAME import $BASE_TITLE
class $PLUGIN_TITLE($BASE_TITLE):
    @classmethod
    def metadata(cls):
        data = {'id': '$PLUGIN_NAME',
                'types': $TYPE_LIST}
        return data
''')

_MULTI_PLUGIN_TEMPLATE = string.Template('''
from pulp.plugins.$BASE_NAME import $BASE_TITLE

class Plugin1($BASE_TITLE):
    @classmethod
    def metadata(cls):
        data = {'id': 'plugin1',
                'types': $TYPE_LIST}
        return data

class Plugin2($BASE_TITLE):
    @classmethod
    def metadata(cls):
        data = {'id': 'plugin2',
                'types': $TYPE_LIST}
        return data

class Plugin3($BASE_TITLE):
    @classmethod
    def metadata(cls):
        data = {'id': 'plugin3',
                'types': $TYPE_LIST}
        return data

# Should not be loaded as a valid plugin since it starts with _
class _BasePlugin($BASE_TITLE):
    @classmethod
    def metadata(cls):
        data = {'id': 'base_plugin',
                'types': $TYPE_LIST}
        return data
''')

_CONF_TEMPLATE = string.Template('''
{"enabled": $ENABLED}
''')


def gen_plugin(root, type_, name, types, enabled=True):
    base_name = type_.lower()
    base_title = type_.title()
    plugin_name = name.lower()
    plugin_title = name
    type_list = '[%s]' % ', '.join('\'%s\'' % t for t in types)
    # create the directory
    plugin_dir = os.path.join(root, '%ss' % base_name, plugin_name)
    os.makedirs(plugin_dir)
    # write the package module
    pck_name = os.path.join(plugin_dir, '__init__.py')
    handle = open(pck_name, 'w')
    handle.write('\n')
    handle.close()
    # write the plugin module
    contents = _PLUGIN_TEMPLATE.safe_substitute({'BASE_NAME': base_name,
                                                 'BASE_TITLE': base_title,
                                                 'PLUGIN_TITLE': plugin_title,
                                                 'PLUGIN_NAME': plugin_name,
                                                 'TYPE_LIST': type_list})
    mod_name = os.path.join(plugin_dir, '%s.py' % base_name)
    handle = open(mod_name, 'w')
    handle.write(contents)
    handle.close()
    # write plugin config
    contents = _CONF_TEMPLATE.safe_substitute({'ENABLED': str(enabled).lower()})
    cfg_name = os.path.join(plugin_dir, '%s.conf' % plugin_name)
    handle = open(cfg_name, 'w')
    handle.write(contents)
    handle.close()
    # return the top level directory
    return os.path.join(root, '%ss' % base_name)

def gen_multi_plugin(root, type_, name, types, enabled=True):
    base_name = type_.lower()
    base_title = type_.title()
    plugin_name = name.lower()
    type_list = '[%s]' % ', '.join('\'%s\'' % t for t in types)
    # create the directory
    plugin_dir = os.path.join(root, '%ss' % base_name, plugin_name)
    os.makedirs(plugin_dir)
    # write the package module
    pck_name = os.path.join(plugin_dir, '__init__.py')
    handle = open(pck_name, 'w')
    handle.write('\n')
    handle.close()
    # write the plugin module
    contents = _MULTI_PLUGIN_TEMPLATE.safe_substitute({'BASE_NAME': base_name,
                                                 'BASE_TITLE': base_title,
                                                 'TYPE_LIST': type_list})
    mod_name = os.path.join(plugin_dir, '%s.py' % base_name)
    handle = open(mod_name, 'w')
    handle.write(contents)
    handle.close()
    # write plugin config
    contents = _CONF_TEMPLATE.safe_substitute({'ENABLED': str(enabled).lower()})
    cfg_name = os.path.join(plugin_dir, '%s.conf' % plugin_name)
    handle = open(cfg_name, 'w')
    handle.write(contents)
    handle.close()
    # return the top level directory
    return os.path.join(root, '%ss' % base_name)


# test classes

class WebDistributor(Distributor):
    @classmethod
    def metadata(cls):
        return {'types': ['http', 'https']}

class ExcellentImporter(Importer):
    @classmethod
    def metadata(cls):
        return {'types': ['excellent_type']}


class BogusImporter(Importer):
    @classmethod
    def metadata(cls):
        return {'types': ['excellent_type']}

class GoodProfiler(Importer):
    @classmethod
    def metadata(cls):
        return {'types': ['good_type']}

# unit tests -------------------------------------------------------------------

class PluginMapTests(base.PulpServerTests):

    def setUp(self):
        super(PluginMapTests, self).setUp()
        self.plugin_map = manager._PluginMap()

    def test_add_plugin(self):
        name = 'excellent'
        types = ExcellentImporter.metadata()['types']
        self.plugin_map.add_plugin(name, ExcellentImporter, {}, types)
        self.assertTrue(name in self.plugin_map.configs)
        self.assertTrue(name in self.plugin_map.plugins)

    def test_add_disabled(self):
        name = 'disabled'
        cfg = {'enabled': False}
        self.plugin_map.add_plugin(name, BogusImporter, cfg)
        self.assertFalse(name in self.plugin_map.configs)
        self.assertFalse(name in self.plugin_map.plugins)
        self.assertFalse(name in self.plugin_map.types)

    def test_conflicting_names(self):
        name = 'less_excellent'
        types = ExcellentImporter.metadata()['types']
        self.plugin_map.add_plugin(name, ExcellentImporter, {}, types)
        self.assertRaises(exceptions.ConflictingPluginName,
                          self.plugin_map.add_plugin,
                          name, BogusImporter, {}, types)

    def test_get_plugin_by_name(self):
        name = 'excellent'
        self.plugin_map.add_plugin(name, ExcellentImporter, {})
        cls = self.plugin_map.get_plugin_by_id(name)[0]
        self.assertTrue(cls is ExcellentImporter)

    def test_get_plugin_by_type(self):
        types = ExcellentImporter.metadata()['types']
        self.plugin_map.add_plugin('excellent', ExcellentImporter, {}, types)
        id = self.plugin_map.get_plugin_ids_by_type(types[0])[0]
        self.assertEqual(id, 'excellent')

    def test_name_not_found(self):
        self.assertRaises(exceptions.PluginNotFound,
                          self.plugin_map.get_plugin_by_id,
                          'bogus')

    def test_type_not_found(self):
        self.assertRaises(exceptions.PluginNotFound,
                          self.plugin_map.get_plugin_ids_by_type,
                          'bogus_type')

    def test_remove_plugin(self):
        name = 'excellent'
        self.plugin_map.add_plugin(name, ExcellentImporter, {})
        self.assertTrue(name in self.plugin_map.plugins)
        self.plugin_map.remove_plugin(name)
        self.assertFalse(name in self.plugin_map.plugins)


class LoaderInstanceTest(base.PulpServerTests):

    def test_loader_instantiation(self):
        try:
            l = manager.PluginManager()
        except Exception, e:
            self.fail('\n'.join((repr(e), traceback.format_exc())))


class LoaderTest(base.PulpServerTests):

    def setUp(self):
        super(LoaderTest, self).setUp()
        self.loader = manager.PluginManager()

    def tearDown(self):
        super(LoaderTest, self).tearDown()
        self.loader = None


class LoaderDirectOperationsTests(LoaderTest):

    def test_distributor(self):
        name = 'spidey'
        types = WebDistributor.metadata()['types']
        self.loader.distributors.add_plugin(name, WebDistributor, {}, types)

        cls = self.loader.distributors.get_plugin_by_id(name)[0]
        self.assertTrue(cls is WebDistributor)

        cls = self.loader.distributors.get_plugins_by_type(types[0])[0][0]
        self.assertTrue(cls is WebDistributor)

        cls = self.loader.distributors.get_plugins_by_type(types[1])[0][0]
        self.assertTrue(cls is WebDistributor)

        distributors = self.loader.distributors.get_loaded_plugins()
        self.assertTrue(name in distributors)

        self.loader.distributors.remove_plugin(name)
        self.assertRaises(exceptions.PluginNotFound,
                          self.loader.distributors.get_plugin_by_id,
                          name)

    def test_importer(self):
        name = 'bill'
        types = ExcellentImporter.metadata()['types']
        self.loader.importers.add_plugin(name, ExcellentImporter, {}, types)

        cls = self.loader.importers.get_plugin_by_id(name)[0]
        self.assertTrue(cls is ExcellentImporter)

        cls = self.loader.importers.get_plugins_by_type(types[0])[0][0]
        self.assertTrue(cls is ExcellentImporter)

        importers = self.loader.importers.get_loaded_plugins()
        self.assertTrue(name in importers)

        self.loader.importers.remove_plugin(name)
        self.assertRaises(exceptions.PluginNotFound,
                          self.loader.importers.get_plugin_by_id,
                          name)

    def test_profiler(self):
        name = 'elmer'
        types = GoodProfiler.metadata()['types']
        self.loader.profilers.add_plugin(name, GoodProfiler, {}, types)

        cls = self.loader.profilers.get_plugin_by_id(name)[0]
        self.assertTrue(cls is GoodProfiler)

        cls = self.loader.profilers.get_plugins_by_type(types[0])[0][0]
        self.assertTrue(cls is GoodProfiler)

        profilers = self.loader.profilers.get_loaded_plugins()
        self.assertTrue(name in profilers)

        self.loader.profilers.remove_plugin(name)
        self.assertRaises(exceptions.PluginNotFound,
                          self.loader.profilers.get_plugin_by_id,
                          name)


class LoaderFileSystemOperationsTests(LoaderTest):

    def test_single_distributor(self):
        plugin_root = gen_plugin_root()
        types = ['test_type']
        distributors_root = gen_plugin(plugin_root,
                                       'distributor',
                                       'TestDistributor',
                                       types)
        loading.load_plugins_from_path(distributors_root, Distributor, self.loader.distributors)
        try:
            cls, cfg = self.loader.distributors.get_plugin_by_id('testdistributor')
        except Exception, e:
            print 'plugin root: %s' % plugin_root
            print 'plugins: ',
            pprint(self.loader.distributors.plugins)
            print 'configs: ',
            pprint(self.loader.distributors.configs)
            print 'types: ',
            pprint(self.loader.distributors.types)
            self.fail('\n'.join((repr(e), traceback.format_exc())))

    def test_single_importer_with_query(self):
        plugin_root = gen_plugin_root()
        types = ['test_type']
        importers_root = gen_plugin(plugin_root,
                                    'importer',
                                    'TestImporter',
                                    types)
        loading.load_plugins_from_path(importers_root, Importer, self.loader.importers)
        cls, cfg = self.loader.importers.get_plugins_by_type(types[0])[0]
        self.assertTrue(issubclass(cls, Importer))

    def test_multiple_distributors(self):
        plugin_root = gen_plugin_root()
        distributors_root_1 = gen_plugin(plugin_root,
                                         'distributor',
                                         'FooDistributor',
                                         ['foo'])
        distributors_root_2 = gen_plugin(plugin_root,
                                         'distributor',
                                         'BarDistributor',
                                         ['bar'])
        distributors_root_3 = gen_plugin(plugin_root,
                                         'distributor',
                                         'BazDistributor',
                                         ['baz'])
        self.assertEqual(distributors_root_1,
                         distributors_root_2,
                         distributors_root_3)
        loading.load_plugins_from_path(distributors_root_1, Distributor, self.loader.distributors)

        cls_1 = self.loader.distributors.get_plugin_by_id('foodistributor')[0]
        self.assertTrue(issubclass(cls_1, Distributor))

        cls_2 = self.loader.distributors.get_plugins_by_type('bar')[0][0]
        self.assertTrue(issubclass(cls_2, Distributor))

        cls_3 = self.loader.distributors.get_plugin_by_id('bazdistributor')[0]
        self.assertTrue(issubclass(cls_3, Distributor))

    def test_multiple_importers_per_plugin(self):
        """
        Tests a single plugin that contains multiple importers.
        """

        # Setup
        plugin_root = gen_plugin_root()
        imp_root = gen_multi_plugin(plugin_root, 'importer', 'MultiImporter', ['foo'])

        # Test
        loading.load_plugins_from_path(imp_root, Importer, self.loader.importers)

        # Verify
        loaded = self.loader.importers.get_loaded_plugins()
        self.assertEqual(3, len(loaded))


    def test_multiple_with_disabled(self):
        plugin_root = gen_plugin_root()
        distributors_root = gen_plugin(plugin_root,
                                       'distributor',
                                       'MyDistributor',
                                       ['test_distribution'])
        importer_root_1 = gen_plugin(plugin_root,
                                     'importer',
                                     'EnabledImporter',
                                     ['test_importer'])
        importer_root_2 = gen_plugin(plugin_root,
                                     'importer',
                                     'DisabledImporter',
                                     ['test_importer'],
                                     enabled=False)
        self.assertEqual(importer_root_1, importer_root_2)
        loading.load_plugins_from_path(distributors_root, Distributor, self.loader.distributors)
        loading.load_plugins_from_path(importer_root_1, Importer, self.loader.importers)

        distributor_cls = self.loader.distributors.get_plugin_by_id('mydistributor')[0]
        self.assertTrue(issubclass(distributor_cls, Distributor))

        importer_cls = self.loader.importers.get_plugins_by_type('test_importer')[0][0]
        self.assertEqual(importer_cls.__name__, 'EnabledImporter')

        self.assertRaises(exceptions.PluginNotFound,
                          self.loader.importers.get_plugin_by_id,
                          'disabledimporter')
