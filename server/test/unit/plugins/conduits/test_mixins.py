import unittest

from pymongo.errors import DuplicateKeyError
import mock
import mongoengine

from ... import base
from pulp.devel import mock_plugins
from pulp.plugins.conduits import mixins
from pulp.plugins.model import Unit, PublishReport
from pulp.server import constants
from pulp.server import exceptions as pulp_exceptions
from pulp.server.db import model
from pulp.server.exceptions import MissingResource
from pulp.server.managers import factory as manager_factory
from pulp.server.managers.repo.distributor import RepoDistributorManager
from pulp.server.managers.repo.importer import RepoImporterManager
import pulp.plugins.types.database as types_database


def _create_mock_side_effect(items):
    """
    This adds a behavior to older mock versions, that is present in mock 1.0.
    If you pass an iterable to the side_effect parameter of mock.Mock, each call
    to that mock will grab the first item in the iterable. If it is an exception,
    it will be raised. If not, it will be returned. Older versions of mock don't
    do the exception inspection, so this adds that feature.

    :param items:   list of return values and/or exceptions. Each exception will
                    be raised. Each other item will be returned.
    :type  items:   list

    :return:    a function that can be used as the "side_effect" argument to Mock
    :rtype:     function
    """
    def _side_effect(*args, **kwargs):
        ret = items.pop(0)
        try:
            if isinstance(ret, Exception) or issubclass(ret, Exception):
                raise ret
        # issubclass will complain if you try to check something that isn't a
        # class. In our case, we don't care.
        except TypeError:
            pass
        return ret
    return _side_effect


class DistributorScratchpadMixinTests(base.PulpServerTests):

    def clean(self):
        super(DistributorScratchpadMixinTests, self).clean()
        types_database.clean()
        model.Repository.drop_collection()

    @mock.patch('pulp.server.managers.repo._common.get_working_directory',
                return_value="/var/cache/pulp/mock_worker/mock_task_id")
    def setUp(self, mock_get_working_directory):
        super(DistributorScratchpadMixinTests, self).setUp()
        mock_plugins.install()
        self.distributor_manager = RepoDistributorManager()
        repo_id = 'repo-1'
        with mock.patch('pulp.server.managers.repo.distributor.model.Repository'):
            self.distributor_manager.add_distributor(repo_id, 'mock-distributor', {}, True,
                                                     distributor_id='test-distributor')

        self.conduit = mixins.DistributorScratchPadMixin(repo_id, 'test-distributor')

    def tearDown(self):
        super(DistributorScratchpadMixinTests, self).tearDown()
        manager_factory.reset()
        mock_plugins.reset()

    def test_get_set_scratchpad(self):
        """
        Tests scratchpad calls.
        """

        # Test - get no scratchpad
        self.assertTrue(self.conduit.get_scratchpad() is None)

        # Test - set scrathpad
        value = 'dragon'
        self.conduit.set_scratchpad(value)

        # Test - get updated value
        self.assertEqual(value, self.conduit.get_scratchpad())

    def test_scratchpad_with_error(self):
        # Setup
        mock_distributor_manager = mock.Mock()
        mock_distributor_manager.get_distributor_scratchpad.side_effect = Exception()
        mock_distributor_manager.set_distributor_scratchpad.side_effect = Exception()

        manager_factory._INSTANCES[manager_factory.TYPE_REPO_DISTRIBUTOR] = mock_distributor_manager

        # Test
        self.assertRaises(mixins.DistributorConduitException, self.conduit.get_scratchpad)
        self.assertRaises(mixins.DistributorConduitException, self.conduit.set_scratchpad, 'foo')


class RepoScratchPadMixinTests(unittest.TestCase):
    """
    Tests for the RepoScratchPadMixin.
    """

    def setUp(self):
        manager_factory.initialize()

        self.repo_id = 'sp-repo'
        self.mixin = mixins.RepoScratchPadMixin(self.repo_id, mixins.ImporterConduitException)

    @mock.patch('pulp.plugins.conduits.mixins.model.Repository.objects')
    def test_get_repo_scratchpad(self, mock_repo_qs):
        """
        Test getting a scratchpad from an existing repository.
        """
        mock_repo = mock_repo_qs.get_repo_or_missing_resource.return_value
        scratchpad = self.mixin.get_repo_scratchpad()
        self.assertTrue(scratchpad is mock_repo.scratchpad)

    @mock.patch('pulp.plugins.conduits.mixins.model.Repository.objects')
    def test_get_repo_scratchpad_missing_repo(self, mock_repo_qs):
        """
        Test getting a scratchpad from a repository that does not exist.
        """
        mock_repo_qs.get_repo_or_missing_resource.side_effect = pulp_exceptions.MissingResource
        self.assertRaises(mixins.ImporterConduitException, self.mixin.get_repo_scratchpad)

    @mock.patch('pulp.plugins.conduits.mixins.model.Repository.objects')
    def test_set_repo_scratchpad(self, mock_repo_qs):
        """
        Test setting a scratchpad on a repository.
        """
        scratchpad = {'a': 1}
        self.mixin.set_repo_scratchpad(scratchpad)
        mock_repo_qs.get_repo_or_missing_resource.assert_called_once_with(self.repo_id)
        mock_repo = mock_repo_qs.get_repo_or_missing_resource.return_value
        self.assertEqual(mock_repo.scratchpad, scratchpad)
        mock_repo.save.assert_called_once_with()

    @mock.patch('pulp.plugins.conduits.mixins.model.Repository.objects')
    def test_set_repo_scratchpad_non_dict(self, mock_repo_qs):
        """
        Test setting an invalid scratchpad.
        """
        scratchpad = 'not a dict'
        mock_repo = mock_repo_qs.get_repo_or_missing_resource.return_value
        mock_repo.save.side_effect = mongoengine.ValidationError()
        self.assertRaises(mixins.ImporterConduitException, self.mixin.set_repo_scratchpad,
                          scratchpad)
        mock_repo_qs.get_repo_or_missing_resource.assert_called_once_with(self.repo_id)
        mock_repo.save.assert_called_once_with()

    @mock.patch('pulp.plugins.conduits.mixins.model.Repository.objects')
    def test_update_repo_scratchpad_no_scratchpad(self, mock_repo_qs):
        """
        If the scratchpad is empty, should return before anything else can happen.
        """
        self.mixin.update_repo_scratchpad({})
        self.assertFalse(mock_repo_qs.get_repo_or_missing_resource.called)

    @mock.patch('pulp.plugins.conduits.mixins.model.Repository.objects')
    def test_update_repo_scratchpad(self, mock_repo_qs):
        """
        Test updating a repository scratchpad.
        """
        mock_repo = mock_repo_qs.get_repo_or_missing_resource.return_value
        mock_repo.scratchpad = {'modify': 0, 'leave': 3}
        delta_scratchpad = {'modify': 1, 'new': 2}
        self.mixin.update_repo_scratchpad(delta_scratchpad)
        expected_scratchpad = {'modify': 1, 'new': 2, 'leave': 3}
        self.assertEqual(mock_repo.scratchpad, expected_scratchpad)

    @mock.patch('pulp.plugins.conduits.mixins.model.Repository.objects')
    def test_update_repo_scratchpad__error(self, mock_repo_qs):
        """
        If there is an issue updating a scratchpad, reraise as the class's exception.
        """

        class MockException(Exception):
            """Used for asserting that the correct exceptions are reraised."""
            pass

        mock_repo = mock_repo_qs.get_repo_or_missing_resource.return_value
        mock_repo.save.side_effect = MockException
        self.assertRaises(mixins.ImporterConduitException, self.mixin.update_repo_scratchpad, 'foo')


class RepoScratchPadReadMixinTests(unittest.TestCase):
    """
    Tests for the RepoScratchPadMixin.
    """

    def setUp(self):
        manager_factory.initialize()
        self.mixin = mixins.RepoScratchpadReadMixin(mixins.ImporterConduitException)

    @mock.patch('pulp.plugins.conduits.mixins.model.Repository.objects')
    def test_get_repo_scratchpad(self, mock_repo_qs):
        """
        Test getting a scratchpad from an existing repository.
        """
        mock_repo = mock_repo_qs.get_repo_or_missing_resource.return_value
        scratchpad = self.mixin.get_repo_scratchpad('repo')
        mock_repo_qs.get_repo_or_missing_resource.assert_called_once_with('repo')
        self.assertTrue(scratchpad is mock_repo.scratchpad)

    @mock.patch('pulp.plugins.conduits.mixins.model.Repository.objects')
    def test_get_repo_scratchpad_missing_repo(self, mock_repo_qs):
        """
        Test getting a scratchpad from a repository that does not exist.
        """
        mock_repo_qs.get_repo_or_missing_resource.side_effect = pulp_exceptions.MissingResource
        self.assertRaises(mixins.ImporterConduitException, self.mixin.get_repo_scratchpad, 'repo')
        mock_repo_qs.get_repo_or_missing_resource.assert_called_once_with('repo')


class SingleRepoUnitsMixinTests(unittest.TestCase):

    def setUp(self):
        manager_factory.initialize()

        self.repo_id = 'sr-repo'
        self.mixin = mixins.SingleRepoUnitsMixin(self.repo_id, mixins.DistributorConduitException)

    @mock.patch('pulp.server.controllers.units.get_unit_key_fields_for_type', spec_set=True)
    @mock.patch('pulp.server.managers.repo.unit_association_query.'
                'RepoUnitAssociationQueryManager.get_units')
    def test_get_units(self, mock_query_call, mock_get_unit_key_fields):
        # Setup
        mock_query_call.return_value = [
            {'unit_type_id': 'type-1', 'metadata': {'m': 'm1', 'k1': 'v1'}},
            {'unit_type_id': 'type-2', 'metadata': {'m': 'm1', 'k1': 'v2'}},
        ]

        mock_get_unit_key_fields.return_value = ('k1',)

        fake_criteria = 'fake-criteria'

        # Test
        units = self.mixin.get_units(criteria=fake_criteria)

        # Verify
        self.assertEqual(2, len(units))
        self.assertEqual(1, mock_query_call.call_count)
        self.assertEqual(mock_query_call.call_args[0][0], self.repo_id)
        self.assertEqual(mock_query_call.call_args[1]['criteria'], fake_criteria)

    @mock.patch('pulp.server.managers.repo.unit_association_query.'
                'RepoUnitAssociationQueryManager.get_units')
    def test_get_units_server_error(self, mock_query_call):
        # Setup
        mock_query_call.side_effect = Exception()

        # Test
        self.assertRaises(mixins.DistributorConduitException, self.mixin.get_units)


class MultipleRepoUnitsMixinTests(unittest.TestCase):

    def setUp(self):
        manager_factory.initialize()

        self.mixin = mixins.MultipleRepoUnitsMixin(mixins.ImporterConduitException)

    @mock.patch('pulp.server.controllers.units.get_unit_key_fields_for_type', spec_set=True)
    @mock.patch('pulp.server.managers.repo.unit_association_query.'
                'RepoUnitAssociationQueryManager.get_units')
    def test_get_units(self, mock_query_call, mock_get_unit_key_fields):
        # Setup
        mock_query_call.return_value = [
            {'unit_type_id': 'type-1', 'metadata': {'m': 'm1', 'k1': 'v1'}},
            {'unit_type_id': 'type-2', 'metadata': {'m': 'm1', 'k1': 'v2'}},
        ]

        mock_get_unit_key_fields.return_value = ('k1',)

        fake_criteria = 'fake-criteria'

        # Test
        repo_id = 'mr-repo'
        units = self.mixin.get_units(repo_id, criteria=fake_criteria)

        # Verify
        self.assertEqual(2, len(units))
        self.assertEqual(1, mock_query_call.call_count)
        self.assertEqual(mock_query_call.call_args[0][0], repo_id)
        self.assertEqual(mock_query_call.call_args[1]['criteria'], fake_criteria)

    @mock.patch('pulp.server.managers.repo.unit_association_query.'
                'RepoUnitAssociationQueryManager.get_units')
    def test_get_units_server_error(self, mock_query_call):
        # Setup
        mock_query_call.side_effect = Exception()

        # Test
        self.assertRaises(mixins.ImporterConduitException, self.mixin.get_units, 'foo')


class SearchUnitsMixinTests(unittest.TestCase):

    def setUp(self):
        manager_factory.initialize()

        self.mixin = mixins.SearchUnitsMixin(mixins.ImporterConduitException)

    @mock.patch('pulp.plugins.types.database.type_definition')
    @mock.patch('pulp.server.managers.content.query.ContentQueryManager.find_by_criteria')
    def test_search_all_units(self, mock_query_call, mock_type_def_call):
        # Setup
        mock_query_call.return_value = [
            {'m': 'm1', 'k1': 'v1'},
            {'m': 'm1', 'k1': 'v2'},
        ]

        mock_type_def_call.return_value = {
            'id': 'mock-type-def',
            'unit_key': ['k1']
        }

        # Test
        units = self.mixin.search_all_units('type-1', 'fake-criteria')

        # Verify
        self.assertEqual(2, len(units))
        self.assertEqual(1, mock_query_call.call_count)
        self.assertTrue(isinstance(units[0], Unit))
        self.assertEqual(mock_query_call.call_args[0][0], 'type-1')
        self.assertEqual(mock_query_call.call_args[0][1], 'fake-criteria')

    @mock.patch('pulp.server.managers.content.query.ContentQueryManager.find_by_criteria')
    def test_search_all_units_server_error(self, mock_call):
        # Setup
        mock_call.side_effect = Exception()

        # Test
        self.assertRaises(mixins.ImporterConduitException, self.mixin.search_all_units,
                          't', 'fake-criteria')

    @mock.patch('pulp.plugins.types.database.type_definition')
    @mock.patch('pulp.server.managers.content.query.ContentQueryManager.'
                'get_content_unit_by_keys_dict')
    def test_find_unit_by_unit_key(self, mock_get_unit, mock_type_def):
        # Setup
        pulp_unit = {'id': 'fake-unit-id', 'another-unit-key-field': 'fake',
                     'other_field': '1234'}
        mock_get_unit.return_value = pulp_unit

        mock_type_def.return_value = {
            'id': 'mock-type-def',
            'unit_key': ['id', 'another-unit-key-field']
        }

        # Test
        unit = self.mixin.find_unit_by_unit_key('type-1', {'id': 'not-used-for-mock'})

        # Verify
        self.assertEqual(1, mock_get_unit.call_count)
        self.assertEqual(unit.unit_key, {'id': 'fake-unit-id', 'another-unit-key-field': 'fake'})
        self.assertEqual(unit.metadata,
                         {'other_field': '1234', constants.PULP_USER_METADATA_FIELDNAME: {}})

    @mock.patch('pulp.server.managers.content.query.ContentQueryManager.'
                'get_content_unit_by_keys_dict')
    def test_find_unit_by_unit_key_not_found(self, mock_get_unit):
        # Setup
        mock_get_unit.side_effect = MissingResource()

        # Test
        unit = self.mixin.find_unit_by_unit_key('type-1', {'id': 'not-used-for-mock'})

        # Verify
        self.assertEqual(unit, None)


class ImporterScratchPadMixinTests(base.PulpServerTests):

    def setUp(self):
        super(ImporterScratchPadMixinTests, self).setUp()
        mock_plugins.install()

        self.importer_manager = RepoImporterManager()

        self.repo_id = 'repo-1'
        self.conduit = mixins.ImporterScratchPadMixin(self.repo_id, 'test-importer')

        manager_factory.initialize()

        self.importer_id = 'isp-importer'
        self.mixin = mixins.ImporterScratchPadMixin(self.repo_id, self.importer_id)

    def clean(self):
        super(ImporterScratchPadMixinTests, self).clean()
        types_database.clean()
        model.Repository.drop_collection()

    def tearDown(self):
        super(ImporterScratchPadMixinTests, self).tearDown()
        manager_factory.reset()
        mock_plugins.reset()

    @mock.patch('pulp.server.managers.repo.importer.model.Repository')
    def test_get_set_scratchpad(self, mock_repo_qs):
        """
        Tests scratchpad calls.
        """

        # Setup
        self.importer_manager.set_importer(self.repo_id, 'mock-importer', {})

        # Test - get no scratchpad
        self.assertTrue(self.conduit.get_scratchpad() is None)

        # Test - set scrathpad
        value = 'dragon'
        self.conduit.set_scratchpad(value)

        # Test - get updated value
        self.assertEqual(value, self.conduit.get_scratchpad())

    def test_scratchpad_with_error(self):
        # Setup
        mock_manager = mock.Mock()
        mock_manager.get_importer_scratchpad.side_effect = Exception()
        mock_manager.set_importer_scratchpad.side_effect = Exception()

        manager_factory._INSTANCES[manager_factory.TYPE_REPO_IMPORTER] = mock_manager

        # Test
        self.assertRaises(mixins.ImporterConduitException, self.conduit.get_scratchpad)
        self.assertRaises(mixins.ImporterConduitException, self.conduit.set_scratchpad, 'foo')

    @mock.patch('pulp.server.managers.repo.importer.RepoImporterManager.get_importer_scratchpad')
    def test_get_scratchpad(self, mock_call):
        # Setup
        mock_call.return_value = 'sp'

        # Test
        sp = self.mixin.get_scratchpad()

        # Verify
        self.assertEqual(sp, 'sp')
        self.assertEqual(1, mock_call.call_count)

    @mock.patch('pulp.server.managers.repo.importer.RepoImporterManager.get_importer_scratchpad')
    def test_get_scratchpad_server_error(self, mock_call):
        # Setup
        mock_call.side_effect = Exception()

        # Test
        self.assertRaises(mixins.ImporterConduitException, self.mixin.get_scratchpad)

    @mock.patch('pulp.server.managers.repo.importer.RepoImporterManager.set_importer_scratchpad')
    def test_set_scratchpad(self, mock_call):
        # Test
        self.mixin.set_scratchpad('foo')

        # Verify
        self.assertEqual(1, mock_call.call_count)
        self.assertEqual(mock_call.call_args[0][0], self.repo_id)
        self.assertEqual(mock_call.call_args[0][1], 'foo')

    @mock.patch('pulp.server.managers.repo.importer.RepoImporterManager.set_importer_scratchpad')
    def test_set_scratchpad_server_error(self, mock_call):
        # Setup
        mock_call.side_effect = Exception()

        # Test
        self.assertRaises(mixins.ImporterConduitException, self.mixin.set_scratchpad, 'foo')


class DistributorScratchPadMixinTests(unittest.TestCase):

    def setUp(self):
        manager_factory.initialize()

        self.repo_id = 'dsp-repo'
        self.distributor_id = 'dsp-distributor'
        self.mixin = mixins.DistributorScratchPadMixin(self.repo_id, self.distributor_id)

    @mock.patch('pulp.server.managers.repo.distributor.RepoDistributorManager.'
                'get_distributor_scratchpad')
    def test_get_scratchpad(self, mock_call):
        # Setup
        mock_call.return_value = 'sp'

        # Test
        sp = self.mixin.get_scratchpad()

        # Verify
        self.assertEqual(sp, 'sp')
        self.assertEqual(1, mock_call.call_count)

    @mock.patch('pulp.server.managers.repo.distributor.RepoDistributorManager.'
                'get_distributor_scratchpad')
    def test_get_scratchpad_server_error(self, mock_call):
        # Setup
        mock_call.side_effect = Exception()

        # Test
        self.assertRaises(mixins.DistributorConduitException, self.mixin.get_scratchpad)

    @mock.patch('pulp.server.managers.repo.distributor.RepoDistributorManager.'
                'set_distributor_scratchpad')
    def test_set_scratchpad(self, mock_call):
        # Test
        self.mixin.set_scratchpad('foo')

        # Verify
        self.assertEqual(1, mock_call.call_count)
        self.assertEqual(mock_call.call_args[0][0], self.repo_id)
        self.assertEqual(mock_call.call_args[0][1], self.distributor_id)
        self.assertEqual(mock_call.call_args[0][2], 'foo')

    @mock.patch('pulp.server.managers.repo.distributor.RepoDistributorManager.'
                'set_distributor_scratchpad')
    def test_set_scratchpad_server_error(self, mock_call):
        # Setup
        mock_call.side_effect = Exception()

        # Test
        self.assertRaises(mixins.DistributorConduitException, self.mixin.set_scratchpad, 'foo')


class RepoGroupDistributorScratchPadMixinTests(unittest.TestCase):

    def setUp(self):
        manager_factory.initialize()

        self.group_id = 'group-id'
        self.distributor_id = 'group-dist'
        self.mixin = mixins.RepoGroupDistributorScratchPadMixin(self.group_id, self.distributor_id)

    @mock.patch('pulp.server.managers.repo.group.distributor.RepoGroupDistributorManager.'
                'get_distributor_scratchpad')
    def test_get_scratchpad(self, mock_call):
        # Setup
        mock_call.return_value = 'sp'

        # Test
        sp = self.mixin.get_scratchpad()

        # Verify
        self.assertEqual(sp, 'sp')
        self.assertEqual(1, mock_call.call_count)
        self.assertEqual(mock_call.call_args[0][0], self.group_id)
        self.assertEqual(mock_call.call_args[0][1], self.distributor_id)

    @mock.patch('pulp.server.managers.repo.group.distributor.RepoGroupDistributorManager.'
                'get_distributor_scratchpad')
    def test_get_scratchpad_server_error(self, mock_call):
        # Setup
        mock_call.side_effect = Exception()

        # Test
        self.assertRaises(mixins.DistributorConduitException, self.mixin.get_scratchpad)

    @mock.patch('pulp.server.managers.repo.group.distributor.RepoGroupDistributorManager.'
                'set_distributor_scratchpad')
    def test_set_scratchpad(self, mock_call):
        # Test
        self.mixin.set_scratchpad('foo')

        # Verify
        self.assertEqual(1, mock_call.call_count)
        self.assertEqual(mock_call.call_args[0][0], self.group_id)
        self.assertEqual(mock_call.call_args[0][1], self.distributor_id)
        self.assertEqual(mock_call.call_args[0][2], 'foo')

    @mock.patch('pulp.server.managers.repo.group.distributor.RepoGroupDistributorManager.'
                'set_distributor_scratchpad')
    def test_set_scratchpad_server_error(self, mock_call):
        # Setup
        mock_call.side_effect = Exception()

        # Test
        self.assertRaises(mixins.DistributorConduitException, self.mixin.set_scratchpad, 'foo')


class AddUnitMixinTests(unittest.TestCase):

    def setUp(self):
        manager_factory.initialize()

        self.repo_id = 'add-repo'
        self.importer_id = 'add-importer'

        self.mixin = mixins.AddUnitMixin(self.repo_id, self.importer_id)

    @mock.patch('pulp.server.managers.content.query.ContentQueryManager.'
                'request_content_unit_file_path')
    def test_init_unit(self, mock_file_path_call):
        # Setup
        mock_file_path_call.return_value = '/tmp'

        # Test
        path_unit = self.mixin.init_unit('t', {'k': 'v'}, {'m': 'm1'}, '/bar')
        no_path_unit = self.mixin.init_unit('t', {'k': 'v'}, {'m': 'm1'}, None)

        # Verify
        self.assertTrue(isinstance(path_unit, Unit))
        self.assertEqual(path_unit.type_id, 't')
        self.assertEqual(path_unit.unit_key, {'k': 'v'})
        self.assertEqual(path_unit.metadata,
                         {'m': 'm1', constants.PULP_USER_METADATA_FIELDNAME: {}})
        self.assertEqual(path_unit.storage_path, '/tmp')

        self.assertEqual(no_path_unit.storage_path, None)

    @mock.patch('pulp.server.managers.content.query.ContentQueryManager.'
                'request_content_unit_file_path')
    def test_init_unit_server_error(self, mock_call):
        # Setup
        mock_call.side_effect = Exception()

        # Test
        self.assertRaises(mixins.ImporterConduitException, self.mixin.init_unit, 't', {'k': 'v'},
                          {'m': 'm1'}, '/bar')

    @mock.patch('pulp.server.managers.content.query.ContentQueryManager.'
                'request_content_unit_file_path')
    @mock.patch('pulp.server.managers.content.query.ContentQueryManager.'
                'get_content_unit_by_keys_dict')
    @mock.patch('pulp.server.managers.content.cud.ContentManager.update_content_unit')
    @mock.patch('pulp.server.managers.content.cud.ContentManager.add_content_unit')
    @mock.patch('pulp.server.managers.repo.unit_association.RepoUnitAssociationManager.'
                'associate_unit_by_id')
    def test_save_unit_new_unit(self, mock_associate, mock_add, mock_update, mock_get, mock_path):
        # Setup
        unit = self.mixin.init_unit('t', {'k': 'v'}, {'m': 'm1'}, '/bar')
        mock_get.side_effect = MissingResource()
        mock_add.return_value = 'new-unit-id'

        # Test
        saved = self.mixin.save_unit(unit)

        # Verify
        self.assertEqual(1, mock_get.call_count)
        self.assertEqual(0, mock_update.call_count)
        self.assertEqual(1, mock_add.call_count)
        self.assertEqual(1, mock_associate.call_count)
        self.assertEqual(1, self.mixin._added_count)
        self.assertEqual(0, self.mixin._updated_count)
        self.assertEqual(saved.id, 'new-unit-id')

    @mock.patch('pulp.server.managers.content.query.ContentQueryManager.'
                'request_content_unit_file_path')
    @mock.patch('pulp.server.managers.content.query.ContentQueryManager.'
                'get_content_unit_by_keys_dict')
    @mock.patch('pulp.server.managers.content.cud.ContentManager.update_content_unit')
    @mock.patch('pulp.server.managers.content.cud.ContentManager.add_content_unit')
    @mock.patch('pulp.server.managers.repo.unit_association.RepoUnitAssociationManager.'
                'associate_unit_by_id')
    def test_save_unit_new_unit_race_condition(self, mock_associate, mock_add, mock_update,
                                               mock_get, mock_path):
        """
        This simulates a case where the same unit gets added by another workflow
        before the save completes. In that case, the failover behavior is to
        update the unit instead of adding it.
        """
        # Setup
        unit = self.mixin.init_unit('t', {'k': 'v'}, {'m': 'm1'}, '/bar')
        mock_add.side_effect = DuplicateKeyError('dups!')
        # raise an exception the first time around, then simulate the unit
        # having appeared since the last call.
        mock_get.side_effect = _create_mock_side_effect([MissingResource, {'_id': 'existing'}])

        # Test
        saved = self.mixin.save_unit(unit)

        # Verify
        self.assertEqual(2, mock_get.call_count)
        self.assertEqual(1, mock_update.call_count)
        self.assertEqual(1, mock_add.call_count)
        self.assertEqual(1, mock_associate.call_count)
        self.assertEqual(0, self.mixin._added_count)
        self.assertEqual(1, self.mixin._updated_count)
        self.assertEqual(saved.id, 'existing')

    @mock.patch('pulp.server.managers.content.query.ContentQueryManager.'
                'request_content_unit_file_path')
    @mock.patch('pulp.server.managers.content.query.ContentQueryManager.'
                'get_content_unit_by_keys_dict')
    @mock.patch('pulp.server.managers.content.cud.ContentManager.update_content_unit')
    @mock.patch('pulp.server.managers.content.cud.ContentManager.add_content_unit')
    @mock.patch('pulp.server.managers.repo.unit_association.RepoUnitAssociationManager.'
                'associate_unit_by_id')
    def test_save_unit_update_race_condition(self, mock_associate, mock_add, mock_update, mock_get,
                                             mock_path):
        """
        This tests a case where the unit gets removed between the call to get its
        ID and the call to update it. In that case, the failover behavior is to
        add it as a new unit.
        """
        # Setup
        unit = self.mixin.init_unit('t', {'k': 'v'}, {'m': 'm1'}, '/bar')
        mock_update.side_effect = MissingResource()
        mock_add.return_value = 'new-unit-id'

        # Test
        saved = self.mixin.save_unit(unit)

        # Verify
        self.assertEqual(1, mock_get.call_count)
        self.assertEqual(1, mock_update.call_count)
        self.assertEqual(1, mock_add.call_count)
        self.assertEqual(1, mock_associate.call_count)
        self.assertEqual(1, self.mixin._added_count)
        self.assertEqual(0, self.mixin._updated_count)
        self.assertEqual(saved.id, 'new-unit-id')

    @mock.patch('pulp.server.managers.content.query.ContentQueryManager.'
                'request_content_unit_file_path')
    @mock.patch('pulp.server.managers.content.query.ContentQueryManager.'
                'get_content_unit_by_keys_dict')
    @mock.patch('pulp.server.managers.content.cud.ContentManager.update_content_unit')
    @mock.patch('pulp.server.managers.content.cud.ContentManager.add_content_unit')
    @mock.patch('pulp.server.managers.repo.unit_association.RepoUnitAssociationManager.'
                'associate_unit_by_id')
    def test_save_unit_updated_unit(self, mock_associate, mock_add, mock_update, mock_get,
                                    mock_path):
        # Setup
        unit = self.mixin.init_unit('t', {'k': 'v'}, {'m': 'm1'}, '/bar')
        mock_get.return_value = {'_id': 'existing'}

        # Test
        saved = self.mixin.save_unit(unit)

        # Verify
        self.assertEqual(1, mock_get.call_count)
        self.assertEqual(1, mock_update.call_count)
        self.assertEqual(0, mock_add.call_count)
        self.assertEqual(1, mock_associate.call_count)
        self.assertEqual(0, self.mixin._added_count)
        self.assertEqual(1, self.mixin._updated_count)
        self.assertEqual(saved.id, 'existing')

    @mock.patch('pulp.server.managers.content.query.ContentQueryManager.'
                'request_content_unit_file_path')
    @mock.patch('pulp.server.managers.content.query.ContentQueryManager.'
                'get_content_unit_by_keys_dict')
    @mock.patch('pulp.server.managers.content.cud.ContentManager.update_content_unit')
    @mock.patch('pulp.server.managers.content.cud.ContentManager.add_content_unit')
    @mock.patch('pulp.server.managers.repo.unit_association.RepoUnitAssociationManager.'
                'associate_unit_by_id')
    def test_save_unit_with_error(self, mock_associate, mock_add, mock_update, mock_get, mock_path):
        # Setup
        mock_get.side_effect = Exception()

        # Test
        self.assertRaises(mixins.ImporterConduitException, self.mixin.save_unit, None)

    @mock.patch('pulp.server.managers.content.cud.ContentManager.link_referenced_content_units')
    def test_link_unit(self, mock_link):
        # Setup
        from_unit = Unit('t1', {'k': 'v1'}, {'m': 'm'}, 'p')
        from_unit.id = 'from-unit'
        to_unit = Unit('t2', {'k': 'v2'}, {'m': 'm'}, 'p')
        to_unit.id = 'to-unit'

        # Test
        self.mixin.link_unit(from_unit, to_unit)

        # Verify
        self.assertEqual(1, mock_link.call_count)
        self.assertEqual(mock_link.call_args[0][0], from_unit.type_id)
        self.assertEqual(mock_link.call_args[0][1], from_unit.id)
        self.assertEqual(mock_link.call_args[0][2], to_unit.type_id)
        self.assertEqual(mock_link.call_args[0][3], [to_unit.id])

    @mock.patch('pulp.server.managers.content.cud.ContentManager.link_referenced_content_units')
    def test_link_unit_bidirectional(self, mock_link):
        # Setup
        from_unit = Unit('t1', {'k': 'v1'}, {'m': 'm'}, 'p')
        from_unit.id = 'from-unit'
        to_unit = Unit('t2', {'k': 'v2'}, {'m': 'm'}, 'p')
        to_unit.id = 'to-unit'

        # Test
        self.mixin.link_unit(from_unit, to_unit, bidirectional=True)

        # Verify
        self.assertEqual(2, mock_link.call_count)

        call_1_args = mock_link.call_args_list[0][0]
        self.assertEqual(call_1_args[0], from_unit.type_id)
        self.assertEqual(call_1_args[1], from_unit.id)
        self.assertEqual(call_1_args[2], to_unit.type_id)
        self.assertEqual(call_1_args[3], [to_unit.id])

        call_2_args = mock_link.call_args_list[1][0]
        self.assertEqual(call_2_args[0], to_unit.type_id)
        self.assertEqual(call_2_args[1], to_unit.id)
        self.assertEqual(call_2_args[2], from_unit.type_id)
        self.assertEqual(call_2_args[3], [from_unit.id])

    @mock.patch('pulp.server.managers.content.cud.ContentManager.link_referenced_content_units')
    def test_link_unit_server_error(self, mock_call):
        # Setup
        mock_call.side_effect = Exception()

        # Test
        self.assertRaises(mixins.ImporterConduitException, self.mixin.link_unit, None, None)


class StatusMixinTests(unittest.TestCase):

    def setUp(self):
        manager_factory.initialize()

    @mock.patch('pulp.server.db.model.TaskStatus.objects')
    @mock.patch('pulp.plugins.conduits.mixins.get_current_task_id')
    def test_set_progress(self, mock_get_task_id, mock_task_status_objects):
        # Setup
        self.report_id = 'test-report'
        task_id = 'test-id'
        mock_get_task_id.return_value = task_id
        test_task_documents = mock.Mock()
        mock_task_status_objects.return_value = test_task_documents
        self.mixin = mixins.StatusMixin(self.report_id, mixins.ImporterConduitException)

        # Test
        status = 'status'
        self.mixin.set_progress(status)

        # Verify
        mock_task_status_objects.assert_called_with(task_id=task_id)
        self.assertEqual(1, test_task_documents.update_one.call_count)
        test_task_documents.update_one.assert_called_with(
            set__progress_report={'test-report': 'status'})

    @mock.patch('pulp.server.db.model.TaskStatus.objects')
    @mock.patch('pulp.plugins.conduits.mixins.get_current_task_id')
    def test_set_progress_no_task(self, mock_get_task_id, mock_task_status_objects):
        # Setup
        mock_get_task_id.return_value = None
        self.mixin = mixins.StatusMixin('', mixins.ImporterConduitException)

        # Test
        status = 'status'
        self.mixin.set_progress(status)

        # Verify
        self.assertFalse(mock_task_status_objects.called)

    @mock.patch('pulp.server.db.model.TaskStatus.objects')
    def test_set_progress_with_exception(self, mock_call):
        # Setup
        self.report_id = 'test-report'
        self.mixin = mixins.StatusMixin(self.report_id, mixins.ImporterConduitException)
        self.mixin.task_id = 'test_id'
        mock_call.side_effect = Exception()

        # Test
        self.assertRaises(mixins.ImporterConduitException, self.mixin.set_progress, 'foo')


class PublishReportMixinTests(unittest.TestCase):

    def setUp(self):
        self.mixin = mixins.PublishReportMixin()

    def test_build_reports(self):
        # Setup
        summary = 'summary'
        details = 'details'

        # Test Success Report
        r = self.mixin.build_success_report(summary, details)
        self.assertTrue(isinstance(r, PublishReport))
        self.assertEqual(r.success_flag, True)
        self.assertEqual(r.canceled_flag, False)
        self.assertEqual(r.summary, summary)
        self.assertEqual(r.details, details)

        # Test Failure Report
        r = self.mixin.build_failure_report(summary, details)
        self.assertTrue(isinstance(r, PublishReport))
        self.assertEqual(r.success_flag, False)
        self.assertEqual(r.canceled_flag, False)
        self.assertEqual(r.summary, summary)
        self.assertEqual(r.details, details)

        # Test Cancel Report
        r = self.mixin.build_cancel_report(summary, details)
        self.assertTrue(isinstance(r, PublishReport))
        self.assertEqual(r.success_flag, False)
        self.assertEqual(r.canceled_flag, True)
        self.assertEqual(r.summary, summary)
        self.assertEqual(r.details, details)
