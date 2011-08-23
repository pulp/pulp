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

import os
import shutil
import sys
import tempfile
import traceback

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../common')))

import testutil

from pulp.server.content import manager

# test data and data generation api --------------------------------------------

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
[ExcellentImporter]
enabled = true
'''

excellent_importer_config_2 = '''
[ExcellentImporter]
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

def gen_excellent_importer(enabled=True):
    path = tempfile.mkdtemp()
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
    mod_handle = open(os.path.join(path, 'less.py'), 'w')
    mod_handle.write(less_excellent_importer)
    mod_handle.close()
    return path

def gen_bogus_importer(version=1):
    path = tempfile.mkdtemp()
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
    mod_handle = open(os.path.join(path, 'http.py'), 'w')
    mod_handle.write(http_distibutor)
    mod_handle.close()
    cfg_handle = open(os.path.join(path, 'http.conf'), 'w')
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


class ManagerPathTest(testutil.PulpTest):

    def setUp(self):
        super(ManagerPathTest, self).setUp()
        self.manager = manager.Manager()

    def tearDown(self):
        super(ManagerPathTest, self).tearDown()
        self.manager = None

    def test_add_valid_path(self):
        path = tempfile.mkdtemp()
        self.manager.add_importer_plugin_path(path)
        self.assertTrue(path in self.manager.importer_plugin_paths)
        self.manager.add_importer_config_path(path)
        self.assertTrue(path in self.manager.importer_config_paths)
        self.manager.add_distributor_plugin_path(path)
        self.assertTrue(path in self.manager.distributor_plugin_paths)
        self.manager.add_distributor_config_path(path)
        self.assertTrue(path in self.manager.distributor_config_paths)
        os.rmdir(path)

    def test_add_invalid_path(self):
        non_existent = '/asdf/jkl'
        cant_read = '/root'
        self.assertRaises(ValueError, self.manager.add_importer_plugin_path, non_existent)
        self.assertRaises(ValueError, self.manager.add_distributor_plugin_path, cant_read)


class ManagerLoadTest(ManagerPathTest):

    def test_enabled_excellent_importer(self):
        path = gen_excellent_importer(enabled=True)
        self.manager.add_importer_plugin_path(path)
        self.manager.add_importer_config_path(path)
        self.manager.load_importers()
        self.assertTrue('ExcellentImporter' in self.manager.importer_plugins)
        self.assertTrue('ExcellentImporter' in self.manager.importer_configs)
        shutil.rmtree(path)