# -*- coding: utf-8 -*-
#
# Copyright © 2012-2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License
# (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied, including implied
# warranties of MERCHANTABILITY, NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR
# PURPOSE. You should have received a copy of GPLv2 along with this software;
# if not, see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import os
import random
import shutil
import string
import tempfile
import traceback
from pprint import pformat

import base

from pulp.server import exceptions as pulp_exceptions
from pulp.plugins.types import database as content_type_db
from pulp.plugins.types.model import TypeDefinition
from pulp.server.db.model.repository import RepoContentUnit
from pulp.server.managers import factory as manager_factory
from pulp.server.managers.content.orphan import OrphanManager

# globals and constants --------------------------------------------------------

PHONY_TYPE_1 = TypeDefinition('phony_type_1', 'Phony Type 1', None, 'name', [], [])
PHONY_TYPE_2 = TypeDefinition('phony_type_2', 'Phony Type 2', None, 'name', [], [])

PHONY_REPO_ID = 'phony_repo'
PHONY_USER_ID = 'orphan_manager_unittests'

# content generation -----------------------------------------------------------

def gen_content_unit(content_type_id, content_root, name=None):
    name = name or ''.join(random.sample(string.ascii_letters, 5))
    path = os.path.join(content_root, name)
    file = open(path, mode='w')
    file.write('')
    file.close()
    unit = {'name': name,
            '_content_type_id': content_type_id,
            '_storage_path': path}
    content_manager = manager_factory.content_manager()
    unit_id = content_manager.add_content_unit(content_type_id, None, unit)
    unit['_id'] = unit_id
    return unit


def gen_content_unit_with_directory(content_type_id, content_root, name=None):
    name = name or ''.join(random.sample(string.ascii_letters, 5))
    path = os.path.join(content_root, name)
    os.mkdir(path)
    unit = {'name': name,
            '_content_type_id': content_type_id,
            '_storage_path': path}
    content_manager = manager_factory.content_manager()
    unit_id = content_manager.add_content_unit(content_type_id, None, unit)
    unit['_id'] = unit_id
    return unit


def gen_buttload_of_content_units(content_type_id, content_root, num_units):
    unit_name_format = '%%s-%%0%dd' % len(str(num_units))
    for i in xrange(1, num_units+1):
        unit_name = unit_name_format % (content_type_id, i)
        gen_content_unit(content_type_id, content_root, unit_name)


def associate_content_unit_with_repo(content_unit):
    repo_content_unit = RepoContentUnit(PHONY_REPO_ID,
                                        content_unit['_id'],
                                        content_unit['_content_type_id'],
                                        RepoContentUnit.OWNER_TYPE_USER,
                                        PHONY_USER_ID)
    collection = RepoContentUnit.get_collection()
    collection.insert(repo_content_unit, safe=True)


def unassociate_content_unit_from_repo(content_unit):
    spec = {'unit_id': content_unit['_id']}
    collection = RepoContentUnit.get_collection()
    collection.remove(spec, safe=True)

# manager instantiation tests --------------------------------------------------

class OrphanManagerInstantiationTests(base.PulpServerTests):

    def test_constructor(self):
        try:
            OrphanManager()
        except:
            self.fail(traceback.format_exc())

    def test_factory(self):
        try:
            manager_factory.content_orphan_manager()
        except:
            self.fail(traceback.format_exc())

# manager tests ----------------------------------------------------------------

class OrphanManagerTests(base.PulpServerTests):

    def setUp(self):
        super(OrphanManagerTests, self).setUp()
        content_type_db.update_database([PHONY_TYPE_1, PHONY_TYPE_2])
        self.content_root = tempfile.mkdtemp(prefix='content_orphan_manager_unittests-')
        self.orphan_manager = OrphanManager()

    def tearDown(self):
        super(OrphanManagerTests, self).tearDown()
        RepoContentUnit.get_collection().remove(safe=True)
        content_type_db.clean()
        if os.path.exists(self.content_root): # can be removed by delete operations
            shutil.rmtree(self.content_root)

    def number_of_files_in_content_root(self):
        if not os.path.exists(self.content_root): # can be removed by delete operations
            return 0
        contents = os.listdir(self.content_root)
        return len(contents)


class OrphanManagerGeneratorTests(OrphanManagerTests):

    # utilities test methods ---------------------------------------------------

    def test_content_creation(self):
        self.assertTrue(self.number_of_files_in_content_root() == 0)
        content_unit = gen_content_unit(PHONY_TYPE_1.id, self.content_root)
        self.assertTrue(os.path.exists(content_unit['_storage_path']))
        self.assertTrue(self.number_of_files_in_content_root() == 1)

    # generator test methods ---------------------------------------------------

    def test_list_one_orphan_using_generators(self):
        orphans = list(self.orphan_manager.generate_all_orphans())
        self.assertEqual(len(orphans), 0, pformat(orphans))

        content_unit = gen_content_unit(PHONY_TYPE_1.id, self.content_root)
        orphans = list(self.orphan_manager.generate_all_orphans())
        self.assertEqual(len(orphans), 1)
        self.assertEqual(content_unit['_id'], orphans[0]['_id'])

    def test_list_two_orphans_using_generators(self):
        unit_1 = gen_content_unit(PHONY_TYPE_1.id, self.content_root)
        unit_2 = gen_content_unit(PHONY_TYPE_2.id, self.content_root)

        orphans = list(self.orphan_manager.generate_all_orphans())
        self.assertEqual(len(orphans), 2)

    def test_list_two_orphans_using_generators_with_search_indexes(self):
        unit_1 = gen_content_unit(PHONY_TYPE_1.id, self.content_root)
        unit_2 = gen_content_unit(PHONY_TYPE_2.id, self.content_root)

        orphans = list(self.orphan_manager.generate_all_orphans_with_unit_keys())
        self.assertEqual(len(orphans), 2)

    def test_list_orphans_by_type_using_generators(self):
        unit_1 = gen_content_unit(PHONY_TYPE_1.id, self.content_root)
        unit_2 = gen_content_unit(PHONY_TYPE_2.id, self.content_root)

        orphans_1 = list(self.orphan_manager.generate_orphans_by_type(PHONY_TYPE_1.id))
        self.assertEqual(len(orphans_1), 1)

        orphans_2 = list(self.orphan_manager.generate_orphans_by_type(PHONY_TYPE_2.id))
        self.assertEqual(len(orphans_2), 1)

    def test_get_orphan_using_generators(self):
        unit = gen_content_unit(PHONY_TYPE_1.id, self.content_root)

        orphan = self.orphan_manager.get_orphan(PHONY_TYPE_1.id, unit['_id'])
        self.assertEqual(orphan['_id'], unit['_id'])

    def test_get_missing_orphan_using_generators(self):
        self.assertRaises(pulp_exceptions.MissingResource,
                          self.orphan_manager.get_orphan,
                          PHONY_TYPE_1.id, 'non-existent')

    def test_associated_units_using_generators(self):
        unit = gen_content_unit(PHONY_TYPE_1.id, self.content_root)
        associate_content_unit_with_repo(unit)

        orphans = list(self.orphan_manager.generate_all_orphans())
        self.assertEqual(len(orphans), 0)

        unassociate_content_unit_from_repo(unit)
        orphans = list(self.orphan_manager.generate_all_orphans())
        self.assertEqual(len(orphans), 1)

    # delete with generator test methods ---------------------------------------

    def test_delete_one_orphan_using_generators(self):
        unit = gen_content_unit(PHONY_TYPE_1.id, self.content_root)
        orphans = list(self.orphan_manager.generate_all_orphans())
        self.assertEqual(len(orphans), 1)

        self.orphan_manager.delete_all_orphans()

        orphans = list(self.orphan_manager.generate_all_orphans())
        self.assertEqual(len(orphans), 0)
        self.assertEqual(self.number_of_files_in_content_root(), 0)

    def test_delete_one_orphan_with_directory_using_generators(self):
        unit = gen_content_unit_with_directory(PHONY_TYPE_1.id, self.content_root)
        orphans = list(self.orphan_manager.generate_all_orphans())
        self.assertEqual(len(orphans), 1)

        self.orphan_manager.delete_all_orphans()

        orphans = list(self.orphan_manager.generate_all_orphans())
        self.assertEqual(len(orphans), 0)
        self.assertEqual(self.number_of_files_in_content_root(), 0)

    # NOTE this test is disabled for normal test runs
    def _test_delete_using_generators_performance_single_content_type(self):
        num_units = 30000
        gen_buttload_of_content_units(PHONY_TYPE_1.id, self.content_root, num_units)
        self.assertEqual(self.number_of_files_in_content_root(), num_units)

        self.orphan_manager.delete_all_orphans()
        self.assertEqual(self.number_of_files_in_content_root(), 0)

    # NOTE this test is disabled for normal test runs
    def _test_delete_using_generators_performance_multiple_content_types(self):
        type_1_num_units = 15000
        type_2_num_units = 15000
        gen_buttload_of_content_units(PHONY_TYPE_1.id, self.content_root, type_1_num_units)
        gen_buttload_of_content_units(PHONY_TYPE_2.id, self.content_root, type_2_num_units)
        self.assertEqual(self.number_of_files_in_content_root(), type_1_num_units+type_2_num_units)

        self.orphan_manager.delete_all_orphans()
        self.assertEqual(self.number_of_files_in_content_root(), 0)

    def test_delete_by_type_using_generators(self):
        unit_1 = gen_content_unit(PHONY_TYPE_1.id, self.content_root)
        unit_2 = gen_content_unit(PHONY_TYPE_2.id, self.content_root)
        self.assertEqual(self.number_of_files_in_content_root(), 2)

        self.orphan_manager.delete_orphans_by_type(PHONY_TYPE_1.id)

        orphans = list(self.orphan_manager.generate_all_orphans())
        self.assertEqual(len(orphans), 1)
        self.assertFalse(os.path.exists(unit_1['_storage_path']))
        self.assertTrue(os.path.exists(unit_2['_storage_path']))

    def test_delete_by_id_using_generators(self):
        unit = gen_content_unit(PHONY_TYPE_1.id, self.content_root)

        json_obj = {'content_type_id': unit['_content_type_id'],
                    'unit_id': unit['_id']}
        self.orphan_manager.delete_orphans_by_id([json_obj])

        orphans = list(self.orphan_manager.generate_all_orphans())
        self.assertEqual(len(orphans), 0)
        self.assertEqual(self.number_of_files_in_content_root(), 0)


