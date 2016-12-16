from pprint import pformat
from unittest import TestCase
import os
import random
import shutil
import string
import tempfile
import traceback

from mock import call, patch, Mock

from .... import base
from pulp.plugins.types import database as content_type_db
from pulp.plugins.types.model import TypeDefinition
from pulp.server import exceptions as pulp_exceptions
from pulp.server.db.model.repository import RepoContentUnit
from pulp.server.managers import factory as manager_factory
from pulp.server.managers.content.orphan import OrphanManager


MODULE_PATH = 'pulp.server.managers.content.orphan.'

PHONY_TYPE_1 = TypeDefinition('phony_type_1', 'Phony Type 1', None, 'name', [], [])
PHONY_TYPE_2 = TypeDefinition('phony_type_2', 'Phony Type 2', None, 'name', [], [])

PHONY_REPO_ID = 'phony_repo'
PHONY_USER_ID = 'orphan_manager_unittests'


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
    for i in xrange(1, num_units + 1):
        unit_name = unit_name_format % (content_type_id, i)
        gen_content_unit(content_type_id, content_root, unit_name)


def associate_content_unit_with_repo(content_unit):
    repo_content_unit = RepoContentUnit(PHONY_REPO_ID,
                                        content_unit['_id'],
                                        content_unit['_content_type_id'])
    collection = RepoContentUnit.get_collection()
    collection.insert(repo_content_unit)


def unassociate_content_unit_from_repo(content_unit):
    spec = {'unit_id': content_unit['_id']}
    collection = RepoContentUnit.get_collection()
    collection.remove(spec)


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


class OrphanManagerTests(base.PulpServerTests):

    def setUp(self):
        super(OrphanManagerTests, self).setUp()
        content_type_db.update_database([PHONY_TYPE_1, PHONY_TYPE_2])
        self.content_root = tempfile.mkdtemp(prefix='content_orphan_manager_unittests-')
        self.orphan_manager = OrphanManager()

    def tearDown(self):
        super(OrphanManagerTests, self).tearDown()
        RepoContentUnit.get_collection().remove()
        content_type_db.clean()
        if os.path.exists(self.content_root):  # can be removed by delete operations
            shutil.rmtree(self.content_root)

    def number_of_files_in_content_root(self):
        if not os.path.exists(self.content_root):  # can be removed by delete operations
            return 0
        contents = os.listdir(self.content_root)
        return len(contents)


class OrphanManagerGeneratorTests(OrphanManagerTests):

    def test_content_creation(self):
        self.assertTrue(self.number_of_files_in_content_root() == 0)
        content_unit = gen_content_unit(PHONY_TYPE_1.id, self.content_root)
        self.assertTrue(os.path.exists(content_unit['_storage_path']))
        self.assertTrue(self.number_of_files_in_content_root() == 1)

    def test_list_one_orphan_using_generators(self):
        orphans = list(self.orphan_manager.generate_all_orphans())
        self.assertEqual(len(orphans), 0, pformat(orphans))

        content_unit = gen_content_unit(PHONY_TYPE_1.id, self.content_root)
        orphans = list(self.orphan_manager.generate_all_orphans())
        self.assertEqual(len(orphans), 1)
        self.assertEqual(content_unit['_id'], orphans[0]['_id'])

    def test_list_two_orphans_using_generators(self):
        gen_content_unit(PHONY_TYPE_1.id, self.content_root)
        gen_content_unit(PHONY_TYPE_2.id, self.content_root)

        orphans = list(self.orphan_manager.generate_all_orphans())
        self.assertEqual(len(orphans), 2)

    def test_list_two_orphans_using_generators_with_search_indexes(self):
        gen_content_unit(PHONY_TYPE_1.id, self.content_root)
        gen_content_unit(PHONY_TYPE_2.id, self.content_root)

        orphans = list(self.orphan_manager.generate_all_orphans_with_unit_keys())
        self.assertEqual(len(orphans), 2)

    def test_list_orphans_by_type_using_generators(self):
        gen_content_unit(PHONY_TYPE_1.id, self.content_root)
        gen_content_unit(PHONY_TYPE_2.id, self.content_root)

        orphans_1 = list(self.orphan_manager.generate_orphans_by_type(PHONY_TYPE_1.id))
        self.assertEqual(len(orphans_1), 1)

        orphans_2 = list(self.orphan_manager.generate_orphans_by_type(PHONY_TYPE_2.id))
        self.assertEqual(len(orphans_2), 1)

    @patch('pulp.server.controllers.units.get_unit_key_fields_for_type', spec_set=True)
    def test_generate_orphans_by_type_with_unit_keys_invalid_type(self, mock_get_unit_key_fields):
        """
        Assert that when an invalid content type is passed to
        generate_orphans_by_type_with_unit_keys a MissingResource exception is raised.
        """
        # simulate the type not being found
        mock_get_unit_key_fields.side_effect = ValueError

        self.assertRaises(
            pulp_exceptions.MissingResource,
            OrphanManager.generate_orphans_by_type_with_unit_keys('Not a type').next)

    @patch('pulp.server.controllers.units.get_unit_key_fields_for_type', spec_set=True)
    def test_generate_orphans_by_type_with_unit_keys(self, mock_get_unit_key_fields):
        """
        Assert that orphans are retrieved by type with unit keys correctly
        """
        mock_get_unit_key_fields.return_value = ('id',)

        # Add two content units of different types
        unit_1 = gen_content_unit(PHONY_TYPE_1.id, self.content_root)
        gen_content_unit(PHONY_TYPE_2.id, self.content_root)

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

    def test_delete_one_orphan_using_generators(self):
        gen_content_unit(PHONY_TYPE_1.id, self.content_root)
        orphans = list(self.orphan_manager.generate_all_orphans())
        self.assertEqual(len(orphans), 1)

        result = self.orphan_manager.delete_all_orphans()

        orphans = list(self.orphan_manager.generate_all_orphans())
        self.assertEqual(len(orphans), 0)
        self.assertEqual(self.number_of_files_in_content_root(), 0)
        self.assertEqual(1, result[PHONY_TYPE_1.id])

    def test_delete_one_orphan_with_directory_using_generators(self):
        gen_content_unit_with_directory(PHONY_TYPE_1.id, self.content_root)
        orphans = list(self.orphan_manager.generate_all_orphans())
        self.assertEqual(len(orphans), 1)

        result = self.orphan_manager.delete_all_orphans()

        orphans = list(self.orphan_manager.generate_all_orphans())
        self.assertEqual(len(orphans), 0)
        self.assertEqual(self.number_of_files_in_content_root(), 0)
        self.assertEqual(1, result[PHONY_TYPE_1.id])

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
        self.assertEqual(self.number_of_files_in_content_root(),
                         type_1_num_units + type_2_num_units)

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

    @patch(MODULE_PATH + 'model.LazyCatalogEntry.objects')
    def test_delete_by_id_using_generators(self, mock_lazy_catalog_objects):
        unit = gen_content_unit(PHONY_TYPE_1.id, self.content_root)

        json_obj = {'content_type_id': unit['_content_type_id'],
                    'unit_id': unit['_id']}
        self.orphan_manager.delete_orphans_by_id([json_obj])

        orphans = list(self.orphan_manager.generate_all_orphans())
        self.assertEqual(len(orphans), 0)
        self.assertEqual(self.number_of_files_in_content_root(), 0)
        mock_lazy_catalog_objects.assert_called_once_with(
            unit_id=unit['_id'],
            unit_type_id=unit['_content_type_id']
        )
        mock_lazy_catalog_objects.return_value.delete.assert_called_once_with()

    @patch(MODULE_PATH + 'model.LazyCatalogEntry.objects')
    @patch(MODULE_PATH + 'OrphanManager.delete_orphaned_file')
    @patch(MODULE_PATH + 'model.RepositoryContentUnit.objects')
    @patch(MODULE_PATH + 'plugin_api.get_unit_model_by_id')
    def test_delete_content_unit_by_type(
            self, m_get_model, m_rcu_objects, m_del_orphan, mock_lazy_catalog_objects):
        orphan = Mock(_storage_path='test_foo_path', id='orphan')
        non_orphan = Mock(_storage_path='test_foo_path', id='non_orphan')
        m_get_model.return_value.objects.only.return_value = [
            orphan,
            non_orphan
        ]
        m_rcu_objects.return_value.distinct.return_value = ['non_orphan']

        self.orphan_manager.delete_orphan_content_units_by_type('foo_type')
        mock_lazy_catalog_objects.assert_called_once_with(
            unit_id='orphan',
            unit_type_id='foo_type'
        )
        mock_lazy_catalog_objects.return_value.delete.assert_called_once_with()
        m_del_orphan.assert_called_once_with('test_foo_path')

    @patch(MODULE_PATH + 'plugin_api.get_unit_model_by_id')
    def test_delete_content_unit_by_type_filtered(self, mock_get_model):
        mock_get_model.return_value.objects.return_value.only.return_value = []

        self.orphan_manager.delete_orphan_content_units_by_type('foo_type',
                                                                content_unit_ids=['orphan2'])
        mock_get_model.return_value.objects.assert_called_once_with(id__in=('orphan2',))


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


@patch('os.path.lexists')
@patch('os.rmdir')
@patch('pulp.server.managers.content.orphan.pulp_config.config')
@patch('pulp.server.managers.content.orphan.OrphanManager.delete')
@patch('pulp.server.managers.content.orphan.OrphanManager.unlink_shared')
@patch('pulp.server.managers.content.orphan.OrphanManager.is_shared')
class TestDeleteOrphanedFile(TestCase):

    def test_not_absolute_path(self, is_shared, unlink_shared, delete, config, rmdir, lexists):
        lexists.return_value = True
        self.assertRaises(ValueError, OrphanManager.delete_orphaned_file, 'path-1')

    def test_path_not_exists(self, is_shared, unlink_shared, delete, config, rmdir, lexists):
        lexists.return_value = False
        path = '/tmp/path-1'

        # test
        OrphanManager.delete_orphaned_file(path)

        # validation
        lexists.assert_called_once_with(path)
        self.assertFalse(is_shared.called)
        self.assertFalse(delete.called)
        self.assertFalse(rmdir.called)
        self.assertFalse(unlink_shared.called)

    def test_shared(self, is_shared, unlink_shared, delete, config, rmdir, lexists):
        path = '/path-1'
        storage_dir = '/storage/pulp/dir'
        is_shared.return_value = True
        config.get.return_value = storage_dir
        lexists.return_value = True

        # test
        OrphanManager.delete_orphaned_file(path)

        # validation
        is_shared.assert_called_once_with(storage_dir, path)
        unlink_shared.assert_called_once_with(path)
        self.assertFalse(delete.called)

    def test_not_shared(self, is_shared, unlink_shared, delete, config, rmdir, lexists):
        path = '/path-1'
        storage_dir = '/storage/pulp/dir'
        is_shared.return_value = False
        config.get.return_value = storage_dir
        lexists.return_value = True

        # test
        OrphanManager.delete_orphaned_file(path)

        # validation
        is_shared.assert_called_once_with(storage_dir, path)
        delete.assert_called_once_with(path)
        self.assertFalse(unlink_shared.called)

    @patch('pulp.server.managers.content.orphan.os.access')
    @patch('pulp.server.managers.content.orphan.os.listdir')
    def test_clean_non_root(
            self,
            listdir,
            access,
            is_shared,
            unlink_shared,
            delete,
            config,
            rmdir,
            lexists):
        """
        Ensure that empty directories more than 1 level up from root are removed.
        """
        listdir.return_value = None
        access.return_value = True
        path = '/storage/pulp/content/test/lvl1/lvl2/thing.remove'
        storage_dir = '/storage/pulp'
        is_shared.return_value = False
        config.get.return_value = storage_dir
        lexists.return_value = True

        OrphanManager.delete_orphaned_file(path)
        rmdir.assert_has_calls(
            [
                call('/storage/pulp/content/test/lvl1/lvl2'),
                call('/storage/pulp/content/test/lvl1')
            ])

    @patch('pulp.server.managers.content.orphan.os.access')
    @patch('pulp.server.managers.content.orphan.os.listdir')
    def test_clean_nonempty(
            self,
            listdir,
            access,
            is_shared,
            unlink_shared,
            delete,
            config,
            rmdir,
            lexists):
        """
        Ensure that nonempty directories are not removed.
        """
        listdir.return_value = ['some', 'files']
        access.return_value = True
        path = '/storage/pulp/content/test/lvl1/lvl2/thing.remove'
        storage_dir = '/storage/pulp'
        is_shared.return_value = False
        config.get.return_value = storage_dir
        lexists.return_value = True

        OrphanManager.delete_orphaned_file(path)
        self.assertFalse(rmdir.called)

    @patch('pulp.server.managers.content.orphan.os.access')
    @patch('pulp.server.managers.content.orphan.os.listdir')
    def test_clean_no_access(
            self,
            listdir,
            access,
            is_shared,
            unlink_shared,
            delete,
            config,
            rmdir,
            lexists):
        """
        Ensure that rmdir is not called when user does not have access to dir.
        """
        listdir.return_value = None
        access.return_value = False
        path = '/storage/pulp/content/test/lvl1/lvl2/thing.remove'
        storage_dir = '/storage/pulp'
        is_shared.return_value = False
        config.get.return_value = storage_dir
        lexists.return_value = True

        OrphanManager.delete_orphaned_file(path)
        self.assertFalse(rmdir.called)
