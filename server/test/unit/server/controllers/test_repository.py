import inspect

from bson.objectid import InvalidId
from mock import call, Mock, MagicMock, patch
import mock
import mongoengine

from pulp.common import error_codes
from pulp.common.compat import unittest
from pulp.plugins.loader import exceptions as plugin_exceptions
from pulp.plugins.model import PublishReport
from pulp.server.controllers import repository as repo_controller
from pulp.server import exceptions as pulp_exceptions
from pulp.server.db import model


MODULE = 'pulp.server.controllers.repository.'


class MockException(Exception):
    """Used for tracking the handling of exceptions."""
    pass


class DemoModel(model.ContentUnit):
    key_field = mongoengine.StringField()
    unit_key_fields = ['key_field']
    _content_type_id = mongoengine.StringField(default='demo_model')


@mock.patch('pulp.server.db.model.RepositoryContentUnit.objects')
class TestGetAssociatedUnitIDs(unittest.TestCase):
    def setUp(self):
        self.associations = [
            model.RepositoryContentUnit(repo_id='repo1', unit_id='a', unit_type_id='demo_model'),
            model.RepositoryContentUnit(repo_id='repo1', unit_id='b', unit_type_id='demo_model'),
        ]

    def test_returns_ids(self, mock_objects):
        mock_objects.return_value.only.return_value = self.associations

        ret = list(repo_controller.get_associated_unit_ids('repo1', 'demo_model'))

        self.assertEqual(ret, ['a', 'b'])

    def test_returns_generator(self, mock_objects):
        mock_objects.return_value.only.return_value = self.associations

        ret = repo_controller.get_associated_unit_ids('repo1', 'demo_model')

        self.assertTrue(inspect.isgenerator(ret))

    def test_uses_q(self, mock_objects):
        mock_objects.return_value.only.return_value = self.associations
        q = mongoengine.Q(foo='bar')

        list(repo_controller.get_associated_unit_ids('repo1', 'demo_model', q))

        mock_objects.assert_called_once_with(repo_id='repo1', unit_type_id='demo_model', q_obj=q)


@mock.patch.object(repo_controller, 'get_associated_unit_ids')
@mock.patch.object(DemoModel, 'objects')
class TestGetUnitModelQuerySets(unittest.TestCase):
    def setUp(self):
        self.units = [
            DemoModel(key_field='foo', id='123'),
            DemoModel(key_field='bar', id='456')
        ]

    def test_returns_generator(self, mock_objects, mock_get_ids):
        mock_objects.return_value = self.units

        ret = repo_controller.get_unit_model_querysets('repo1', DemoModel)

        self.assertTrue(inspect.isgenerator(ret))

    def test_returns_objects_return_value(self, mock_objects, mock_get_ids):
        """
        yielded items should directly be the QuerySets returned by calling model_class.objects()
        """
        mock_get_ids.return_value = ['123', '456']

        ret = repo_controller.get_unit_model_querysets('repo1', DemoModel)

        self.assertEqual(list(ret)[0], mock_objects.return_value)

    def test_filters_with_ids(self, mock_objects, mock_get_ids):
        mock_get_ids.return_value = ['123', '456']

        list(repo_controller.get_unit_model_querysets('repo1', DemoModel))

        mock_objects.assert_called_once_with(id__in=('123', '456'))

    def test_calls_get_ids(self, mock_objects, mock_get_ids):
        q = mongoengine.Q(foo='bar')

        list(repo_controller.get_unit_model_querysets('repo1', DemoModel, q))

        mock_get_ids.assert_called_once_with('repo1', 'demo_model', q)


@patch('pulp.server.controllers.repository.model.RepositoryContentUnit.objects')
class FindRepoContentUnitsTest(unittest.TestCase):

    def test_repo_content_units_query(self, mock_rcu_objects):
        """
        Test the query parameters for the RepositoryContentUnit
        """
        repo = MagicMock(repo_id='foo')
        rcu_filter = mongoengine.Q(unit_type_id='demo_model')
        list(repo_controller.find_repo_content_units(repo, repo_content_unit_q=rcu_filter))
        self.assertEquals(mock_rcu_objects.call_args[1]['repo_id'], 'foo')
        self.assertEquals(mock_rcu_objects.call_args[1]['q_obj'], rcu_filter)

    @patch.object(DemoModel, 'objects')
    @patch('pulp.server.controllers.repository.plugin_api.get_unit_model_by_id')
    def test_content_units_query_test(self, mock_get_model, mock_demo_objects, mock_rcu_objects):
        """
        Test the query parameters for the ContentUnit
        """
        repo = MagicMock(repo_id='foo')
        test_unit = DemoModel(id='bar', key_field='baz')
        test_rcu = model.RepositoryContentUnit(repo_id='foo',
                                               unit_type_id='demo_model',
                                               unit_id='bar')
        mock_rcu_objects.return_value = [test_rcu]

        u_filter = mongoengine.Q(key_field='baz')
        u_fields = ['key_field']
        mock_get_model.return_value = DemoModel
        mock_demo_objects.return_value.only.return_value = [test_unit]
        result = list(repo_controller.find_repo_content_units(repo, units_q=u_filter,
                                                              unit_fields=u_fields))

        mock_demo_objects.return_value.only.assert_called_once_with('key_field')

        # validate that the repo content unit was returned and that the unit is attached
        self.assertEquals(result, [test_rcu])
        self.assertEquals(result[0].unit, test_unit)

    @patch.object(DemoModel, 'objects')
    @patch('pulp.server.controllers.repository.plugin_api.get_unit_model_by_id')
    def test_content_units_query_yield_unit(self, mock_get_model, mock_demo_objects,
                                            mock_rcu_objects):
        """
        Test the query parameters for yielding the ContentUnit instead of the RepositoryContentUnit
        """
        repo = MagicMock(repo_id='foo')
        test_unit = DemoModel(id='bar', key_field='baz')
        test_rcu = model.RepositoryContentUnit(repo_id='foo',
                                               unit_type_id='demo_model',
                                               unit_id='bar')
        mock_rcu_objects.return_value = [test_rcu]

        u_filter = mongoengine.Q(key_field='baz')
        u_fields = ['key_field']
        mock_get_model.return_value = DemoModel
        mock_demo_objects.return_value.only.return_value = [test_unit]
        result = list(repo_controller.find_repo_content_units(repo, units_q=u_filter,
                                                              unit_fields=u_fields,
                                                              yield_content_unit=True))

        mock_demo_objects.return_value.only.assert_called_once_with('key_field')

        # validate that the content unit was returned
        self.assertEquals(result, [test_unit])

    @patch.object(DemoModel, 'objects')
    @patch('pulp.server.controllers.repository.plugin_api.get_unit_model_by_id')
    def test_limit(self, mock_get_model, mock_demo_objects, mock_rcu_objects):
        """
        Test that limits are applied properly to the results
        """
        repo = MagicMock(repo_id='foo')
        rcu_list = []
        unit_list = []
        for i in range(10):
            unit_id = 'bar_%i' % i
            unit_key = 'key_%i' % i
            rcu = model.RepositoryContentUnit(repo_id='foo',
                                              unit_type_id='demo_model',
                                              unit_id=unit_id)
            rcu_list.append(rcu)
            unit_list.append(DemoModel(id=unit_id, key_field=unit_key))

        mock_rcu_objects.return_value = rcu_list

        mock_get_model.return_value = DemoModel
        mock_demo_objects.return_value = unit_list
        result = list(repo_controller.find_repo_content_units(repo, limit=5))

        self.assertEquals(5, len(result))
        self.assertEquals(result[0].unit_id, 'bar_0')
        self.assertEquals(result[4].unit_id, 'bar_4')

    @patch.object(DemoModel, 'objects')
    @patch('pulp.server.controllers.repository.plugin_api.get_unit_model_by_id')
    def test_skip(self, mock_get_model, mock_demo_objects, mock_rcu_objects):
        """
        Test that the skip parameter is applied properly
        """
        repo = MagicMock(repo_id='foo')
        rcu_list = []
        unit_list = []
        for i in range(10):
            unit_id = 'bar_%i' % i
            unit_key = 'key_%i' % i
            rcu = model.RepositoryContentUnit(repo_id='foo',
                                              unit_type_id='demo_model',
                                              unit_id=unit_id)
            rcu_list.append(rcu)
            unit_list.append(DemoModel(id=unit_id, key_field=unit_key))

        mock_rcu_objects.return_value = rcu_list

        mock_get_model.return_value = DemoModel
        mock_demo_objects.return_value = unit_list
        result = list(repo_controller.find_repo_content_units(repo, limit=5, skip=5))

        self.assertEquals(5, len(result))
        self.assertEquals(result[0].unit_id, 'bar_5')
        self.assertEquals(result[4].unit_id, 'bar_9')


class FindUnitsNotDownloadedTests(unittest.TestCase):

    @patch(MODULE + 'get_mongoengine_unit_querysets')
    def test_call(self, mock_repo_querysets):
        mock_qs = Mock()
        mock_qs.return_value = [0, 1, 2]
        mock_repo_querysets.return_value = [mock_qs]
        units = repo_controller.find_units_not_downloaded('mock_repo')
        for x, unit in zip(range(3), units):
            self.assertEqual(x, unit)


class MissingUnitCountTests(unittest.TestCase):

    @patch(MODULE + 'get_mongoengine_unit_querysets')
    def test_call(self, mock_repo_querysets):
        query_set = Mock()
        query_set.return_value.count.return_value = 5
        mock_repo_querysets.return_value = [query_set]
        self.assertEqual(5, repo_controller.missing_unit_count('mock_repo'))


class HasAllUnitsDownloadedTests(unittest.TestCase):

    @patch(MODULE + 'get_mongoengine_unit_querysets')
    def test_true(self, mock_repo_querysets):
        query_set = Mock()
        query_set.return_value.count.return_value = 0
        mock_repo_querysets.return_value = [query_set]
        self.assertTrue(repo_controller.has_all_units_downloaded('mock_repo'))

    @patch(MODULE + 'get_mongoengine_unit_querysets')
    def test_false(self, mock_repo_querysets):
        query_set = Mock()
        query_set.return_value.count.return_value = 5
        mock_repo_querysets.return_value = [query_set]
        self.assertFalse(repo_controller.has_all_units_downloaded('mock_repo'))


class GetMongoengineRepoQuerysetsTests(unittest.TestCase):
    """Tests for the get_mongoengine_unit_querysets function."""

    @patch(MODULE + 'get_unit_model_querysets')
    @patch(MODULE + 'plugin_api.get_unit_model_by_id', lambda x: x)
    @patch(MODULE + 'model.RepositoryContentUnit.objects')
    def test_mongoengine_types_only(self, mock_repo_units, mock_get_querysets):
        """Assert that the correct number of query sets are returned."""
        content_types = ['dog', 'cat', 'goat']
        mock_repo_units.return_value.distinct.return_value = content_types
        mock_get_querysets.return_value = [1]

        result = list(repo_controller.get_mongoengine_unit_querysets('mock_repo'))
        self.assertEqual(3, len(result))
        for content_type, actual_call in zip(content_types, mock_get_querysets.call_args_list):
            self.assertEqual(call('mock_repo', content_type, None), actual_call)

    @patch(MODULE + 'get_unit_model_querysets')
    @patch(MODULE + 'plugin_api.get_unit_model_by_id', lambda x: x)
    @patch(MODULE + 'model.RepositoryContentUnit.objects')
    def test_non_mongoengine_type(self, mock_repo_units, mock_get_querysets):
        """Assert that the correct number of query sets are returned."""
        content_types = ['dog', None, 'goat']
        mock_repo_units.return_value.distinct.return_value = content_types
        mock_get_querysets.return_value = [1]

        result = list(repo_controller.get_mongoengine_unit_querysets('mock_repo'))
        self.assertEqual(2, len(result))
        for content_type, actual_call in zip(['dog', 'goat'], mock_get_querysets.call_args_list):
            self.assertEqual(call('mock_repo', content_type, None), actual_call)

    @patch(MODULE + 'get_unit_model_querysets')
    @patch(MODULE + 'plugin_api.get_unit_model_by_id', lambda x: x)
    @patch(MODULE + 'model.RepositoryContentUnit.objects')
    def test_non_mongoengine_filter_file_units(self, mock_repo_units, mock_get_querysets):
        """Assert that the correct number of query sets are returned."""
        class FileUnit(model.FileContentUnit):
            pass

        class NonFileUnit(model.ContentUnit):
            pass

        content_types = [FileUnit, NonFileUnit]
        mock_repo_units.return_value.distinct.return_value = content_types
        mock_get_querysets.return_value = [1]

        result = list(repo_controller.get_mongoengine_unit_querysets('mock_repo',
                                                                     file_units=True))
        self.assertEqual(1, len(result))


class UpdateRepoUnitCountsTests(unittest.TestCase):

    @patch('pulp.server.controllers.repository.model.Repository.objects')
    @patch('pulp.server.controllers.repository.connection.get_database')
    def test_calculate_counts(self, mock_get_db, m_repo_objects):
        """
        Test the calculation of the unit counts.
        This is only a marginally useful test as 90% of the work is done by the
        mongo server
        """
        mock_get_db.return_value.command.return_value = \
            {'result': [{'_id': 'type_1', 'sum': 5}, {'_id': 'type_2', 'sum': 3}]}
        repo = MagicMock(repo_id='foo')
        repo_controller.rebuild_content_unit_counts(repo)

        expected_pipeline = [
            {'$match': {'repo_id': 'foo'}},
            {'$group': {'_id': '$unit_type_id', 'sum': {'$sum': 1}}}]

        mock_get_db.return_value.command.assert_called_once_with(
            'aggregate', 'repo_content_units', pipeline=expected_pipeline
        )
        self.assertDictEqual(repo.content_unit_counts, {'type_1': 5, 'type_2': 3})
        repo.save.assert_called_once_with()


class AssociateSingleUnitTests(unittest.TestCase):

    @patch('pulp.server.controllers.repository.model.RepositoryContentUnit.objects')
    @patch('pulp.server.controllers.repository.dateutils.format_iso8601_utc_timestamp')
    def test_unit_association(self, mock_get_timestamp, mock_rcu_objects):
        mock_get_timestamp.return_value = 'foo_tstamp'
        test_unit = DemoModel(id='bar', key_field='baz')
        repo = MagicMock(repo_id='foo')
        repo_controller.associate_single_unit(repo, test_unit)
        mock_rcu_objects.assert_called_once_with(
            repo_id='foo',
            unit_id='bar',
            unit_type_id=DemoModel._content_type_id.default
        )
        mock_rcu_objects.return_value.update_one.assert_called_once_with(
            set_on_insert__created='foo_tstamp',
            set__updated='foo_tstamp',
            upsert=True)


class TestDisassociateUnits(unittest.TestCase):

    @patch('pulp.server.controllers.repository.model.RepositoryContentUnit.objects')
    def test_disaccociate_units(self, m_rcu_objects):
        """"
        Test that multiple objects are all deleted
        """
        test_unit1 = DemoModel(id='bar', key_field='baz')
        test_unit2 = DemoModel(id='baz', key_field='baz')
        repo = MagicMock(repo_id='foo')
        repo_controller.disassociate_units(repo, [test_unit1, test_unit2])
        m_rcu_objects.assert_called_once_with(repo_id='foo', unit_id__in=['bar', 'baz'])
        m_rcu_objects.return_value.delete.assert_called_once()


@mock.patch('pulp.server.controllers.repository.dist_controller')
@mock.patch('pulp.server.controllers.repository.importer_controller')
@mock.patch('pulp.server.controllers.repository.manager_factory')
@mock.patch('pulp.server.controllers.repository.model.Repository')
class TestCreateRepo(unittest.TestCase):
    """
    Tests for repo creation.
    """

    def test_invalid_repo_id(self, m_repo_model, m_factory, m_imp_ctrl, m_dist_ctrl):
        """
        Test creating a repository with invalid characters.
        """
        m_repo_model().save.side_effect = mongoengine.ValidationError
        self.assertRaises(pulp_exceptions.InvalidValue, repo_controller.create_repo,
                          'invalid_chars&')

    def test_minimal_creation(self, m_repo_model, m_factory, m_imp_ctrl, m_dist_ctrl):
        """
        Test creating a repository with only the required parameters.
        """
        repo = repo_controller.create_repo('m_repo')
        m_repo_model.assert_called_once_with(repo_id='m_repo', notes=None, display_name=None,
                                             description=None)
        repo.save.assert_called_once_with()
        self.assertTrue(repo is m_repo_model.return_value)

    def test_duplicate_repo(self, m_repo_model, m_factory, m_imp_ctrl, m_dist_ctrl):
        """
        Test creation of a repository that already exists.
        """
        m_repo_model.return_value.save.side_effect = mongoengine.NotUniqueError
        self.assertRaises(pulp_exceptions.DuplicateResource, repo_controller.create_repo,
                          'm_repo')

    def test_invalid_notes(self, m_repo_model, m_factory, m_imp_ctrl, m_dist_ctrl):
        """
        Test creation of a repository that has invalid notes.
        """
        m_repo_model.return_value.save.side_effect = mongoengine.ValidationError
        self.assertRaises(pulp_exceptions.InvalidValue, repo_controller.create_repo, 'm_repo')

    def test_create_with_importer_config(self, m_repo_model, m_factory, m_imp_ctrl, m_dist_ctrl):
        """
        Test creation of a repository with a specified importer configuration.
        """
        repo = repo_controller.create_repo('m_repo', importer_type_id='mock_type',
                                           importer_repo_plugin_config='mock_config')
        m_imp_ctrl.set_importer.assert_called_once_with('m_repo', 'mock_type', 'mock_config')
        self.assertTrue(repo is m_repo_model.return_value)
        self.assertEqual(repo.delete.call_count, 0)

    def test_create_with_importer_config_exception(self, m_repo_model, m_factory, m_imp_ctrl,
                                                   m_dist_ctrl):
        """
        Test creation of a repository when the importer configuration fails.
        """
        m_imp_ctrl.set_importer.side_effect = MockException
        repo_inst = m_repo_model.return_value
        self.assertRaises(MockException, repo_controller.create_repo, 'm_repo',
                          importer_type_id='id', importer_repo_plugin_config='mock_config')
        m_imp_ctrl.set_importer.assert_called_once_with('m_repo', 'id', 'mock_config')
        self.assertEqual(repo_inst.delete.call_count, 1)

    def test_create_with_distributor_list_not_list(self, m_repo_model, m_factory, m_imp_ctrl,
                                                   m_dist_ctrl):
        """
        Test creation of a repository when distributor list is invalid.
        """
        self.assertRaises(pulp_exceptions.InvalidValue, repo_controller.create_repo,
                          'm_repo', distributor_list='non-list')
        self.assertEqual(m_repo_model.call_count, 0)

    def test_create_with_invalid_dists_in_dist_list(self, m_repo_model, m_factory, m_imp_ctrl,
                                                    m_dist_ctrl):
        """
        Test creation of a repository when one of the distributors is invalid.
        """
        self.assertRaises(pulp_exceptions.InvalidValue, repo_controller.create_repo,
                          'm_repo', distributor_list=['not_dict'])
        self.assertEqual(m_repo_model.call_count, 0)

    def test_create_with_valid_distributors(self, m_repo_model, m_factory, m_imp_ctrl, m_dist_ctrl):
        """
        Test creation of a repository and the proper configuration of distributors.
        """
        dist = {'distributor_type_id': 'type', 'distributor_config': {}, 'distributor_id': 'dist'}
        repo = repo_controller.create_repo('repo', distributor_list=[dist])
        self.assertEqual(repo.delete.call_count, 0)
        m_dist_ctrl.add_distributor.assert_called_once_with('repo', 'type', {}, False, 'dist')

    def test_create_with_distributor_exception(self, m_repo_model, m_factory, m_imp_ctrl,
                                               m_dist_ctrl):
        """
        Test creation of a repository when distributor configuration fails.
        """
        m_dist_ctrl.add_distributor.side_effect = MockException
        repo_inst = m_repo_model.return_value
        self.assertRaises(MockException, repo_controller.create_repo, 'm_repo',
                          distributor_list=[{}])
        self.assertEqual(repo_inst.delete.call_count, 1)


class TestQueueDelete(unittest.TestCase):
    """
    Tests for dispatching repository delete tasks.
    """

    @mock.patch('pulp.server.controllers.repository.delete')
    @mock.patch('pulp.server.controllers.repository.tags')
    def test_dispatch(self, mock_tags, mock_delete):
        """
        Test that the appropriate task is dispatched with the correct arguments.
        """
        mock_task_tags = [mock_tags.resource_tag.return_value, mock_tags.action_tag.return_value]
        async_result = repo_controller.queue_delete('m_repo')
        mock_delete.apply_async_with_reservation.assert_called_once_with(
            mock_tags.RESOURCE_REPOSITORY_TYPE, 'm_repo', ['m_repo'], tags=mock_task_tags)
        self.assertTrue(async_result is mock_delete.apply_async_with_reservation())


@mock.patch('pulp.server.controllers.repository.dist_controller')
@mock.patch('pulp.server.controllers.repository.importer_controller')
@mock.patch('pulp.server.controllers.repository.TaskResult')
@mock.patch('pulp.server.controllers.repository.RepoSyncResult')
@mock.patch('pulp.server.controllers.repository.RepoPublishResult')
@mock.patch('pulp.server.controllers.repository.RepoContentUnit')
@mock.patch('pulp.server.controllers.repository.model')
@mock.patch('pulp.server.controllers.repository.manager_factory')
class TestDelete(unittest.TestCase):
    """
    Tests for deleting a repository.
    """

    def test_delete_no_importers_or_distributors(self, m_factory, m_model, m_content, m_publish,
                                                 m_sync, m_task_result, m_imp_ctrl, m_dist_ctrl):
        """
        Test a simple repository delete when there are no importers or distributors.
        """
        m_model.Importer.objects.return_value.first.return_value = None
        m_model.Distributor.objects.return_value.__iter__.return_value = []
        m_repo = m_model.Repository.objects.get_repo_or_missing_resource.return_value
        mock_group_manager = m_factory.repo_group_manager.return_value
        mock_consumer_bind_manager = m_factory.consumer_bind_manager.return_value
        mock_consumer_bind_manager.find_by_repo.return_value = []

        result = repo_controller.delete('foo-repo')

        m_repo.delete.assert_called_once_with()
        pymongo_args = {'repo_id': 'foo-repo'}
        pymongo_kwargs = {}
        m_model.Distributor.objects.return_value.delete.assert_called_once_with()
        m_model.Importer.objects.return_value.delete.assert_called_once_with()
        m_sync.get_collection().remove.assert_called_once_with(pymongo_args, **pymongo_kwargs)
        m_publish.get_collection().remove.assert_called_once_with(pymongo_args, **pymongo_kwargs)
        m_content.get_collection().remove.assert_called_once_with(pymongo_args, **pymongo_kwargs)
        mock_group_manager.remove_repo_from_groups.assert_called_once_with('foo-repo')
        m_task_result.assert_called_once_with(error=None, spawned_tasks=[])
        self.assertTrue(result is m_task_result.return_value)

    @mock.patch('pulp.server.controllers.repository.consumer_controller')
    def test_delete_imforms_other_collections(self, mock_consumer_ctrl, m_factory, m_model,
                                              m_content, m_publish, m_sync, m_task_result,
                                              m_imp_ctrl, m_dist_ctrl):
        """
        Test that other collections are correctly informed when a repository is deleted.
        """
        m_model.Importer.objects.return_value.first.return_value = None
        m_dist = mock.MagicMock()
        m_model.Distributor.objects.return_value.__iter__.return_value = [m_dist]
        m_repo = m_model.Repository.objects.get_repo_or_missing_resource.return_value
        mock_group_manager = m_factory.repo_group_manager.return_value
        mock_consumer_bind_manager = m_factory.consumer_bind_manager.return_value
        mock_consumer_bind_manager.find_by_repo.return_value = [{
            'consumer_id': 'mock_con', 'repo_id': 'm_repo', 'distributor_id': 'm_dist'
        }]
        mock_consumer_ctrl.unbind.return_value.spawned_tasks = ['mock_task']

        result = repo_controller.delete('foo-repo')

        m_repo.delete.assert_called_once_with()
        pymongo_args = {'repo_id': 'foo-repo'}
        pymongo_kwargs = {}
        m_dist_ctrl.delete.assert_called_once_with(m_dist.repo_id, m_dist.distributor_id)
        m_model.Distributor.objects.return_value.delete.assert_called_once_with()
        m_model.Importer.objects.return_value.delete.assert_called_once_with()
        m_sync.get_collection().remove.assert_called_once_with(pymongo_args, **pymongo_kwargs)
        m_publish.get_collection().remove.assert_called_once_with(pymongo_args, **pymongo_kwargs)
        m_content.get_collection().remove.assert_called_once_with(pymongo_args, **pymongo_kwargs)
        mock_consumer_ctrl.unbind.assert_called_once_with('mock_con', 'm_repo', 'm_dist', {})
        mock_group_manager.remove_repo_from_groups.assert_called_once_with('foo-repo')
        m_task_result.assert_called_once_with(error=None, spawned_tasks=['mock_task'])
        self.assertTrue(result is m_task_result.return_value)

    def test_delete_with_dist_and_imp_errors(self, m_factory, m_model, m_content, m_publish,
                                             m_sync, m_task_result, m_imp_ctrl, m_dist_ctrl):
        """
        Test repository delete when the other collections raise errors.
        """
        m_model.Importer.objects.return_value.first.return_value = mock.MagicMock(
            importer_type_id='mock_type')
        m_imp_ctrl.remove_importer.side_effect = MockException
        m_dist_ctrl.delete.side_effect = MockException
        m_model.Distributor.objects.return_value.__iter__.return_value = [
            mock.MagicMock(id='mock_d1'), mock.MagicMock(id='mock_d2')]
        m_repo = m_model.Repository.objects.get_repo_or_missing_resource.return_value
        mock_group_manager = m_factory.repo_group_manager.return_value
        mock_consumer_bind_manager = m_factory.consumer_bind_manager.return_value

        try:
            repo_controller.delete('foo-repo')
        except pulp_exceptions.PulpExecutionException, e:
            pass
        else:
            raise AssertionError('Distributor/importer errors should raise a '
                                 'PulpExecutionException.')

        m_repo.delete.assert_called_once_with()
        pymongo_args = {'repo_id': 'foo-repo'}
        pymongo_kwargs = {}

        m_dist_ctrl.remove_distributor.has_calls([
            mock.call('foo-repo', 'mock_d1'), mock.call('foo-repo', 'mock_d2')])

        # Direct db manipulation should still occur with distributor errors.
        m_model.Distributor.objects.return_value.delete.assert_called_once_with()
        m_model.Importer.objects.return_value.delete.assert_called_once_with()
        m_sync.get_collection().remove.assert_called_once_with(pymongo_args, **pymongo_kwargs)
        m_publish.get_collection().remove.assert_called_once_with(pymongo_args, **pymongo_kwargs)
        m_content.get_collection().remove.assert_called_once_with(pymongo_args, **pymongo_kwargs)
        mock_group_manager.remove_repo_from_groups.assert_called_once_with('foo-repo')

        # Consumers should not be unbound if there are distribur errors.
        self.assertEqual(m_task_result.call_count, 0)
        self.assertEqual(mock_consumer_bind_manager.find_by_repo.call_count, 0)

        # Exceptions should be reraised as child execptions.
        self.assertEqual(len(e.child_exceptions), 3)
        self.assertTrue(isinstance(e.child_exceptions[0], MockException))
        self.assertTrue(isinstance(e.child_exceptions[1], MockException))
        self.assertTrue(isinstance(e.child_exceptions[2], MockException))

    def test_delete_content_errors(self, m_factory, m_model, m_content, m_publish,
                                   m_sync, m_task_result, m_imp_ctrl, m_dist_ctrl):
        """
        Test delete repository when the content collection raises errors.
        """

        m_model.Importer.objects.return_value.first.return_value = None
        m_model.Distributor.objects.return_value.__iter__.return_value = []
        m_repo = m_model.Repository.objects.get_repo_or_missing_resource.return_value
        mock_group_manager = m_factory.repo_group_manager.return_value
        mock_consumer_bind_manager = m_factory.consumer_bind_manager.return_value
        mock_consumer_bind_manager.find_by_repo.return_value = []
        m_content.get_collection().remove.side_effect = MockException

        try:
            repo_controller.delete('foo-repo')
        except pulp_exceptions.PulpExecutionException, e:
            pass
        else:
            raise AssertionError('Content errors should raise a PulpExecutionException.')

        m_repo.delete.assert_called_once_with()
        pymongo_args = {'repo_id': 'foo-repo'}
        pymongo_kwargs = {}

        m_model.Distributor.objects.return_value.delete.assert_called_once_with()
        m_model.Importer.objects.return_value.delete.assert_called_once_with()
        m_sync.get_collection().remove.assert_called_once_with(pymongo_args, **pymongo_kwargs)
        m_publish.get_collection().remove.assert_called_once_with(pymongo_args, **pymongo_kwargs)
        m_content.get_collection().remove.assert_called_once_with(pymongo_args, **pymongo_kwargs)
        mock_group_manager.remove_repo_from_groups.assert_called_once_with('foo-repo')

        # Consumers should not be unbound if there are distribur errors.
        self.assertEqual(m_task_result.call_count, 0)
        self.assertEqual(mock_consumer_bind_manager.find_by_repo.call_count, 0)

        # Exceptions should be reraised as child execptions.
        self.assertEqual(len(e.child_exceptions), 1)
        self.assertTrue(isinstance(e.child_exceptions[0], MockException))

    @mock.patch('pulp.server.controllers.repository.consumer_controller')
    @mock.patch('pulp.server.controllers.repository.error_codes.PLP0007')
    @mock.patch('pulp.server.controllers.repository.pulp_exceptions.PulpCodedException')
    def test_delete_consumer_bind_error(self, mock_coded_exception, mock_pulp_error,
                                        mock_consumer_ctrl, m_factory, m_model, m_content,
                                        m_publish, m_sync, m_task_result, m_imp_ctrl, m_dist_ctrl):
        """
        Test repository delete when consumer bind collection raises an error.
        """
        m_model.Importer.objects.return_value.first.return_value = None
        m_model.Distributor.objects.return_value.__iter__.return_value = []
        m_repo = m_model.Repository.objects.get_repo_or_missing_resource.return_value
        mock_group_manager = m_factory.repo_group_manager.return_value
        mock_consumer_bind_manager = m_factory.consumer_bind_manager.return_value
        mock_consumer_bind_manager.find_by_repo.return_value = [{
            'consumer_id': 'mock_con', 'repo_id': 'm_repo', 'distributor_id': 'm_dist'
        }]
        mock_consumer_ctrl.unbind.side_effect = MockException

        result = repo_controller.delete('foo-repo')
        m_repo.delete.assert_called_once_with()
        pymongo_args = {'repo_id': 'foo-repo'}
        pymongo_kwargs = {}

        m_model.Distributor.objects.return_value.delete.assert_called_once_with()
        m_model.Importer.objects.return_value.delete.assert_called_once_with()
        m_sync.get_collection().remove.assert_called_once_with(pymongo_args, **pymongo_kwargs)
        m_publish.get_collection().remove.assert_called_once_with(pymongo_args, **pymongo_kwargs)
        m_content.get_collection().remove.assert_called_once_with(pymongo_args, **pymongo_kwargs)
        mock_group_manager.remove_repo_from_groups.assert_called_once_with('foo-repo')
        mock_consumer_ctrl.unbind.assert_called_once_with('mock_con', 'm_repo', 'm_dist', {})

        expected_error = mock_coded_exception.return_value
        mock_coded_exception.assert_called_once_with(mock_pulp_error, repo_id='foo-repo')
        self.assertEqual(len(expected_error.child_exceptions), 1)
        self.assertTrue(isinstance(expected_error.child_exceptions[0], MockException))
        m_task_result.assert_called_once_with(error=expected_error, spawned_tasks=[])
        self.assertTrue(result is m_task_result.return_value)


class TestUpdateRepoAndPlugins(unittest.TestCase):
    """
    Tests for updating a repository and its related collections.
    """

    @mock.patch('pulp.server.controllers.repository.TaskResult')
    def test_no_change(self, m_task_result):
        """
        No change should be made to a repository if update is called without actual changes.
        """
        m_repo = mock.MagicMock()
        result = repo_controller.update_repo_and_plugins(m_repo, None, None, None)
        self.assertTrue(result is m_task_result.return_value)
        m_task_result.assert_called_once_with(m_repo, None, [])

    @mock.patch('pulp.server.controllers.repository.TaskResult')
    def test_update_with_delta(self, m_task_result):
        """
        Test that the repo_delta is passed to the appropriate helper function.
        """
        m_repo = mock.MagicMock()
        result = repo_controller.update_repo_and_plugins(m_repo, {'mock': 'delta'}, None, None)
        self.assertTrue(result is m_task_result.return_value)
        m_task_result.assert_called_once_with(m_repo, None, [])
        m_repo.update_from_delta.assert_called_once_with({'mock': 'delta'})
        m_repo.save.assert_called_once_with()

    def test_update_with_invalid_delta(self):
        """
        Ensure that a PulpCodedValidationException is raised if the delta is not a valid dictionary.
        """
        m_repo = mock.MagicMock()
        self.assertRaises(pulp_exceptions.PulpCodedValidationException,
                          repo_controller.update_repo_and_plugins,
                          m_repo, 'non-dict', None, None)

    @mock.patch('pulp.server.controllers.repository.importer_controller')
    @mock.patch('pulp.server.controllers.repository.manager_factory')
    @mock.patch('pulp.server.controllers.repository.TaskResult')
    def test_update_with_importer(self, m_task_result, m_factory, m_imp_ctrl):
        """
        Ensure that the importer manager is invoked to update the importer when specified.
        """
        m_repo = mock.MagicMock()
        result = repo_controller.update_repo_and_plugins(m_repo, None, 'imp_config', None)
        m_imp_ctrl.update_importer_config.assert_called_once_with(m_repo.repo_id, 'imp_config')
        self.assertTrue(result is m_task_result.return_value)
        m_task_result.assert_called_once_with(m_repo, None, [])

    @mock.patch('pulp.server.controllers.repository.TaskResult')
    @mock.patch('pulp.server.controllers.repository.dist_controller')
    @mock.patch('pulp.server.controllers.repository.tags')
    def test_update_with_distributors(self, mock_tags, m_dist_ctrl, m_task_result):
        """
        Ensure that the distributor manager is invoked to update the distributors when specified.
        """
        m_repo = mock.MagicMock()
        dist_configs = {'id1': 'conf1', 'id2': 'conf2'}
        result = repo_controller.update_repo_and_plugins(m_repo, None, None, dist_configs)
        mock_async = m_dist_ctrl.update.apply_async_with_reservation.return_value

        mock_task_tags = [mock_tags.resource_tag.return_value, mock_tags.resource_tag.return_value,
                          mock_tags.action_tag.return_value]
        m_dist_ctrl.update.apply_async_with_reservation.assert_has_calls([
            mock.call(mock_tags.RESOURCE_REPOSITORY_TYPE, m_repo.repo_id,
                      [m_repo.repo_id, 'id1', 'conf1', None], tags=mock_task_tags),
            mock.call(mock_tags.RESOURCE_REPOSITORY_TYPE, m_repo.repo_id,
                      [m_repo.repo_id, 'id2', 'conf2', None], tags=mock_task_tags),
        ], any_order=True)
        m_task_result.assert_called_once_with(m_repo, None, [mock_async, mock_async])
        self.assertTrue(result is m_task_result.return_value)


class TestUpdateLastUnitAdded(unittest.TestCase):
    """
    Tests for update last unit added.
    """

    @mock.patch('pulp.server.controllers.repository.model.Repository.objects')
    @mock.patch('pulp.server.controllers.repository.dateutils')
    def test_update_last_unit_added(self, mock_date, m_repo_qs):
        """
        Ensure that the last_unit_added field is correctly updated.
        """
        m_repo = m_repo_qs.get_repo_or_missing_resource.return_value
        repo_controller.update_last_unit_added('m_repo')
        self.assertEqual(m_repo.last_unit_added, mock_date.now_utc_datetime_with_tzinfo())
        m_repo.save.assert_called_once_with()


class TestUpdateLastUnitRemoved(unittest.TestCase):
    """
    Tests for update last unit removed.
    """

    @mock.patch('pulp.server.controllers.repository.model.Repository.objects')
    @mock.patch('pulp.server.controllers.repository.dateutils')
    def test_update_last_unit_removed(self, mock_date, m_repo_qs):
        """
        Ensure that the last_unit_removed field is correctly updated.
        """
        m_repo = m_repo_qs.get_repo_or_missing_resource.return_value
        repo_controller.update_last_unit_removed('m_repo')
        self.assertEqual(m_repo.last_unit_removed, mock_date.now_utc_datetime_with_tzinfo())
        m_repo.save.assert_called_once_with()


@mock.patch('pulp.server.controllers.repository.rebuild_content_unit_counts')
@mock.patch('pulp.server.controllers.repository.sys')
@mock.patch('pulp.server.controllers.repository.register_sigterm_handler')
@mock.patch('pulp.server.controllers.repository._now_timestamp')
@mock.patch('pulp.server.controllers.repository.manager_factory')
@mock.patch('pulp.server.controllers.repository.RepoSyncResult')
@mock.patch('pulp.server.controllers.repository.RepoSyncConduit')
@mock.patch('pulp.server.controllers.repository.common_utils.get_working_directory')
@mock.patch('pulp.server.controllers.repository.PluginCallConfiguration')
@mock.patch('pulp.server.controllers.repository.plugin_api')
@mock.patch('pulp.server.controllers.repository.model')
class TestSync(unittest.TestCase):
    """
    Tests for syncing a repository.
    """

    def test_sync_no_importer_inst(self, m_model, mock_plugin_api, *unused):
        """
        Raise when importer is not associated with a plugin.
        """
        mock_plugin_api.get_importer_by_id.side_effect = plugin_exceptions.PluginNotFound
        self.assertRaises(pulp_exceptions.MissingResource, repo_controller.sync, 'm_repo')

    def test_sync_sigterm_error(self, m_model, mock_plugin_api,
                                mock_plug_conf, mock_wd, mock_conduit, mock_result, m_factory,
                                mock_now, mock_reg_sig, mock_sys, mock_rebuild):
        """
        An error_result should be built when there is an error with the sigterm handler.
        """
        m_repo = m_model.Repository.objects.get_repo_or_missing_resource.return_value
        mock_imp = mock.MagicMock()
        mock_imp_inst = m_model.Importer.objects.get_or_404.return_value
        mock_plugin_api.get_importer_by_id.return_value = (mock_imp, 'mock_conf')
        expected_exp = MockException()
        sync_func = mock_reg_sig.return_value
        sync_func.side_effect = expected_exp
        self.assertRaises(MockException, repo_controller.sync, 'm_repo')
        mock_result.error_result.assert_called_once_with(
            m_repo.repo_id, mock_imp_inst['id'], mock_imp_inst['importer_type_id'], mock_now(),
            mock_now(), expected_exp, mock_sys.exc_info.return_value[2]
        )
        mock_reg_sig.assert_called_once_with(mock_imp.sync_repo, mock_imp.cancel_sync_repo)
        sync_func.assert_called_once_with(m_repo.to_transfer_repo(), mock_conduit(),
                                          mock_plug_conf())

        # It is now platform's responsiblity to update plugin content unit counts
        self.assertTrue(mock_rebuild.called, "rebuild_content_unit_counts must be called")

    @mock.patch('pulp.server.controllers.repository._queue_auto_publish_tasks')
    @mock.patch('pulp.server.controllers.repository.TaskResult')
    def test_sync_canceled(self, m_task_result, mock_spawn_auto_pub, m_model,
                           mock_plugin_api, mock_plug_conf, mock_wd, mock_conduit, mock_result,
                           m_factory, mock_now, mock_reg_sig, mock_sys, mock_rebuild):
        """
        Test the behavior of sync when the task is canceled.
        """
        mock_spawn_auto_pub.return_value = []
        mock_fire_man = m_factory.event_fire_manager()
        m_repo = m_model.Repository.objects.get_repo_or_missing_resource.return_value
        m_sync_result = repo_controller.SyncReport(
            success_flag=False, added_count=1, updated_count=2, removed_count=3, summary='sum',
            details='deets')
        sync_func = mock_reg_sig.return_value
        sync_func.return_value = m_sync_result
        m_sync_result.canceled_flag = True

        mock_result.RESULT_CANCELED = 'canceled'
        m_repo = m_model.Repository.objects.get_repo_or_missing_resource.return_value
        mock_imp = mock.MagicMock()
        mock_imp_inst = m_model.Importer.objects.get_or_404.return_value
        mock_plugin_api.get_importer_by_id.return_value = (mock_imp, 'mock_conf')

        actual_result = repo_controller.sync('mock_id')
        mock_result.expected_result.assert_called_once_with(
            m_repo.repo_id, mock_imp_inst['id'], mock_imp_inst['importer_type_id'],
            mock_now(), mock_now(), m_sync_result.added_count, m_sync_result.updated_count,
            m_sync_result.removed_count, m_sync_result.summary, m_sync_result.details,
            'canceled'
        )
        m_model.Importer.objects().update.assert_called_once_with(set__last_sync=mock_now())
        mock_result.get_collection().save.assert_called_once_with(mock_result.expected_result())
        mock_fire_man.fire_repo_sync_finished.assert_called_once_with(mock_result.expected_result())
        self.assertTrue(actual_result is m_task_result.return_value)

        # It is now platform's responsiblity to update plugin content unit counts
        self.assertTrue(mock_rebuild.called, "rebuild_content_unit_counts must be called")

    @mock.patch('pulp.server.controllers.repository._queue_auto_publish_tasks')
    @mock.patch('pulp.server.controllers.repository.TaskResult')
    def test_sync_success(self, m_task_result, mock_spawn_auto_pub, m_model,
                          mock_plugin_api, mock_plug_conf, mock_wd,
                          mock_conduit, mock_result, m_factory, mock_now, mock_reg_sig,
                          mock_sys, mock_rebuild):
        """
        Test repository sync when everything works as expected.
        """
        mock_spawn_auto_pub.return_value = []
        mock_fire_man = m_factory.event_fire_manager()
        m_repo = m_model.Repository.objects.get_repo_or_missing_resource.return_value
        m_sync_result = repo_controller.SyncReport(
            success_flag=False, added_count=1, updated_count=2, removed_count=3, summary='sum',
            details='deets')
        sync_func = mock_reg_sig.return_value
        sync_func.return_value = m_sync_result
        m_sync_result.canceled_flag = False
        m_sync_result.success_flag = True

        mock_result.RESULT_SUCCESS = 'success'
        m_repo = m_model.Repository.objects.get_repo_or_missing_resource.return_value
        mock_imp = mock.MagicMock()
        mock_imp_inst = m_model.Importer.objects.get_or_404.return_value
        mock_plugin_api.get_importer_by_id.return_value = (mock_imp, 'mock_conf')

        actual_result = repo_controller.sync('mock_id')
        mock_result.expected_result.assert_called_once_with(
            m_repo.repo_id, mock_imp_inst['id'], mock_imp_inst['importer_type_id'],
            mock_now(), mock_now(), m_sync_result.added_count, m_sync_result.updated_count,
            m_sync_result.removed_count, m_sync_result.summary, m_sync_result.details,
            'success'
        )
        m_model.Importer.objects().update.assert_called_once_with(set__last_sync=mock_now())
        mock_result.get_collection().save.assert_called_once_with(mock_result.expected_result())
        mock_fire_man.fire_repo_sync_finished.assert_called_once_with(mock_result.expected_result())
        self.assertEqual(mock_imp_inst.id, mock_conduit.call_args_list[0][0][2])
        self.assertTrue(actual_result is m_task_result.return_value)

        # It is now platform's responsiblity to update plugin content unit counts
        self.assertTrue(mock_rebuild.called, "rebuild_content_unit_counts must be called")

    @mock.patch('pulp.server.controllers.repository.TaskResult')
    def test_sync_failed(self, m_task_result, m_model, mock_plugin_api, mock_plug_conf,
                         mock_wd, mock_conduit, mock_result, m_factory, mock_now, mock_reg_sig,
                         mock_sys, mock_rebuild):
        """
        Test repository sync when the result is failure.
        """
        mock_fire_man = m_factory.event_fire_manager()
        m_repo = m_model.Repository.objects.get_repo_or_missing_resource.return_value
        m_sync_result = repo_controller.SyncReport(
            success_flag=False, added_count=1, updated_count=2, removed_count=3, summary='sum',
            details='deets')
        mock_result.RESULT_FAILED = 'failed'
        mock_result.expected_result.return_value.result = mock_result.RESULT_FAILED
        sync_func = mock_reg_sig.return_value
        sync_func.return_value = m_sync_result
        m_sync_result.canceled_flag = False
        m_sync_result.success_flag = False

        m_repo = m_model.Repository.objects.get_repo_or_missing_resource.return_value
        mock_imp = mock.MagicMock()
        mock_imp_inst = m_model.Importer.objects.get_or_404.return_value
        mock_plugin_api.get_importer_by_id.return_value = (mock_imp, 'mock_conf')

        self.assertRaises(pulp_exceptions.PulpExecutionException, repo_controller.sync, 'mock_id')
        mock_result.expected_result.assert_called_once_with(
            m_repo.repo_id, mock_imp_inst['id'], mock_imp_inst['importer_type_id'],
            mock_now(), mock_now(), m_sync_result.added_count, m_sync_result.updated_count,
            m_sync_result.removed_count, m_sync_result.summary, m_sync_result.details,
            'failed'
        )
        m_model.Importer.objects().update.assert_called_once_with(set__last_sync=mock_now())
        mock_result.get_collection().save.assert_called_once_with(mock_result.expected_result())
        mock_fire_man.fire_repo_sync_finished.assert_called_once_with(mock_result.expected_result())

        # It is now platform's responsiblity to update plugin content unit counts
        self.assertTrue(mock_rebuild.called, "rebuild_content_unit_counts must be called")

    @mock.patch('pulp.server.controllers.repository._queue_auto_publish_tasks')
    @mock.patch('pulp.server.controllers.repository._')
    @mock.patch('pulp.server.controllers.repository._logger')
    @mock.patch('pulp.server.controllers.repository.TaskResult')
    def test_sync_invalid_sync_report(self, m_task_result, mock_logger, mock_gettext,
                                      mock_spawn_auto_pub, m_model, mock_plugin_api,
                                      mock_plug_conf, mock_wd, mock_conduit, mock_result,
                                      m_factory, mock_now, mock_reg_sig, mock_sys, mock_rebuild):
        """
        Test repository sync when the sync report is not valid.
        """
        mock_spawn_auto_pub.return_value = []
        mock_fire_man = m_factory.event_fire_manager()
        m_repo = m_model.Repository.objects.get_repo_or_missing_resource.return_value
        mock_result.RESULT_ERROR = 'err'

        m_repo = m_model.Repository.objects.get_repo_or_missing_resource.return_value
        mock_imp = mock.MagicMock()
        mock_imp_inst = m_model.Importer.objects.get_or_404.return_value
        mock_plugin_api.get_importer_by_id.return_value = (mock_imp, 'mock_conf')

        result = repo_controller.sync('mock_id')
        mock_result.expected_result.assert_called_once_with(
            m_repo.repo_id, mock_imp_inst['id'], mock_imp_inst['importer_type_id'],
            mock_now(), mock_now(), -1, -1, -1, mock_gettext(), mock_gettext(),
            'err'
        )
        m_model.Importer.objects().update.assert_called_once_with(set__last_sync=mock_now())
        mock_result.get_collection().save.assert_called_once_with(mock_result.expected_result())
        mock_fire_man.fire_repo_sync_finished.assert_called_once_with(mock_result.expected_result())
        self.assertTrue(result is m_task_result.return_value)

        # It is now platform's responsiblity to update plugin content unit counts
        self.assertTrue(mock_rebuild.called, "rebuild_content_unit_counts must be called")


@mock.patch('pulp.server.controllers.repository.model.Distributor.objects')
@mock.patch('pulp.server.controllers.repository.model.Repository.objects')
@mock.patch('pulp.server.controllers.repository.manager_factory')
class TestPublish(unittest.TestCase):
    """
    Tests for publishing a repository.
    """
    @mock.patch('pulp.server.controllers.repository.common_utils')
    @mock.patch('pulp.server.controllers.repository._do_publish')
    @mock.patch('pulp.server.controllers.repository.PluginCallConfiguration')
    @mock.patch('pulp.server.controllers.repository.RepoPublishConduit')
    @mock.patch('pulp.server.controllers.repository._get_distributor_instance_and_config')
    def test_expected(self, mock_get_dist_inst, mock_pub_conduit, mock_plug_call_conf, mock_do_pub,
                      m_common, mock_f, m_repo_qs, m_dist_qs):
        """
        Test publish when all goes as expected.
        """
        mock_fire = mock_f.event_fire_manager()
        mock_get_dist_inst.return_value = ('inst', 'conf')
        result = repo_controller.publish('repo', 'dist', 'override')

        mock_get_dist_inst.assert_called_once_with('repo', 'dist')
        mock_pub_conduit.assert_called_once_with('repo', 'dist')
        mock_plug_call_conf.assert_called_once_with(
            'conf', m_dist_qs.get_or_404.return_value.config, 'override')
        m_repo = m_repo_qs.get_repo_or_missing_resource.return_value
        mock_fire.fire_repo_publish_started.assert_called_once_with('repo', 'dist')
        mock_do_pub.assert_called_once_with(m_repo, 'dist', 'inst', m_repo.to_transfer_repo(),
                                            mock_pub_conduit(), mock_plug_call_conf())
        mock_fire.fire_repo_publish_finished.assert_called_once_with(mock_do_pub())
        self.assertTrue(
            m_repo.to_transfer_repo().working_dir is m_common.get_working_directory())
        self.assertTrue(result is mock_do_pub())


class TestGetDistributorInstanceAndConfig(unittest.TestCase):
    """
    Tests for retrieving a distributor instance and config.
    """

    @mock.patch('pulp.server.controllers.repository.plugin_api')
    @mock.patch('pulp.server.controllers.repository.model.Distributor.objects')
    def test_get_as_expected(self, m_dist_qs, mock_plug_api):
        """
        Test retrieving distributor information when everything goes as expected.
        """
        mock_plug_api.get_distributor_by_id.return_value = ('dist', 'conf')
        result = repo_controller._get_distributor_instance_and_config('repo', 'dist')
        m_dist_qs.get_or_404.assert_called_once_with(repo_id='repo', distributor_id='dist')
        mock_plug_api.get_distributor_by_id.assert_called_once_with(
            m_dist_qs.get_or_404.return_value.distributor_type_id)
        self.assertEqual(result, mock_plug_api.get_distributor_by_id.return_value)


@mock.patch('pulp.server.controllers.repository._')
@mock.patch('pulp.server.controllers.repository._logger')
@mock.patch('pulp.server.controllers.repository.register_sigterm_handler')
@mock.patch('pulp.server.controllers.repository._now_timestamp')
@mock.patch('pulp.server.controllers.repository.RepoPublishResult')
@mock.patch('pulp.server.controllers.repository.model.Distributor.objects')
class TestDoPublish(unittest.TestCase):
    """
    Tests that other collections are dealt with correctly when publishing a repository.
    """

    @mock.patch('pulp.server.controllers.repository.sys')
    @mock.patch('pulp.server.controllers.repository.pulp_exceptions.PulpCodedException')
    def test_invalid_publish_report(self, mock_e, mock_sys, m_dist_qs, m_repo_pub_result,
                                    mock_now, mock_sig_handler, mock_log, mock_text):
        """
        Test that invalid publish reports should raise.
        """
        m_report = mock_sig_handler.return_value.return_value
        m_report.success_flag = False
        m_repo = mock.MagicMock()
        mock_inst = mock.MagicMock()
        expected_e = MockException()
        mock_e.side_effect = expected_e
        m_dist = m_dist_qs.get_or_404.return_value
        args = [m_repo, 'dist', mock_inst, 'transfer', 'conduit', 'config']

        self.assertRaises(MockException, repo_controller._do_publish, *args)

        mock_sig_handler.assert_called_once_with(mock_inst.publish_repo,
                                                 mock_inst.cancel_publish_repo)

        # Exception should be caught and rereaised. Test the cleanup.
        m_dist_qs.get_or_404.assert_called_once_with(repo_id=m_repo.repo_id, distributor_id='dist')
        m_repo_pub_result.error_result.assert_called_once_with(
            m_repo.repo_id, m_dist.distributor_id, m_dist.distributor_type_id, mock_now(),
            mock_now(), expected_e, mock_sys.exc_info()[2])

        m_repo_pub_result.get_collection().save.assert_called_once_with(
            m_repo_pub_result.error_result())
        mock_log.exception.assert_called_once_with(mock_text())

    def test_successful_publish(self, m_dist_qs, m_repo_pub_result, mock_now,
                                mock_sig_handler, mock_log, mock_text):
        """
        Test publish when everything is as expected.
        """
        fake_report = PublishReport(success_flag=True, summary='summary', details='details')
        mock_sig_handler.return_value.return_value = fake_report
        fake_repo = model.Repository(repo_id='repo1')
        mock_inst = mock.MagicMock()
        m_dist = m_dist_qs.get_or_404.return_value

        result = repo_controller._do_publish(fake_repo, 'dist', mock_inst,
                                             fake_repo.to_transfer_repo(), 'conduit',
                                             'conf')
        self.assertTrue(m_dist.last_publish is mock_now.return_value)
        m_repo_pub_result.expected_result.assert_called_once_with(
            fake_repo.repo_id, m_dist.distributor_id, m_dist.distributor_type_id, mock_now(),
            mock_now(), 'summary', 'details', m_repo_pub_result.RESULT_SUCCESS
        )
        m_repo_pub_result.get_collection().save.assert_called_once_with(
            m_repo_pub_result.expected_result())
        self.assertTrue(result is m_repo_pub_result.expected_result.return_value)

    def test_failed_publish(self, m_dist_qs, m_repo_pub_result, mock_now,
                            mock_sig_handler, mock_log, mock_text):
        """
        Test publish when everything is as expected.
        """
        fake_report = PublishReport(success_flag=False, summary='ouch', details='details')
        mock_sig_handler.return_value.return_value = fake_report
        fake_repo = model.Repository(repo_id='repo1')
        mock_inst = mock.MagicMock()
        m_dist = mock.MagicMock(distributor_id='mock_id', distributor_type_id='m_dist_type')
        m_dist_qs.get_or_404.return_value = m_dist

        with self.assertRaises(pulp_exceptions.PulpCodedException) as assertion:
            repo_controller._do_publish(fake_repo, 'dist', mock_inst, fake_repo.to_transfer_repo(),
                                        mock.MagicMock(), mock.MagicMock())

        e = assertion.exception
        self.assertEqual(e.error_code, error_codes.PLP0034)
        self.assertEqual(e.error_data['distributor_id'], 'dist')
        self.assertEqual(e.error_data['repository_id'], fake_repo.repo_id)
        self.assertEqual(e.error_data['summary'], fake_report.summary)


class TestQueuePublish(unittest.TestCase):
    """
    Tests for queuing a publish task.
    """

    @mock.patch('pulp.server.controllers.repository.action_tag')
    @mock.patch('pulp.server.controllers.repository.resource_tag')
    @mock.patch('pulp.server.controllers.repository.publish')
    def test_expected(self, m_publish, mock_r_tag, mock_a_tag):
        """
        Ensure that the correct args are passed to the dispatched publish task.
        """
        mock_tags = [mock_r_tag.return_value, mock_a_tag.return_value]
        mock_kwargs = {'repo_id': 'repo', 'dist_id': 'dist', 'scheduled_call_id': '123',
                       'publish_config_override': 'over'}
        result = repo_controller.queue_publish('repo', 'dist', overrides='over',
                                               scheduled_call_id='123')
        mock_r_tag.assert_called_once_with(repo_controller.RESOURCE_REPOSITORY_TYPE, 'repo')
        mock_a_tag.assert_called_once_with('publish')
        m_publish.apply_async_with_reservation.assert_called_once_with(
            repo_controller.RESOURCE_REPOSITORY_TYPE, 'repo', tags=mock_tags, kwargs=mock_kwargs)
        self.assertTrue(result is m_publish.apply_async_with_reservation.return_value)


@mock.patch('pulp.server.controllers.repository.model.Repository.objects')
@mock.patch('pulp.server.controllers.repository.RepoSyncResult')
class TestSyncHistory(unittest.TestCase):
    """
    Tests for retrieving sync history.
    """

    def test_sync_history_minimal(self, m_sync_result, m_repo_qs):
        """
        Test that sync history is returned when optional parameters are not passed.
        """
        result = repo_controller.sync_history(None, None, 'm_repo')
        m_sync_result.get_collection().find.assert_called_once_with({'repo_id': 'm_repo'})
        self.assertTrue(result is m_sync_result.get_collection().find.return_value)

    def test_sync_history_with_all_options(self, m_sync_result, m_repo_qs):
        """
        Test that search includes all optional parameters.
        """
        result = repo_controller.sync_history('start', 'end', 'm_repo')
        m_sync_result.get_collection().find.assert_called_once_with(
            {'repo_id': 'm_repo', 'started': {'$gte': 'start', '$lte': 'end'}})
        self.assertTrue(result is m_sync_result.get_collection().find.return_value)


@mock.patch('pulp.server.controllers.repository.model.Distributor.objects')
@mock.patch('pulp.server.controllers.repository.model.Repository.objects')
@mock.patch('pulp.server.controllers.repository.RepoPublishResult')
class TestPublishHistory(unittest.TestCase):
    """
    Tests for retrieving publish history.
    """

    def test_publish_history_minimal(self, m_publish_result, m_repo_qs, m_dist_qs):
        """
        Test that publish history is returned when optional parameters are not passed.
        """
        result = repo_controller.publish_history(None, None, 'm_repo', 'm_dist')
        m_publish_result.get_collection().find.assert_called_once_with(
            {'repo_id': 'm_repo', 'distributor_id': 'm_dist'})
        self.assertTrue(result is m_publish_result.get_collection().find.return_value)

    def test_publish_history_with_all_options(self, m_publish_result, m_repo_qs, m_dist_qs):
        """
        Test that search includes all optional parameters when passed.
        """
        result = repo_controller.publish_history('start', 'end', 'm_repo', 'm_dist')
        m_publish_result.get_collection().find.assert_called_once_with({
            'repo_id': 'm_repo', 'distributor_id': 'm_dist',
            'started': {'$gte': 'start', '$lte': 'end'}
        })
        self.assertTrue(result is m_publish_result.get_collection().find.return_value)


class TestNowTimestamp(unittest.TestCase):
    """
    Tests for creating a current timestamp.
    """

    @mock.patch('pulp.server.controllers.repository.dateutils')
    def test_ts(self, mock_date):
        """
        Make sure timestamp uses the correct dateutils.
        """
        result = repo_controller._now_timestamp()
        mock_date.now_utc_datetime_with_tzinfo.assert_called_once_with()
        mock_date.format_iso8601_datetime.assert_called_once_with(
            mock_date.now_utc_datetime_with_tzinfo.return_value
        )
        self.assertTrue(result is mock_date.format_iso8601_datetime.return_value)


class TestSpawnAutoPublishTasks(unittest.TestCase):
    """
    Tests for queuing publish tasks for distributors with auto publish.
    """

    @mock.patch('pulp.server.controllers.repository.queue_publish')
    @mock.patch('pulp.server.controllers.repository.model')
    def test_autopublish(self, m_model, mock_queue):
        """
        Assert that tasks are spawned for each distributor with auto publish enabled.
        """
        m_model.Distributor.objects.return_value = [mock.MagicMock(distributor_id='m_dist')]
        result = repo_controller._queue_auto_publish_tasks('m_repo', 'mock_schedule')
        m_model.Distributor.objects.assert_called_once_with(repo_id='m_repo', auto_publish=True)
        mock_queue.assert_called_once_with('m_repo', 'm_dist',
                                           scheduled_call_id='mock_schedule')
        self.assertEqual(result, [mock_queue().task_id])


class TestQueueSyncWithAutoPublish(unittest.TestCase):
    """
    Tests for queuing sync repository tasks.
    """

    @mock.patch('pulp.server.controllers.repository.sync')
    @mock.patch('pulp.server.controllers.repository.RESOURCE_REPOSITORY_TYPE')
    @mock.patch('pulp.server.controllers.repository.action_tag')
    @mock.patch('pulp.server.controllers.repository.resource_tag')
    def test_queue_sync(self, mock_r_tag, mock_a_tag, m_repo_type, m_sync_task):
        """
        Ensure that the sync task is queued with the correct arguments.
        """
        result = repo_controller.queue_sync_with_auto_publish('repo', scheduled_call_id='123')
        mock_r_tag.assert_called_once_with(m_repo_type, 'repo')
        mock_a_tag.assert_called_once_with('sync')
        m_sync_task.apply_async_with_reservation.assert_called_once_with(
            m_repo_type, 'repo', tags=[mock_r_tag(), mock_a_tag()],
            kwargs={'repo_id': 'repo', 'sync_config_override': None, 'scheduled_call_id': '123'}
        )
        self.assertTrue(result is m_sync_task.apply_async_with_reservation.return_value)


class TestUpdateUnitCount(unittest.TestCase):
    """
    Tests for updating the unit count of a repository.
    """

    @mock.patch('pulp.server.controllers.repository.model.Repository.objects')
    def test_update_unit_count(self, m_repo_qs):
        """
        Make sure the correct mongoengine key is used.
        """
        repo_controller.update_unit_count('m_repo', 'mock_type', 2)
        expected_key = 'inc__content_unit_counts__mock_type'
        m_repo_qs().update_one.assert_called_once_with(**{expected_key: 2})

    @mock.patch('pulp.server.controllers.repository.model.Repository.objects')
    def test_update_unit_count_errror(self, m_repo_qs):
        """
        If update throws an error, catch it an reraise a PulpExecutionException.
        """
        m_repo_qs().update_one.side_effect = mongoengine.OperationError
        self.assertRaises(pulp_exceptions.PulpExecutionException, repo_controller.update_unit_count,
                          'm_repo', 'mock_type', 2)
        expected_key = 'inc__content_unit_counts__mock_type'
        m_repo_qs().update_one.assert_called_once_with(**{expected_key: 2})


class TestGetImporterById(unittest.TestCase):

    @patch('pulp.server.controllers.repository.ObjectId')
    @patch('pulp.server.controllers.repository.plugin_api')
    @patch('pulp.server.controllers.repository.PluginCallConfiguration')
    @patch('pulp.server.db.model.Importer')
    def test_call(self, importer, call_conf, plugin_api, object_id):
        _id = '1234'
        cfg = MagicMock()
        plugin = MagicMock()
        document = MagicMock()
        importer.objects.get.return_value = document
        plugin_api.get_importer_by_id.return_value = (plugin, cfg)

        # test
        _plugin, _conf = repo_controller.get_importer_by_id(_id)

        # validation
        object_id.assert_called_once_with(_id)
        importer.objects.get.assert_called_once_with(id=object_id.return_value)
        call_conf.assert_called_once_with(cfg, document.config)
        self.assertEqual(_plugin, plugin)
        self.assertEqual(_conf, call_conf.return_value)

    @patch('pulp.server.controllers.repository.ObjectId', MagicMock())
    @patch('pulp.server.db.model.Importer')
    def test_call_document_not_found(self, importer):
        _id = '1234'
        importer.objects.get.side_effect = mongoengine.DoesNotExist
        self.assertRaises(
            plugin_exceptions.PluginNotFound,
            repo_controller.get_importer_by_id, _id)

    @patch('pulp.server.controllers.repository.ObjectId')
    def test_call_invalid_id(self, object_id):
        _id = '1234'
        object_id.side_effect = InvalidId
        self.assertRaises(
            plugin_exceptions.PluginNotFound,
            repo_controller.get_importer_by_id, _id)

    @patch('pulp.server.controllers.repository.ObjectId')
    @patch('pulp.server.controllers.repository.plugin_api')
    @patch('pulp.server.controllers.repository.PluginCallConfiguration')
    @patch('pulp.server.db.model.Importer')
    def test_call_plugin_not_found(self, importer, call_conf, plugin_api, object_id):
        _id = '1234'
        document = MagicMock()
        importer.objects.get.return_value = document
        plugin_api.get_importer_by_id.side_effect = plugin_exceptions.PluginNotFound

        # test
        self.assertRaises(
            plugin_exceptions.PluginNotFound,
            repo_controller.get_importer_by_id, _id)

        # validation
        object_id.assert_called_once_with(_id)
        importer.objects.get.assert_called_once_with(id=object_id.return_value)
        self.assertFalse(call_conf.called)


class TestQueueDownloadDeferred(unittest.TestCase):

    @patch(MODULE + 'tags')
    @patch(MODULE + 'download_deferred')
    def test_queue_download_deferred(self, mock_download_deferred, mock_tags):
        """Assert download_deferred tasks are tagged correctly."""
        repo_controller.queue_download_deferred()
        mock_tags.action_tag.assert_called_once_with(mock_tags.ACTION_DEFERRED_DOWNLOADS_TYPE)
        mock_download_deferred.apply_async.assert_called_once_with(
            tags=[mock_tags.action_tag.return_value]
        )


class TestQueueDownloadRepo(unittest.TestCase):

    @patch(MODULE + 'tags')
    @patch(MODULE + 'download_repo')
    def test_queue_download_repo(self, mock_download_repo, mock_tags):
        """Assert download_repo tasks are tagged correctly."""
        repo_controller.queue_download_repo('fake-id')
        mock_tags.resource_tag.assert_called_once_with(
            mock_tags.RESOURCE_REPOSITORY_TYPE,
            'fake-id'
        )
        mock_tags.action_tag.assert_called_once_with(mock_tags.ACTION_DOWNLOAD_TYPE)
        mock_download_repo.apply_async.assert_called_once_with(
            ['fake-id'],
            {'verify_all_units': False},
            tags=[mock_tags.resource_tag.return_value, mock_tags.action_tag.return_value]
        )


class TestDownloadDeferred(unittest.TestCase):

    @patch(MODULE + 'LazyUnitDownloadStep')
    @patch(MODULE + '_create_download_requests')
    @patch(MODULE + '_get_deferred_content_units')
    def test_download_deferred(self, mock_get_deferred, mock_create_requests, mock_step):
        """Assert the download step is initialized and called."""
        repo_controller.download_deferred()
        mock_create_requests.assert_called_once_with(mock_get_deferred.return_value)
        mock_step.return_value.start.assert_called_once_with()


class TestDownloadRepo(unittest.TestCase):

    @patch(MODULE + 'LazyUnitDownloadStep')
    @patch(MODULE + '_create_download_requests')
    @patch(MODULE + 'find_units_not_downloaded')
    def test_download_repo_no_verify(self, mock_missing_units, mock_create_requests, mock_step):
        """Assert the download step is initialized and called with missing units."""
        repo_controller.download_repo('fake-id')
        mock_missing_units.assert_called_once_with('fake-id')
        mock_create_requests.assert_called_once_with(mock_missing_units.return_value)
        mock_step.return_value.start.assert_called_once_with()

    @patch(MODULE + 'LazyUnitDownloadStep')
    @patch(MODULE + '_create_download_requests')
    @patch(MODULE + 'get_mongoengine_unit_querysets')
    def test_download_repo_verify(self, mock_units_qs, mock_create_requests, mock_step):
        """Assert the download step is initialized and called with all units."""
        mock_units_qs.return_value = [['some'], ['lists']]
        repo_controller.download_repo('fake-id', verify_all_units=True)
        mock_units_qs.assert_called_once_with('fake-id')
        self.assertEqual(list(mock_create_requests.call_args[0][0]), ['some', 'lists'])
        mock_step.return_value.start.assert_called_once_with()


class TestGetDeferredContentUnits(unittest.TestCase):

    @patch(MODULE + 'plugin_api.get_unit_model_by_id')
    @patch(MODULE + 'model.DeferredDownload')
    def test_get_deferred_content_units(self, mock_qs, mock_get_model):
        # Setup
        mock_unit = Mock(unit_type_id='abc', unit_id='123')
        mock_qs.objects.filter.return_value = [mock_unit]

        # Test
        result = list(repo_controller._get_deferred_content_units())
        self.assertEqual(1, len(result))
        mock_get_model.assert_called_once_with('abc')
        unit_filter = mock_get_model.return_value.objects.filter
        unit_filter.assert_called_once_with(id='123')
        unit_filter.return_value.get.assert_called_once_with()

    @patch(MODULE + '_logger.error')
    @patch(MODULE + 'plugin_api.get_unit_model_by_id')
    @patch(MODULE + 'model.DeferredDownload')
    def test_get_deferred_content_units_no_model(self, mock_qs, mock_get_model, mock_log):
        # Setup
        mock_unit = Mock(unit_type_id='abc', unit_id='123')
        mock_qs.objects.filter.return_value = [mock_unit]
        mock_get_model.return_value = None

        # Test
        result = list(repo_controller._get_deferred_content_units())
        self.assertEqual(0, len(result))
        mock_log.assert_called_once_with('Unable to find the model object for the abc type.')
        mock_get_model.assert_called_once_with('abc')

    @patch(MODULE + '_logger.debug')
    @patch(MODULE + 'plugin_api.get_unit_model_by_id')
    @patch(MODULE + 'model.DeferredDownload')
    def test_get_deferred_content_units_no_unit(self, mock_qs, mock_get_model, mock_log):
        # Setup
        mock_unit = Mock(unit_type_id='abc', unit_id='123')
        mock_qs.objects.filter.return_value = [mock_unit]
        unit_qs = mock_get_model.return_value.objects.filter.return_value
        unit_qs.get.side_effect = mongoengine.DoesNotExist()

        # Test
        result = list(repo_controller._get_deferred_content_units())
        self.assertEqual(0, len(result))
        mock_log.assert_called_once_with('Unable to find the abc:123 content unit.')
        mock_get_model.assert_called_once_with('abc')


class TestCreateDownloadRequests(unittest.TestCase):

    @patch(MODULE + 'Key.load', Mock())
    @patch(MODULE + 'common_utils.get_working_directory', Mock(return_value='/working/'))
    @patch(MODULE + 'mkdir')
    @patch(MODULE + '_get_streamer_url')
    @patch(MODULE + 'model.LazyCatalogEntry')
    def test_create_download_requests(self, mock_catalog, mock_get_url, mock_mkdir):
        # Setup
        content_units = [Mock(id='123', type_id='abc', list_files=lambda: ['/file/path'])]
        filtered_qs = mock_catalog.objects.filter.return_value
        catalog_entry = filtered_qs.order_by.return_value.first.return_value
        catalog_entry.path = '/storage/123/path'
        expected_data_dict = {
            repo_controller.TYPE_ID: 'abc',
            repo_controller.UNIT_ID: '123',
            repo_controller.UNIT_FILES: {
                '/working/123/path': {
                    repo_controller.CATALOG_ENTRY: catalog_entry,
                    repo_controller.PATH_DOWNLOADED: None
                }
            }
        }

        # Test
        requests = repo_controller._create_download_requests(content_units)
        expected_data_dict[repo_controller.REQUEST] = requests[0]
        mock_catalog.objects.filter.assert_called_once_with(
            unit_id='123',
            unit_type_id='abc',
            path='/file/path'
        )
        filtered_qs.order_by.assert_called_once_with('revision')
        filtered_qs.order_by.return_value.first.assert_called_once_with()
        mock_mkdir.assert_called_once_with('/working/123')
        self.assertEqual(1, len(requests))
        self.assertEqual(mock_get_url.return_value, requests[0].url)
        self.assertEqual('/working/123/path', requests[0].destination)
        self.assertEqual(expected_data_dict, requests[0].data)


class TestGetStreamerUrl(unittest.TestCase):

    def setUp(self):
        self.catalog = Mock(path='/path/to/content')
        self.config = {
            'https_retrieval': 'true',
            'redirect_host': 'pulp.example.com',
            'redirect_port': '',
            'redirect_path': '/streamer/'
        }

    @patch(MODULE + 'pulp_conf')
    @patch(MODULE + 'URL')
    def test_https_url(self, mock_url, mock_conf):
        """Assert HTTPS URLs are made if configured."""
        expected_unsigned_url = 'https://pulp.example.com/streamer/path/to/content'
        mock_key = Mock()
        mock_conf.get = lambda s, k: self.config[k]

        url = repo_controller._get_streamer_url(self.catalog, mock_key)
        mock_url.assert_called_once_with(expected_unsigned_url)
        mock_url.return_value.sign.assert_called_once_with(
            mock_key, expiration=(60 * 60 * 24 * 365))
        signed_url = mock_url.return_value.sign.return_value
        self.assertEqual(url, str(signed_url))

    @patch(MODULE + 'pulp_conf')
    @patch(MODULE + 'URL')
    def test_http_url(self, mock_url, mock_conf):
        """Assert HTTP URLs are made if configured."""
        expected_unsigned_url = 'http://pulp.example.com/streamer/path/to/content'
        mock_key = Mock()
        mock_conf.get = lambda s, k: self.config[k]
        self.config['https_retrieval'] = 'false'

        repo_controller._get_streamer_url(self.catalog, mock_key)
        mock_url.assert_called_once_with(expected_unsigned_url)

    @patch(MODULE + 'pulp_conf')
    @patch(MODULE + 'URL')
    def test_url_unparsable_setting(self, mock_url, mock_conf):
        """Assert an exception is raised if the configuration is unparsable."""
        mock_conf.get = lambda s, k: self.config[k]
        self.config['https_retrieval'] = 'unsure'

        self.assertRaises(
            pulp_exceptions.PulpCodedTaskException,
            repo_controller._get_streamer_url,
            self.catalog,
            Mock(),
        )

    @patch(MODULE + 'pulp_conf')
    @patch(MODULE + 'URL')
    def test_explicit_port(self, mock_url, mock_conf):
        """Assert URLs are correctly formed with ports."""
        expected_unsigned_url = 'https://pulp.example.com:1234/streamer/path/to/content'
        mock_key = Mock()
        mock_conf.get = lambda s, k: self.config[k]
        self.config['redirect_port'] = '1234'

        repo_controller._get_streamer_url(self.catalog, mock_key)
        mock_url.assert_called_once_with(expected_unsigned_url)


class TestLazyUnitDownloadStep(unittest.TestCase):

    def setUp(self):
        self.step = repo_controller.LazyUnitDownloadStep(
            'test_step',
            'Test Step',
            [Mock()]
        )
        self.data = {
            repo_controller.TYPE_ID: 'abc',
            repo_controller.UNIT_ID: '1234',
            repo_controller.REQUEST: Mock(canceled=False),
            repo_controller.UNIT_FILES: {
                '/no/where': {
                    repo_controller.CATALOG_ENTRY: Mock(),
                    repo_controller.PATH_DOWNLOADED: None
                }
            }
        }
        self.report = Mock(data=self.data, destination='/no/where')

    def test_start(self):
        """Assert calls to `_process_block` result in calls to the downloader."""
        self.step.downloader = Mock()
        self.step.start()
        self.step.downloader.download.assert_called_once_with(self.step.download_requests)

    @patch(MODULE + 'model.DeferredDownload')
    def test_download_started(self, mock_deferred_download):
        """Assert if validate_file raises an exception, the download is not skipped."""
        self.step.validate_file = Mock(side_effect=IOError)

        self.step.download_started(self.report)
        qs = mock_deferred_download.objects.filter
        qs.assert_called_once_with(unit_id='1234', unit_type_id='abc')
        qs.return_value.delete.assert_called_once_with()

    @patch(MODULE + 'model.DeferredDownload')
    def test_download_started_already_downloaded(self, mock_deferred_download):
        """Assert if validate_file doesn't raise an exception, the download is skipped."""
        self.step.validate_file = Mock()

        self.step.download_started(self.report)
        self.assertTrue(self.report.data[repo_controller.REQUEST].canceled)
        qs = mock_deferred_download.objects.filter
        qs.assert_called_once_with(unit_id='1234', unit_type_id='abc')
        qs.return_value.delete.assert_called_once_with()

    @patch(MODULE + 'os.path.relpath', Mock(return_value='filename'))
    @patch(MODULE + 'plugin_api.get_unit_model_by_id')
    def test_download_succeeded(self, mock_get_model):
        """Assert single file units mark the unit downloaded."""
        # Setup
        self.step.validate_file = Mock()
        model_qs = mock_get_model.return_value
        unit = model_qs.objects.filter.return_value.only.return_value.get.return_value

        # Test
        self.step.download_succeeded(self.report)
        unit.set_storage_path.assert_called_once_with('filename')
        self.assertEqual(
            {'set___storage_path': unit._storage_path},
            model_qs.objects.filter.return_value.update_one.call_args_list[0][1]
        )
        unit.import_content.assert_called_once_with(self.report.destination)
        self.assertEqual(1, self.step.progress_successes)
        self.assertEqual(0, self.step.progress_failures)
        self.assertEqual(
            {'set__downloaded': True},
            model_qs.objects.filter.return_value.update_one.call_args_list[1][1]
        )

    @patch(MODULE + 'os.path.relpath', Mock(return_value='a/filename'))
    @patch(MODULE + 'plugin_api.get_unit_model_by_id')
    def test_download_succeeded_multifile(self, mock_get_model):
        """Assert multi-file units are not marked as downloaded on single file completion."""
        # Setup
        self.step.validate_file = Mock()
        model_qs = mock_get_model.return_value
        unit = model_qs.objects.filter.return_value.only.return_value.get.return_value
        self.data[repo_controller.UNIT_FILES]['/second/file'] = {
            repo_controller.PATH_DOWNLOADED: None
        }

        # Test
        self.step.download_succeeded(self.report)
        self.assertEqual(0, unit.set_storage_path.call_count)
        unit.import_content.assert_called_once_with(
            self.report.destination,
            location='a/filename'
        )
        self.assertEqual(1, self.step.progress_successes)
        self.assertEqual(0, self.step.progress_failures)
        self.assertEqual(0, model_qs.objects.filter.return_value.update_one.call_count)

    @patch(MODULE + 'os.path.relpath', Mock(return_value='a/filename'))
    @patch(MODULE + 'plugin_api.get_unit_model_by_id')
    def test_download_succeeded_multifile_last_file(self, mock_get_model):
        """Assert multi-file units are marked as downloaded on last file completion."""
        # Setup
        self.step.validate_file = Mock()
        model_qs = mock_get_model.return_value
        unit = model_qs.objects.filter.return_value.only.return_value.get.return_value
        self.data[repo_controller.UNIT_FILES]['/second/file'] = {
            repo_controller.PATH_DOWNLOADED: True
        }

        # Test
        self.step.download_succeeded(self.report)
        self.assertEqual(0, unit.set_storage_path.call_count)
        unit.import_content.assert_called_once_with(
            self.report.destination,
            location='a/filename'
        )
        self.assertEqual(1, self.step.progress_successes)
        self.assertEqual(0, self.step.progress_failures)
        model_qs.objects.filter.return_value.update_one.assert_called_once_with(
            set__downloaded=True)

    @patch(MODULE + 'os.path.relpath', Mock(return_value='filename'))
    @patch(MODULE + 'plugin_api.get_unit_model_by_id')
    def test_download_succeeded_corrupted_download(self, mock_get_model):
        """Assert corrupted downloads are not copied or marked as downloaded."""
        # Setup
        self.step.validate_file = Mock(side_effect=repo_controller.VerificationException)
        model_qs = mock_get_model.return_value
        unit = model_qs.objects.filter.return_value.only.return_value.get.return_value

        # Test
        self.step.download_succeeded(self.report)
        self.assertEqual(0, unit.set_storage_path.call_count)
        self.assertEqual(0, unit.import_content.call_count)
        self.assertEqual(0, self.step.progress_successes)
        self.assertEqual(1, self.step.progress_failures)

    def test_download_failed(self):
        self.assertEqual(0, self.step.progress_failures)
        self.step.download_failed(self.report)
        self.assertEqual(1, self.step.progress_failures)
        path_entry = self.report.data[repo_controller.UNIT_FILES]['/no/where']
        self.assertFalse(path_entry[repo_controller.PATH_DOWNLOADED])

    @patch('__builtin__.open')
    @patch(MODULE + 'verify_checksum')
    def test_validate_file(self, mock_verify_checksum, mock_open):
        self.step.validate_file('/no/where', 'sha8', '7')
        self.assertEqual(('sha8', '7'), mock_verify_checksum.call_args[0][1:])
        mock_open.assert_called_once_with('/no/where')

    @patch(MODULE + 'verify_checksum')
    def test_validate_file_fail(self, mock_verify_checksum):
        mock_verify_checksum.side_effect = IOError
        self.assertRaises(IOError, self.step.validate_file, '/no/where', 'sha8', '7')

    @patch(MODULE + 'os.path.isfile')
    def test_validate_file_no_checksum(self, mock_isfile):
        mock_isfile.return_value = False
        self.assertRaises(IOError, self.step.validate_file, '/no/where', None, None)
