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
import sys
import tempfile
import traceback

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../common')))

import testutil

from pulp.server.content import manager
from pulp.server.content.distributor.base import Distributor
from pulp.server.content.importer.base import Importer

# test data and data generation api --------------------------------------------

# delete the generated data

_generated_paths = []

def _delete_generated_paths():
    for p in _generated_paths:
        if p in sys.path:
            sys.path.remove(p)
        shutil.rmtree(p)

atexit.register(_delete_generated_paths)

# test data

excellent_importer = '''
from pulp.server.content.importer import base
class ExcellentImporter(base.Importer):
    @classmethod
    def metadata(cls):
        data = {'name': 'Excellent',
                'version': 1,
                'types': ['excellent_type'],
                'conf_file': 'excellent.conf'}
        return data
'''

less_excellent_importer = '''
from pulp.server.content.importer import base
class LessExcellentImporter(base.Importer):
    @classmethod
    def metadata(cls):
        data = {'name': 'Excellent',
                'version': 0,
                'types': ['excellent_type']}
        return data
'''

not_excellent_importer = '''
from pulp.server.content.importer import base
class NotExcellentImporter(base.Importer):
    @classmethod
    def metadata(cls):
        data = {'name': 'Excellent',
                'version': 1,
                'types': ['excellent_type']}
        return data
'''

bogus_importer_1 = '''
from pulp.server.content.importer import base
class BogusOneImporter(base.Importer):
    @classmethod
    def metadata(cls):
        return {}
'''

bogus_importer_2 = '''
from pulp.server.content.importer import base
class BogusTwoImporter(base.Importer):
    @classmethod
    def metadata(cls):
        return None
'''

excellent_importer_config_1 = '''
[Excellent]
enabled = true
'''

excellent_importer_config_2 = '''
[Excellent]
enabled = false
'''

http_distibutor = '''
from pulp.server.content.distributor import base
class HTTPDistributor(base.Distributor):
    @classmethod
    def metadata(cls):
        data = {'name': 'HTTP',
                'version': 1.1,
                'types': ['http', 'https'],
                'conf_file': 'http.conf'}
        return data
'''

http_conf = '''
[HTTPDistributor]
enabled: yes
'''

# test file(s) generation

def gen_excellent_importer(enabled=True):
    path = tempfile.mkdtemp()
    sys.path.insert(0, path)
    _generated_paths.append(path)
    mod_handle = open(os.path.join(path, 'excellent.py'), 'w')
    mod_handle.write(excellent_importer)
    mod_handle.close()
    cfg_handle = open(os.path.join(path, 'excellent.conf'), 'w')
    if enabled:
        cfg_handle.write(excellent_importer_config_1)
    else:
        cfg_handle.write(excellent_importer_config_2)
    cfg_handle.close()
    return path


def gen_less_excellent_importer():
    path = tempfile.mkdtemp()
    sys.path.insert(0, path)
    _generated_paths.append(path)
    handle = open(os.path.join(path, 'less_excellent.py'), 'w')
    handle.write(less_excellent_importer)
    handle.close()
    return path


def gen_not_excellent_importer():
    path = tempfile.mkdtemp()
    sys.path.insert(0, path)
    _generated_paths.append(path)
    handle = open(os.path.join(path, 'not_excellent.py'), 'w')
    handle.write(not_excellent_importer)
    handle.close()
    return path


def gen_bogus_importer(version=1):
    path = tempfile.mkdtemp()
    sys.path.insert(0, path)
    _generated_paths.append(path)
    handle = open(os.path.join(path, 'bogus_%d.py' % version), 'w')
    if version == 1:
        handle.write(bogus_importer_1)
    elif version == 2:
        handle.write(bogus_importer_2)
    else:
        raise Exception('Are you kidding me?')
    handle.close()
    return path


def gen_http_distributor():
    path = tempfile.mkdtemp()
    sys.path.insert(0, path)
    _generated_paths.append(path)
    mod_handle = open(os.path.join(path, 'http_distributor.py'), 'w')
    mod_handle.write(http_distibutor)
    mod_handle.close()
    cfg_handle = open(os.path.join(path, 'http_distributor.conf'), 'w')
    cfg_handle.write(http_conf)
    cfg_handle.close()
    return path

# unit tests -------------------------------------------------------------------

class ManagerInstanceTest(testutil.PulpTest):

    def test_manager_instantiation(self):
        try:
            m = manager.Manager()
        except Exception, e:
            self.fail('\n'.join((repr(e), traceback.format_exc())))


class ManagerTest(testutil.PulpTest):

    def setUp(self):
        super(ManagerTest, self).setUp()
        self.manager = manager.Manager()

    def tearDown(self):
        super(ManagerTest, self).tearDown()
        self.manager = None


class ManagerPathTest(ManagerTest):

    def test_add_valid_path(self):
        path = tempfile.mkdtemp()
        _generated_paths.append(path)
        self.manager.add_importer_plugin_path(path)
        self.assertTrue(path in self.manager.importer_plugin_paths)
        self.manager.add_importer_config_path(path)
        self.assertTrue(path in self.manager.importer_config_paths)
        self.manager.add_distributor_plugin_path(path)
        self.assertTrue(path in self.manager.distributor_plugin_paths)
        self.manager.add_distributor_config_path(path)
        self.assertTrue(path in self.manager.distributor_config_paths)

    def test_non_existent_path(self):
        non_existent = tempfile.mkdtemp()
        os.rmdir(non_existent)
        self.assertRaises(ValueError, self.manager.add_importer_plugin_path, non_existent)

    def test_bad_permissions_path(self):
        cant_read = tempfile.mkdtemp()
        os.chmod(cant_read, 0300)
        self.assertRaises(ValueError, self.manager.add_distributor_plugin_path, cant_read)
        os.rmdir(cant_read)


class ManagerLoadTest(ManagerTest):

    def test_enabled_importer(self):
        path = gen_excellent_importer(enabled=True)
        self.manager.add_importer_plugin_path(path)
        self.manager.add_importer_config_path(path)
        self.manager.load_importers()
        self.assertTrue('Excellent' in self.manager.importer_plugins)
        self.assertTrue('Excellent' in self.manager.importer_configs)

    def test_disabled_importer(self):
        path = gen_excellent_importer(enabled=False)
        self.manager.add_importer_plugin_path(path)
        self.manager.add_importer_config_path(path)
        self.manager.load_importers()
        self.assertFalse('Excellent' in self.manager.importer_plugins)
        self.assertFalse('Excellent' in self.manager.importer_configs)

    def test_multiple_importers(self):
        path = gen_excellent_importer()
        self.manager.add_importer_plugin_path(path)
        self.manager.add_importer_config_path(path)
        path = gen_less_excellent_importer()
        self.manager.add_importer_plugin_path(path)
        self.manager.add_importer_config_path(path)
        self.manager.load_importers()
        self.assertTrue(len(self.manager.importer_plugins['Excellent']) == 2)

    def test_conflicting_excellent_importers(self):
        path = gen_excellent_importer(enabled=True)
        self.manager.add_importer_plugin_path(path)
        self.manager.add_importer_config_path(path)
        path = gen_not_excellent_importer()
        self.manager.add_importer_plugin_path(path)
        self.manager.add_importer_config_path(path)
        self.assertRaises(manager.ConflictingPluginError, self.manager.load_importers)

    def test_missing_metadata_plugin(self):
        path = gen_bogus_importer(version=1)
        self.manager.add_importer_plugin_path(path)
        self.assertRaises(manager.MalformedPluginError, self.manager.load_importers)

    def test_malformed_metadata_plugin(self):
        path = gen_bogus_importer(version=2)
        self.manager.add_importer_plugin_path(path)
        self.assertRaises(manager.MalformedPluginError, self.manager.load_importers)

    def test_distributor(self):
        path = gen_http_distributor()
        self.manager.add_distributor_plugin_path(path)
        self.manager.add_distributor_config_path(path)
        self.manager.load_distributors()
        self.assertTrue('HTTP' in self.manager.distributor_plugins)
        self.assertTrue('HTTP' in self.manager.distributor_configs)


class ManagerAPITest(ManagerTest):

    def test_get_importer(self):
        path = gen_excellent_importer()
        self.manager.add_importer_plugin_path(path)
        self.manager.add_importer_config_path(path)
        self.manager.load_importers()
        manager._MANAGER = self.manager
        importer = manager.get_importer_by_name('Excellent')
        self.assertTrue(isinstance(importer, Importer))

    def test_get_non_existent_importer(self):
        manager._MANAGER = self.manager
        importer = manager.get_distributor_by_name('Bogus')
        self.assertTrue(importer is None)

    def test_get_distributor(self):
        path = gen_http_distributor()
        self.manager.add_distributor_plugin_path(path)
        self.manager.add_distributor_config_path(path)
        self.manager.load_distributors()
        manager._MANAGER = self.manager
        distributor = manager.get_distributor_by_name('HTTP')
        self.assertTrue(distributor, Distributor)

    def test_get_non_existent_distributor(self):
        manager._MANAGER = self.manager
        distributor = manager.get_distributor_by_name('HTTPS')
        self.assertTrue(distributor is None)
