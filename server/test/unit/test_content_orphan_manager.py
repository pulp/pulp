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
from unittest import TestCase

from mock import patch

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

    def test_generate_orphans_by_type_with_unit_keys_invalid_type(self):
        """
        Assert that when an invalid content type is passed to generate_orphans_by_type_with_unit_keys
        a MissingResource exception is raised.
        """

        self.assertRaises(pulp_exceptions.MissingResource,
                          OrphanManager.generate_orphans_by_type_with_unit_keys('Not a type').next
                          )

    def test_generate_orphans_by_type_with_unit_keys(self):
        """
        Assert that orphans are retrieved by type with unit keys correctly
        """
        # Add two content units of different types
        unit_1 = gen_content_unit(PHONY_TYPE_1.id, self.content_root)
        unit_2 = gen_content_unit(PHONY_TYPE_2.id, self.content_root)

        results = list(self.orphan_manager.generate_orphans_by_type_with_unit_keys(PHONY_TYPE_1.id))
        self.assertEqual(1, len(results))
        self.assertEqual(unit_1['_content_type_id'], results[0]['_content_type_id'])

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


class TestDelete(TestCase):

    @patch('shutil.rmtree')
    @patch('os.unlink')
    @patch('os.path.islink')
    @patch('os.path.isfile')
    def test_delete_dir(self, is_file, is_link, unlink, rmtree):
        path = 'path-1'
        is_file.return_value = False
        is_link.return_value = False

        # test
        OrphanManager.delete(path)

        # validation
        is_file.assert_called_with(path)
        is_link.assert_called_with(path)
        rmtree.assert_called_with(path)
        self.assertFalse(unlink.called)

    @patch('shutil.rmtree')
    @patch('os.unlink')
    @patch('os.path.isfile')
    def test_delete_file(self, is_file, unlink, rmtree):
        path = 'path-1'
        is_file.return_value = True

        # test
        OrphanManager.delete(path)

        # validation
        is_file.assert_called_with(path)
        unlink.assert_called_with(path)
        self.assertFalse(rmtree.called)

    @patch('shutil.rmtree')
    @patch('os.unlink')
    @patch('os.path.islink')
    @patch('os.path.isfile')
    def test_delete_link(self, is_file, is_link, unlink, rmtree):
        path = 'path-1'
        is_file.return_value = False
        is_link.return_value = True

        # test
        OrphanManager.delete(path)

        # validation
        is_file.assert_called_with(path)
        is_link.assert_called_with(path)
        unlink.assert_called_with(path)
        self.assertFalse(rmtree.called)

    @patch('logging.Logger.error')
    @patch('os.unlink')
    @patch('os.path.isdir')
    def test_delete_exception(self, is_dir, unlink, log_error):
        path = 'path-1'
        is_dir.return_value = False
        unlink.side_effect = OSError

        # test
        OrphanManager.delete(path)

        # validation
        self.assertTrue(log_error.called)


class TestIsShared(TestCase):

    @patch('os.path.islink')
    def test_shared(self, is_link):
        storage_dir = '/var/lib/pulp'
        path = os.path.join(storage_dir, 'content/shared/repo-id/links/link-1')
        is_link.return_value = True

        # test
        shared = OrphanManager.is_shared(storage_dir, path)

        # validation
        self.assertTrue(shared)

    @patch('os.path.islink')
    def test_not_shared(self, is_link):
        storage_dir = '/var/lib/pulp'
        path = os.path.join(storage_dir, 'content/repo-id/links/link-1')
        is_link.return_value = True

        # test
        shared = OrphanManager.is_shared(storage_dir, path)

        # validation
        self.assertFalse(shared)

    @patch('os.path.islink')
    def test_not_link(self, is_link):
        storage_dir = '/var/lib/pulp'
        path = os.path.join(storage_dir, 'content/shared/repo-id/links/link-1')
        is_link.return_value = False

        # test
        shared = OrphanManager.is_shared(storage_dir, path)

        # validation
        self.assertFalse(shared)

    @patch('os.path.islink')
    def test_not_links_dir(self, is_link):
        storage_dir = '/var/lib/pulp'
        path = os.path.join(storage_dir, 'content/shared/repo-id/OTHER/link-1')
        is_link.return_value = True

        # test
        shared = OrphanManager.is_shared(storage_dir, path)

        # validation
        self.assertFalse(shared)


class TestUnlinkShared(TestCase):

    @patch('os.listdir')
    @patch('os.readlink')
    @patch('pulp.server.managers.content.orphan.OrphanManager.delete')
    def test_delete_all(self, delete, read_link, listdir):
        path = '/parent/links/path-1'
        content = '/parent/content'
        read_link.return_value = content
        listdir.return_value = []

        # test
        OrphanManager.unlink_shared(path)

        # validation
        read_link.assert_called_once_with(path)
        listdir.assert_called_once_with(os.path.dirname(path))
        self.assertEqual(
            delete.call_args_list,
            [
                ((path,), {}),
                ((content,), {}),
            ])

    @patch('os.listdir')
    @patch('os.readlink')
    @patch('pulp.server.managers.content.orphan.OrphanManager.delete')
    def test_delete_links_not_empty(self, delete, read_link, listdir):
        path = '/parent/links/path-1'
        content = '/parent/content'
        read_link.return_value = content
        listdir.return_value = ['link-2']

        # test
        OrphanManager.unlink_shared(path)

        # validation
        read_link.assert_called_once_with(path)
        listdir.assert_called_once_with(os.path.dirname(path))
        delete.assert_called_once_with(path)

    @patch('os.listdir')
    @patch('os.readlink')
    @patch('pulp.server.managers.content.orphan.OrphanManager.delete')
    def test_delete_target_not_sibling(self, delete, read_link, listdir):
        path = '/parent/links/path-1'
        content = '/NOT-SAME-PARENT/content'
        read_link.return_value = content
        listdir.return_value = []

        # test
        OrphanManager.unlink_shared(path)

        # validation
        read_link.assert_called_once_with(path)
        listdir.assert_called_once_with(os.path.dirname(path))
        delete.assert_called_once_with(path)


class TestDeleteOrphanedFile(TestCase):

    def test_not_absolute_path(self):
        self.assertRaises(ValueError, OrphanManager.delete_orphaned_file, 'path-1')

    @patch('pulp.server.managers.content.orphan.pulp_config.config')
    @patch('pulp.server.managers.content.orphan.OrphanManager.delete')
    @patch('pulp.server.managers.content.orphan.OrphanManager.unlink_shared')
    @patch('pulp.server.managers.content.orphan.OrphanManager.is_shared')
    def test_shared(self, is_shared, unlink_shared, delete, config):
        path = '/path-1'
        storage_dir = '/storage/pulp/dir'
        is_shared.return_value = True
        config.get.return_value = storage_dir

        # test
        OrphanManager.delete_orphaned_file(path)

        # validation
        is_shared.assert_called_once_with(storage_dir, path)
        unlink_shared.assert_called_once_with(path)
        self.assertFalse(delete.called)

    @patch('pulp.server.managers.content.orphan.pulp_config.config')
    @patch('pulp.server.managers.content.orphan.OrphanManager.delete')
    @patch('pulp.server.managers.content.orphan.OrphanManager.unlink_shared')
    @patch('pulp.server.managers.content.orphan.OrphanManager.is_shared')
    def test_not_shared(self, is_shared, unlink_shared, delete, config):
        path = '/path-1'
        storage_dir = '/storage/pulp/dir'
        is_shared.return_value = False
        config.get.return_value = storage_dir

        # test
        OrphanManager.delete_orphaned_file(path)

        # validation
        is_shared.assert_called_once_with(storage_dir, path)
        delete.assert_called_once_with(path)
        self.assertFalse(unlink_shared.called)
