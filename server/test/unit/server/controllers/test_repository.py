try:
    import unittest2 as unittest
except ImportError:
    import unittest

from mock import MagicMock, patch
import mock
import mongoengine

from pulp.plugins.loader import exceptions as plugin_exceptions
from pulp.plugins.model import PublishReport
from pulp.server.controllers import repository as repo_controller
from pulp.server import exceptions as pulp_exceptions
from pulp.server.db import model


class MockException(Exception):
    """Used for tracking the handling of exceptions."""
    pass


class DemoModel(model.ContentUnit):
    key_field = mongoengine.StringField()
    unit_key_fields = ['key_field']
    unit_type_id = 'demo_model'


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

        mock_demo_objects.return_value.only.assert_called_once_with(['key_field'])

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

        mock_demo_objects.return_value.only.assert_called_once_with(['key_field'])

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


class UpdateRepoUnitCountsTests(unittest.TestCase):

    @patch('pulp.server.controllers.repository.model.Repository.objects')
    @patch('pulp.server.controllers.repository.connection.get_database')
    def test_calculate_counts(self, mock_get_db, mock_repo_objects):
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

        mock_repo_objects.assert_called_once_with(__raw__={'id': 'foo'})
        mock_repo_objects.return_value.update_one.assert_called_once_with(
            set__content_unit_counts={'type_1': 5, 'type_2': 3}
        )


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
            unit_type_id=DemoModel.unit_type_id
        )
        mock_rcu_objects.return_value.update_one.assert_called_once_with(
            set_on_insert__created='foo_tstamp',
            set__updated='foo_tstamp',
            upsert=True)


@mock.patch('pulp.server.controllers.repository.manager_factory')
@mock.patch('pulp.server.controllers.repository.model.Repository')
class TestCreateRepo(unittest.TestCase):
    """
    Tests for repo creation.
    """

    def test_invalid_repo_id(self, mock_model, mock_factory):
        """
        Test creating a repository with invalid characters.
        """
        mock_model().save.side_effect = mongoengine.ValidationError
        self.assertRaises(pulp_exceptions.InvalidValue, repo_controller.create_repo,
                          'invalid_chars&')

    def test_minimal_creation(self, mock_model, mock_factory):
        """
        Test creating a repository with only the required parameters.
        """
        repo = repo_controller.create_repo('mock_repo')
        mock_model.assert_called_once_with(repo_id='mock_repo', notes=None, display_name=None,
                                           description=None)
        repo.save.assert_called_once_with()
        self.assertTrue(repo is mock_model.return_value)

    def test_duplicate_repo(self, mock_model, mock_factory):
        """
        Test creation of a repository that already exists.
        """
        mock_model.return_value.save.side_effect = mongoengine.NotUniqueError
        self.assertRaises(pulp_exceptions.DuplicateResource, repo_controller.create_repo,
                          'mock_repo')

    def test_invalid_notes(self, mock_model, mock_factory):
        """
        Test creation of a repository that has invalid notes.
        """
        mock_model.return_value.save.side_effect = mongoengine.ValidationError
        self.assertRaises(pulp_exceptions.InvalidValue, repo_controller.create_repo, 'mock_repo')

    def test_create_with_importer_config(self, mock_model, mock_factory):
        """
        Test creation of a repository with a specified importer configuration.
        """
        mock_importer_manager = mock_factory.repo_importer_manager.return_value
        repo = repo_controller.create_repo('mock_repo', importer_type_id='mock_type',
                                           importer_repo_plugin_config='mock_config')
        mock_importer_manager.set_importer.assert_called_once_with('mock_repo', 'mock_type',
                                                                   'mock_config')
        self.assertTrue(repo is mock_model.return_value)
        self.assertEqual(repo.delete.call_count, 0)

    def test_create_with_importer_config_exception(self, mock_model, mock_factory):
        """
        Test creation of a repository when the importer configuration fails.
        """
        repo_inst = mock_model.return_value
        mock_importer_manager = mock_factory.repo_importer_manager.return_value
        mock_importer_manager.set_importer.side_effect = MockException
        repo_inst = mock_model.return_value
        self.assertRaises(MockException, repo_controller.create_repo, 'mock_repo',
                          importer_type_id='id', importer_repo_plugin_config='mock_config')
        mock_importer_manager.set_importer.assert_called_once_with('mock_repo', 'id', 'mock_config')
        self.assertEqual(repo_inst.delete.call_count, 1)

    def test_create_with_distributor_list_not_list(self, mock_model, mock_factory):
        """
        Test creation of a repository when distributor list is invalid.
        """
        self.assertRaises(pulp_exceptions.InvalidValue, repo_controller.create_repo,
                          'mock_repo', distributor_list='non-list')
        self.assertEqual(mock_model.call_count, 0)

    def test_create_with_invalid_dists_in_dist_list(self, mock_model, mock_factory):
        """
        Test creation of a repository when one of the distributors is invalid.
        """
        repo_inst = mock_model.return_value
        self.assertRaises(pulp_exceptions.InvalidValue, repo_controller.create_repo,
                          'mock_repo', distributor_list=['not_dict'])
        repo_inst.delete.assert_called_with()

    def test_create_with_valid_distsributors(self, mock_model, mock_factory):
        """
        Test creation of a repository and the proper configuration of distributors.
        """
        mock_dist_manager = mock_factory.repo_distributor_manager.return_value
        mock_dist = {'distributor_type_id': 'mock_type', 'distributor_config': 'mock_conf',
                     'distributor_id': 'mock_dist'}
        repo = repo_controller.create_repo('mock_repo', distributor_list=[mock_dist])
        self.assertEqual(repo.delete.call_count, 0)
        mock_dist_manager.add_distributor.assert_called_once_with(
            'mock_repo', 'mock_type', 'mock_conf', False, 'mock_dist'
        )

    def test_create_with_distsributor_exception(self, mock_model, mock_factory):
        """
        Test creation of a repository when distributor configuration fails.
        """
        mock_dist_manager = mock_factory.repo_distributor_manager.return_value
        mock_dist_manager.add_distributor.side_effect = MockException
        repo_inst = mock_model.return_value
        self.assertRaises(MockException, repo_controller.create_repo, 'mock_repo',
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
        async_result = repo_controller.queue_delete('mock_repo')
        mock_delete.apply_async_with_reservation.assert_called_once_with(
            mock_tags.RESOURCE_REPOSITORY_TYPE, 'mock_repo', ['mock_repo'],
            tags=mock_task_tags
        )
        self.assertTrue(async_result is mock_delete.apply_async_with_reservation())


@mock.patch('pulp.server.controllers.repository.TaskResult')
@mock.patch('pulp.server.controllers.repository.RepoDistributor')
@mock.patch('pulp.server.controllers.repository.RepoImporter')
@mock.patch('pulp.server.controllers.repository.RepoSyncResult')
@mock.patch('pulp.server.controllers.repository.RepoPublishResult')
@mock.patch('pulp.server.controllers.repository.RepoContentUnit')
@mock.patch('pulp.server.controllers.repository.model.Repository')
@mock.patch('pulp.server.controllers.repository.manager_factory')
class TestDelete(unittest.TestCase):
    """
    Tests for deleting a repository.
    """

    def test_delete_no_importers_or_distributors(self, mock_factory, mock_model, mock_content,
                                                 mock_publish, mock_sync, mock_imp, mock_dist,
                                                 mock_task_result):
        """
        Test a simple repository delete when there are no importers or distributors.
        """
        mock_imp.get_collection().find_one.return_value = None
        mock_dist.get_collection().find.return_value = []
        mock_repo = mock_model.objects.get_repo_or_missing_resource.return_value
        mock_group_manager = mock_factory.repo_group_manager.return_value
        mock_consumer_bind_manager = mock_factory.consumer_bind_manager.return_value
        mock_consumer_bind_manager.find_by_repo.return_value = []

        result = repo_controller.delete('foo-repo')
        mock_repo.delete.assert_called_once_with()
        pymongo_args = {'repo_id': 'foo-repo'}
        pymongo_kwargs = {'safe': True}

        mock_dist.get_collection().remove.assert_called_once_with(pymongo_args, **pymongo_kwargs)
        mock_imp.get_collection().remove.assert_called_once_with(pymongo_args, **pymongo_kwargs)
        mock_sync.get_collection().remove.assert_called_once_with(pymongo_args, **pymongo_kwargs)
        mock_publish.get_collection().remove.assert_called_once_with(pymongo_args, **pymongo_kwargs)
        mock_content.get_collection().remove.assert_called_once_with(pymongo_args, **pymongo_kwargs)
        mock_group_manager.remove_repo_from_groups.assert_called_once_with('foo-repo')
        mock_task_result.assert_called_once_with(error=None, spawned_tasks=[])
        self.assertTrue(result is mock_task_result.return_value)

    @mock.patch('pulp.server.controllers.repository.consumer_controller')
    def test_delete_imforms_other_collections(self, mock_consumer_ctrl, mock_factory, mock_model,
                                              mock_content, mock_publish, mock_sync, mock_imp,
                                              mock_dist, mock_task_result):
        """
        Test that other collections are correctly informed when a repository is deleted.
        """
        mock_imp.get_collection().find_one.return_value = None
        mock_dist_manager = mock_factory.repo_distributor_manager.return_value
        mock_dist.get_collection().find.return_value = [{'id': 'mock_d'}]
        mock_repo = mock_model.objects.get_repo_or_missing_resource.return_value
        mock_group_manager = mock_factory.repo_group_manager.return_value
        mock_consumer_bind_manager = mock_factory.consumer_bind_manager.return_value
        mock_consumer_bind_manager.find_by_repo.return_value = [{
            'consumer_id': 'mock_con', 'repo_id': 'mock_repo', 'distributor_id': 'mock_dist'
        }]
        mock_consumer_ctrl.unbind.return_value.spawned_tasks = ['mock_task']

        result = repo_controller.delete('foo-repo')
        mock_repo.delete.assert_called_once_with()
        pymongo_args = {'repo_id': 'foo-repo'}
        pymongo_kwargs = {'safe': True}

        mock_dist_manager.remove_distributor.assert_called_once_with('foo-repo', 'mock_d')

        mock_dist.get_collection().remove.assert_called_once_with(pymongo_args, **pymongo_kwargs)
        mock_imp.get_collection().remove.assert_called_once_with(pymongo_args, **pymongo_kwargs)
        mock_sync.get_collection().remove.assert_called_once_with(pymongo_args, **pymongo_kwargs)
        mock_publish.get_collection().remove.assert_called_once_with(pymongo_args, **pymongo_kwargs)
        mock_content.get_collection().remove.assert_called_once_with(pymongo_args, **pymongo_kwargs)
        mock_consumer_ctrl.unbind.assert_called_once_with('mock_con', 'mock_repo', 'mock_dist', {})
        mock_group_manager.remove_repo_from_groups.assert_called_once_with('foo-repo')
        mock_task_result.assert_called_once_with(error=None, spawned_tasks=['mock_task'])
        self.assertTrue(result is mock_task_result.return_value)

    def test_delete_with_dist_and_imp_errors(self, mock_factory, mock_model, mock_content,
                                             mock_publish, mock_sync, mock_imp, mock_dist,
                                             mock_task_result):
        """
        Test repository delete when the other collections raise errors.
        """
        mock_imp_manager = mock_factory.repo_importer_manager.return_value
        mock_imp.get_collection().find_one.return_value = {'importer_type_id': 'mock'}
        mock_dist_manager = mock_factory.repo_distributor_manager.return_value
        mock_imp_manager.remove_importer.side_effect = MockException
        mock_dist_manager.remove_distributor.side_effect = MockException
        mock_dist.get_collection().find.return_value = [{'id': 'mock_d1'}, {'id': 'mock_d2'}]
        mock_repo = mock_model.objects.get_repo_or_missing_resource.return_value
        mock_group_manager = mock_factory.repo_group_manager.return_value
        mock_consumer_bind_manager = mock_factory.consumer_bind_manager.return_value

        try:
            repo_controller.delete('foo-repo')
        except pulp_exceptions.PulpExecutionException, e:
            pass
        else:
            raise AssertionError('Distributor/importer errors should raise a '
                                 'PulpExecutionException.')

        mock_repo.delete.assert_called_once_with()
        pymongo_args = {'repo_id': 'foo-repo'}
        pymongo_kwargs = {'safe': True}

        mock_dist_manager.remove_distributor.has_calls([
            mock.call('foo-repo', 'mock_d1'), mock.call('foo-repo', 'mock_d2')])

        # Direct db manipulation should still occur with distributor errors.
        mock_dist.get_collection().remove.assert_called_once_with(pymongo_args, **pymongo_kwargs)
        mock_imp.get_collection().remove.assert_called_once_with(pymongo_args, **pymongo_kwargs)
        mock_sync.get_collection().remove.assert_called_once_with(pymongo_args, **pymongo_kwargs)
        mock_publish.get_collection().remove.assert_called_once_with(pymongo_args, **pymongo_kwargs)
        mock_content.get_collection().remove.assert_called_once_with(pymongo_args, **pymongo_kwargs)
        mock_group_manager.remove_repo_from_groups.assert_called_once_with('foo-repo')

        # Consumers should not be unbound if there are distribur errors.
        self.assertEqual(mock_task_result.call_count, 0)
        self.assertEqual(mock_consumer_bind_manager.find_by_repo.call_count, 0)

        # Exceptions should be reraised as child execptions.
        self.assertEqual(len(e.child_exceptions), 3)
        self.assertTrue(isinstance(e.child_exceptions[0], MockException))
        self.assertTrue(isinstance(e.child_exceptions[1], MockException))
        self.assertTrue(isinstance(e.child_exceptions[2], MockException))

    def test_delete_content_errors(self, mock_factory, mock_model, mock_content, mock_publish,
                                   mock_sync, mock_imp, mock_dist, mock_task_result):
        """
        Test delete repository when the content collection raises errors.
        """

        mock_imp.get_collection().find_one.return_value = None
        mock_dist.get_collection().find.return_value = []
        mock_repo = mock_model.objects.get_repo_or_missing_resource.return_value
        mock_group_manager = mock_factory.repo_group_manager.return_value
        mock_consumer_bind_manager = mock_factory.consumer_bind_manager.return_value
        mock_consumer_bind_manager.find_by_repo.return_value = []
        mock_content.get_collection().remove.side_effect = MockException

        try:
            repo_controller.delete('foo-repo')
        except pulp_exceptions.PulpExecutionException, e:
            pass
        else:
            raise AssertionError('Content errors should raise a PulpExecutionException.')

        mock_repo.delete.assert_called_once_with()
        pymongo_args = {'repo_id': 'foo-repo'}
        pymongo_kwargs = {'safe': True}

        mock_dist.get_collection().remove.assert_called_once_with(pymongo_args, **pymongo_kwargs)
        mock_imp.get_collection().remove.assert_called_once_with(pymongo_args, **pymongo_kwargs)
        mock_sync.get_collection().remove.assert_called_once_with(pymongo_args, **pymongo_kwargs)
        mock_publish.get_collection().remove.assert_called_once_with(pymongo_args, **pymongo_kwargs)
        mock_content.get_collection().remove.assert_called_once_with(pymongo_args, **pymongo_kwargs)
        mock_group_manager.remove_repo_from_groups.assert_called_once_with('foo-repo')

        # Consumers should not be unbound if there are distribur errors.
        self.assertEqual(mock_task_result.call_count, 0)
        self.assertEqual(mock_consumer_bind_manager.find_by_repo.call_count, 0)

        # Exceptions should be reraised as child execptions.
        self.assertEqual(len(e.child_exceptions), 1)
        self.assertTrue(isinstance(e.child_exceptions[0], MockException))

    @mock.patch('pulp.server.controllers.repository.consumer_controller')
    @mock.patch('pulp.server.controllers.repository.error_codes.PLP0007')
    @mock.patch('pulp.server.controllers.repository.pulp_exceptions.PulpCodedException')
    def test_delete_consumer_bind_error(self, mock_coded_exception, mock_pulp_error,
                                        mock_consumer_ctrl, mock_factory, mock_model,
                                        mock_content, mock_publish, mock_sync, mock_imp, mock_dist,
                                        mock_task_result):
        """
        Test repository delete when consumer bind collection raises an error.
        """

        mock_imp.get_collection().find_one.return_value = None
        mock_dist.get_collection().find.return_value = []
        mock_repo = mock_model.objects.get_repo_or_missing_resource.return_value
        mock_group_manager = mock_factory.repo_group_manager.return_value
        mock_consumer_bind_manager = mock_factory.consumer_bind_manager.return_value
        mock_consumer_bind_manager.find_by_repo.return_value = [{
            'consumer_id': 'mock_con', 'repo_id': 'mock_repo', 'distributor_id': 'mock_dist'
        }]
        mock_consumer_ctrl.unbind.side_effect = MockException

        result = repo_controller.delete('foo-repo')
        mock_repo.delete.assert_called_once_with()
        pymongo_args = {'repo_id': 'foo-repo'}
        pymongo_kwargs = {'safe': True}

        mock_dist.get_collection().remove.assert_called_once_with(pymongo_args, **pymongo_kwargs)
        mock_imp.get_collection().remove.assert_called_once_with(pymongo_args, **pymongo_kwargs)
        mock_sync.get_collection().remove.assert_called_once_with(pymongo_args, **pymongo_kwargs)
        mock_publish.get_collection().remove.assert_called_once_with(pymongo_args, **pymongo_kwargs)
        mock_content.get_collection().remove.assert_called_once_with(pymongo_args, **pymongo_kwargs)
        mock_group_manager.remove_repo_from_groups.assert_called_once_with('foo-repo')
        mock_consumer_ctrl.unbind.assert_called_once_with('mock_con', 'mock_repo', 'mock_dist', {})

        expected_error = mock_coded_exception.return_value
        mock_coded_exception.assert_called_once_with(mock_pulp_error, repo_id='foo-repo')
        self.assertEqual(len(expected_error.child_exceptions), 1)
        self.assertTrue(isinstance(expected_error.child_exceptions[0], MockException))
        mock_task_result.assert_called_once_with(error=expected_error, spawned_tasks=[])
        self.assertTrue(result is mock_task_result.return_value)


class TestUpdateRepoAndPlugins(unittest.TestCase):
    """
    Tests for updating a repository and its related collections.
    """

    @mock.patch('pulp.server.controllers.repository.TaskResult')
    def test_no_change(self, mock_task_result):
        """
        No change should be made to a repository if update is called without actual changes.
        """
        mock_repo = mock.MagicMock()
        result = repo_controller.update_repo_and_plugins(mock_repo, None, None, None)
        self.assertTrue(result is mock_task_result.return_value)
        mock_task_result.assert_called_once_with(mock_repo, None, [])

    @mock.patch('pulp.server.controllers.repository.TaskResult')
    def test_update_with_delta(self, mock_task_result):
        """
        Test that the repo_delta is passed to the appropriate helper function.
        """
        mock_repo = mock.MagicMock()
        result = repo_controller.update_repo_and_plugins(mock_repo, {'mock': 'delta'}, None, None)
        self.assertTrue(result is mock_task_result.return_value)
        mock_task_result.assert_called_once_with(mock_repo, None, [])
        mock_repo.update_from_delta.assert_called_once_with({'mock': 'delta'})
        mock_repo.save.assert_called_once_with()

    def test_update_with_invalid_delta(self):
        """
        Ensure that InvalidValue is raised if the delta is not a valid dictionary.
        """
        mock_repo = mock.MagicMock()
        self.assertRaises(pulp_exceptions.InvalidValue, repo_controller.update_repo_and_plugins,
                          mock_repo, 'non-dict', None, None)

    @mock.patch('pulp.server.controllers.repository.manager_factory')
    @mock.patch('pulp.server.controllers.repository.TaskResult')
    def test_update_with_importer(self, mock_task_result, mock_factory):
        """
        Ensure that the importer manager is invoked to update the importer when specified.
        """
        mock_repo = mock.MagicMock()
        mock_imp_manager = mock_factory.repo_importer_manager.return_value
        result = repo_controller.update_repo_and_plugins(mock_repo, None, 'imp_config', None)
        mock_imp_manager.update_importer_config.assert_called_once_with(mock_repo.repo_id,
                                                                        'imp_config')
        self.assertTrue(result is mock_task_result.return_value)
        mock_task_result.assert_called_once_with(mock_repo, None, [])

    @mock.patch('pulp.server.controllers.repository.TaskResult')
    @mock.patch('pulp.server.controllers.repository.dist_controller')
    @mock.patch('pulp.server.controllers.repository.tags')
    def test_update_with_distributors(self, mock_tags, mock_dist_ctrl, mock_task_result):
        """
        Ensure that the distributor manager is invoked to update the distributors when specified.
        """
        mock_repo = mock.MagicMock()
        dist_configs = {'id1': 'conf1', 'id2': 'conf2'}
        result = repo_controller.update_repo_and_plugins(mock_repo, None, None, dist_configs)
        mock_async = mock_dist_ctrl.update.apply_async_with_reservation.return_value

        mock_task_tags = [mock_tags.resource_tag.return_value, mock_tags.resource_tag.return_value,
                          mock_tags.action_tag.return_value]
        mock_dist_ctrl.update.apply_async_with_reservation.assert_has_calls([
            mock.call(mock_tags.RESOURCE_REPOSITORY_TYPE, mock_repo.repo_id,
                      [mock_repo.repo_id, 'id1', 'conf1', None], tags=mock_task_tags),
            mock.call(mock_tags.RESOURCE_REPOSITORY_TYPE, mock_repo.repo_id,
                      [mock_repo.repo_id, 'id2', 'conf2', None], tags=mock_task_tags),
        ], any_order=True)
        mock_task_result.assert_called_once_with(mock_repo, None, [mock_async, mock_async])
        self.assertTrue(result is mock_task_result.return_value)


class TestUpdateLastUnitAdded(unittest.TestCase):
    """
    Tests for update last unit added.
    """

    @mock.patch('pulp.server.controllers.repository.model.Repository.objects')
    @mock.patch('pulp.server.controllers.repository.dateutils')
    def test_update_last_unit_added(self, mock_date, mock_repo_qs):
        """
        Ensure that the last_unit_added field is correctly updated.
        """
        mock_repo = mock_repo_qs.get_repo_or_missing_resource.return_value
        repo_controller.update_last_unit_added('mock_repo')
        self.assertEqual(mock_repo.last_unit_added, mock_date.now_utc_datetime_with_tzinfo())
        mock_repo.save.assert_called_once_with()


class TestUpdateLastUnitRemoved(unittest.TestCase):
    """
    Tests for update last unit removed.
    """

    @mock.patch('pulp.server.controllers.repository.model.Repository.objects')
    @mock.patch('pulp.server.controllers.repository.dateutils')
    def test_update_last_unit_removed(self, mock_date, mock_repo_qs):
        """
        Ensure that the last_unit_removed field is correctly updated.
        """
        mock_repo = mock_repo_qs.get_repo_or_missing_resource.return_value
        repo_controller.update_last_unit_removed('mock_repo')
        self.assertEqual(mock_repo.last_unit_removed, mock_date.now_utc_datetime_with_tzinfo())
        mock_repo.save.assert_called_once_with()


@mock.patch('pulp.server.controllers.repository.sys')
@mock.patch('pulp.server.controllers.repository.register_sigterm_handler')
@mock.patch('pulp.server.controllers.repository._now_timestamp')
@mock.patch('pulp.server.controllers.repository.manager_factory')
@mock.patch('pulp.server.controllers.repository.RepoSyncResult')
@mock.patch('pulp.server.controllers.repository.RepoSyncConduit')
@mock.patch('pulp.server.controllers.repository.common_utils.get_working_directory')
@mock.patch('pulp.server.controllers.repository.PluginCallConfiguration')
@mock.patch('pulp.server.controllers.repository.plugin_api')
@mock.patch('pulp.server.controllers.repository.RepoImporter')
@mock.patch('pulp.server.controllers.repository.model.Repository.objects')
class TestSync(unittest.TestCase):
    """
    Tests for syncing a repository.
    """

    def test_sync_no_importer(self, mock_repo_qs, mock_importer, *unused):
        """
        Raise when sync is requested but there is no importer.
        """
        mock_importer.get_collection().find_one.return_value = None
        self.assertRaises(pulp_exceptions.MissingResource, repo_controller.sync, 'mock_repo')

    def test_sync_no_importer_inst(self, mock_reqo_qs, mock_imp_manager, mock_plugin_api, *unused):
        """
        Raise when importer is not associated with a plugin.
        """
        mock_plugin_api.get_importer_by_id.side_effect = plugin_exceptions.PluginNotFound
        self.assertRaises(pulp_exceptions.MissingResource, repo_controller.sync, 'mock_repo')

    def test_sync_sigterm_error(self, mock_repo_qs, mock_imp_manager, mock_plugin_api,
                                mock_plug_conf, mock_wd, mock_conduit, mock_result, mock_factory,
                                mock_now, mock_reg_sig, mock_sys):
        """
        An error_result should be built when there is an error with the sigterm handler.
        """
        mock_repo = mock_repo_qs.get_repo_or_missing_resource.return_value
        mock_imp = mock.MagicMock()
        mock_imp_inst = mock_imp_manager.get_collection().find_one.return_value
        mock_plugin_api.get_importer_by_id.return_value = (mock_imp, 'mock_conf')
        expected_exp = MockException()
        sync_func = mock_reg_sig.return_value
        sync_func.side_effect = expected_exp
        self.assertRaises(MockException, repo_controller.sync, 'mock_repo')
        mock_result.error_result.assert_called_once_with(
            mock_repo.repo_id, mock_imp_inst['id'], mock_imp_inst['importer_type_id'], mock_now(),
            mock_now(), expected_exp, mock_sys.exc_info.return_value[2]
        )
        mock_reg_sig.assert_called_once_with(mock_imp.sync_repo, mock_imp.cancel_sync_repo)
        sync_func.assert_called_once_with(mock_repo.to_transfer_repo(), mock_conduit(),
                                          mock_plug_conf())

    @mock.patch('pulp.server.controllers.repository._queue_auto_publish_tasks')
    @mock.patch('pulp.server.controllers.repository.TaskResult')
    def test_sync_canceled(self, mock_task_result, mock_spawn_auto_pub, mock_repo_qs,
                           mock_imp_manager, mock_plugin_api, mock_plug_conf, mock_wd,
                           mock_conduit, mock_result, mock_factory, mock_now, mock_reg_sig,
                           mock_sys):
        """
        Test the behavior of sync when the task is canceled.
        """
        mock_spawn_auto_pub.return_value = []
        mock_fire_man = mock_factory.event_fire_manager()
        mock_repo = mock_repo_qs.get_repo_or_missing_resource.return_value
        mock_sync_result = repo_controller.SyncReport(
            success_flag=False, added_count=1, updated_count=2, removed_count=3, summary='sum',
            details='deets')
        sync_func = mock_reg_sig.return_value
        sync_func.return_value = mock_sync_result
        mock_sync_result.canceled_flag = True

        mock_result.RESULT_CANCELED = 'canceled'
        mock_repo = mock_repo_qs.get_repo_or_missing_resource.return_value
        mock_imp = mock.MagicMock()
        mock_imp_inst = mock_imp_manager.get_collection().find_one.return_value
        mock_plugin_api.get_importer_by_id.return_value = (mock_imp, 'mock_conf')

        actual_result = repo_controller.sync('mock_id')
        mock_result.expected_result.assert_called_once_with(
            mock_repo.repo_id, mock_imp_inst['id'], mock_imp_inst['importer_type_id'],
            mock_now(), mock_now(), mock_sync_result.added_count, mock_sync_result.updated_count,
            mock_sync_result.removed_count, mock_sync_result.summary, mock_sync_result.details,
            'canceled'
        )
        mock_imp_manager.get_collection().update.assert_called_once_with(
            {'repo_id': mock_repo.repo_id}, {'$set': {'last_sync': mock_now()}}, safe=True)
        mock_result.get_collection().save.assert_called_once_with(mock_result.expected_result(),
                                                                  safe=True)
        mock_fire_man.fire_repo_sync_finished.assert_called_once_with(mock_result.expected_result())
        self.assertTrue(actual_result is mock_task_result.return_value)

    @mock.patch('pulp.server.controllers.repository._queue_auto_publish_tasks')
    @mock.patch('pulp.server.controllers.repository.TaskResult')
    def test_sync_success(self, mock_task_result, mock_spawn_auto_pub, mock_repo_qs,
                          mock_imp_manager, mock_plugin_api, mock_plug_conf, mock_wd,
                          mock_conduit, mock_result, mock_factory, mock_now, mock_reg_sig,
                          mock_sys):
        """
        Test repository sync when everything works as expected.
        """
        mock_spawn_auto_pub.return_value = []
        mock_fire_man = mock_factory.event_fire_manager()
        mock_repo = mock_repo_qs.get_repo_or_missing_resource.return_value
        mock_sync_result = repo_controller.SyncReport(
            success_flag=False, added_count=1, updated_count=2, removed_count=3, summary='sum',
            details='deets')
        sync_func = mock_reg_sig.return_value
        sync_func.return_value = mock_sync_result
        mock_sync_result.canceled_flag = False
        mock_sync_result.success_flag = True

        mock_result.RESULT_SUCCESS = 'success'
        mock_repo = mock_repo_qs.get_repo_or_missing_resource.return_value
        mock_imp = mock.MagicMock()
        mock_imp_inst = mock_imp_manager.get_collection().find_one.return_value
        mock_plugin_api.get_importer_by_id.return_value = (mock_imp, 'mock_conf')

        actual_result = repo_controller.sync('mock_id')
        mock_result.expected_result.assert_called_once_with(
            mock_repo.repo_id, mock_imp_inst['id'], mock_imp_inst['importer_type_id'],
            mock_now(), mock_now(), mock_sync_result.added_count, mock_sync_result.updated_count,
            mock_sync_result.removed_count, mock_sync_result.summary, mock_sync_result.details,
            'success'
        )
        mock_imp_manager.get_collection().update.assert_called_once_with(
            {'repo_id': mock_repo.repo_id}, {'$set': {'last_sync': mock_now()}}, safe=True)
        mock_result.get_collection().save.assert_called_once_with(mock_result.expected_result(),
                                                                  safe=True)
        mock_fire_man.fire_repo_sync_finished.assert_called_once_with(mock_result.expected_result())
        self.assertTrue(actual_result is mock_task_result.return_value)

    @mock.patch('pulp.server.controllers.repository.TaskResult')
    def test_sync_failed(self, mock_task_result, mock_repo_qs, mock_imp_manager, mock_plugin_api,
                         mock_plug_conf, mock_wd, mock_conduit, mock_result, mock_factory, mock_now,
                         mock_reg_sig, mock_sys):
        """
        Test repository sync when the result is failure.
        """
        mock_fire_man = mock_factory.event_fire_manager()
        mock_repo = mock_repo_qs.get_repo_or_missing_resource.return_value
        mock_sync_result = repo_controller.SyncReport(
            success_flag=False, added_count=1, updated_count=2, removed_count=3, summary='sum',
            details='deets')
        mock_result.RESULT_FAILED = 'failed'
        mock_result.expected_result.return_value.result = mock_result.RESULT_FAILED
        sync_func = mock_reg_sig.return_value
        sync_func.return_value = mock_sync_result
        mock_sync_result.canceled_flag = False
        mock_sync_result.success_flag = False

        mock_repo = mock_repo_qs.get_repo_or_missing_resource.return_value
        mock_imp = mock.MagicMock()
        mock_imp_inst = mock_imp_manager.get_collection().find_one.return_value
        mock_plugin_api.get_importer_by_id.return_value = (mock_imp, 'mock_conf')

        self.assertRaises(pulp_exceptions.PulpExecutionException, repo_controller.sync, 'mock_id')
        mock_result.expected_result.assert_called_once_with(
            mock_repo.repo_id, mock_imp_inst['id'], mock_imp_inst['importer_type_id'],
            mock_now(), mock_now(), mock_sync_result.added_count, mock_sync_result.updated_count,
            mock_sync_result.removed_count, mock_sync_result.summary, mock_sync_result.details,
            'failed'
        )
        mock_imp_manager.get_collection().update.assert_called_once_with(
            {'repo_id': mock_repo.repo_id}, {'$set': {'last_sync': mock_now()}}, safe=True)
        mock_result.get_collection().save.assert_called_once_with(mock_result.expected_result(),
                                                                  safe=True)
        mock_fire_man.fire_repo_sync_finished.assert_called_once_with(mock_result.expected_result())

    @mock.patch('pulp.server.controllers.repository._queue_auto_publish_tasks')
    @mock.patch('pulp.server.controllers.repository._')
    @mock.patch('pulp.server.controllers.repository._logger')
    @mock.patch('pulp.server.controllers.repository.TaskResult')
    def test_sync_invalid_sync_report(self, mock_task_result, mock_logger, mock_gettext,
                                      mock_spawn_auto_pub, mock_repo_qs, mock_imp_manager,
                                      mock_plugin_api, mock_plug_conf, mock_wd, mock_conduit,
                                      mock_result, mock_factory, mock_now, mock_reg_sig, mock_sys):
        """
        Test repository sync when the sync repoort is not valid.
        """
        mock_spawn_auto_pub.return_value = []
        mock_fire_man = mock_factory.event_fire_manager()
        mock_repo = mock_repo_qs.get_repo_or_missing_resource.return_value
        mock_result.RESULT_ERROR = 'err'

        mock_repo = mock_repo_qs.get_repo_or_missing_resource.return_value
        mock_imp = mock.MagicMock()
        mock_imp_inst = mock_imp_manager.get_collection().find_one.return_value
        mock_plugin_api.get_importer_by_id.return_value = (mock_imp, 'mock_conf')

        result = repo_controller.sync('mock_id')
        mock_result.expected_result.assert_called_once_with(
            mock_repo.repo_id, mock_imp_inst['id'], mock_imp_inst['importer_type_id'],
            mock_now(), mock_now(), -1, -1, -1, mock_gettext(), mock_gettext(),
            'err'
        )
        mock_imp_manager.get_collection().update.assert_called_once_with(
            {'repo_id': mock_repo.repo_id}, {'$set': {'last_sync': mock_now()}}, safe=True)
        mock_result.get_collection().save.assert_called_once_with(mock_result.expected_result(),
                                                                  safe=True)
        mock_fire_man.fire_repo_sync_finished.assert_called_once_with(mock_result.expected_result())
        self.assertTrue(result is mock_task_result.return_value)


@mock.patch('pulp.server.controllers.repository.RepoDistributor')
@mock.patch('pulp.server.controllers.repository.model.Repository.objects')
@mock.patch('pulp.server.controllers.repository.manager_factory')
class TestPublish(unittest.TestCase):
    """
    Tests for publishing a repository.
    """

    def test_missing_distributor(self, mock_f, mock_repo_qs, mock_repo_dist):
        """
        Test publish when the distributor is not valid.
        """
        mock_repo_dist.get_collection().find_one.return_value = None
        self.assertRaises(pulp_exceptions.MissingResource, repo_controller.publish, 'repo', 'dist')

    @mock.patch('pulp.server.controllers.repository.common_utils')
    @mock.patch('pulp.server.controllers.repository._do_publish')
    @mock.patch('pulp.server.controllers.repository.PluginCallConfiguration')
    @mock.patch('pulp.server.controllers.repository.RepoPublishConduit')
    @mock.patch('pulp.server.controllers.repository._get_distributor_instance_and_config')
    def test_expected(self, mock_get_dist_inst, mock_pub_conduit, mock_plug_call_conf, mock_do_pub,
                      mock_common, mock_f, mock_repo_qs, mock_repo_dist):
        """
        Test publish when all goes as expected.
        """
        mock_fire = mock_f.event_fire_manager()
        mock_get_dist_inst.return_value = ('inst', 'conf')
        result = repo_controller.publish('repo', 'dist', 'override')

        mock_get_dist_inst.assert_called_once_with('repo', 'dist')
        mock_pub_conduit.assert_called_once_with('repo', 'dist')
        mock_plug_call_conf.assert_called_once_with(
            'conf', mock_repo_dist.get_collection().find_one()['config'], 'override')
        mock_repo = mock_repo_qs.get_repo_or_missing_resource.return_value
        mock_fire.fire_repo_publish_started.assert_called_once_with('repo', 'dist')
        mock_do_pub.assert_called_once_with(mock_repo, 'dist', 'inst', mock_repo.to_transfer_repo(),
                                            mock_pub_conduit(), mock_plug_call_conf())
        mock_fire.fire_repo_publish_finished.assert_called_once_with(mock_do_pub())
        self.assertTrue(
            mock_repo.to_transfer_repo().working_dir is mock_common.get_working_directory())
        self.assertTrue(result is mock_do_pub())


class TestGetDistributorInstanceAndConfig(unittest.TestCase):
    """
    Tests for retrieving a distributor instance and config.
    """

    @mock.patch('pulp.server.controllers.repository.plugin_api')
    @mock.patch('pulp.server.controllers.repository.manager_factory')
    def test_get_as_expected(self, mock_f, mock_plug_api):
        """
        Test retrieving distributor information when everything goes as expected.
        """
        mock_repo_dist_m = mock_f.repo_distributor_manager.return_value
        mock_plug_api.get_distributor_by_id.return_value = ('dist', 'conf')
        result = repo_controller._get_distributor_instance_and_config('repo', 'dist')
        mock_repo_dist_m.get_distributor.assert_called_once_with('repo', 'dist')
        mock_plug_api.get_distributor_by_id.assert_called_once_with(
            mock_repo_dist_m.get_distributor.return_value['distributor_type_id'])
        self.assertEqual(result, mock_plug_api.get_distributor_by_id.return_value)


@mock.patch('pulp.server.controllers.repository._')
@mock.patch('pulp.server.controllers.repository._logger')
@mock.patch('pulp.server.controllers.repository.register_sigterm_handler')
@mock.patch('pulp.server.controllers.repository._now_timestamp')
@mock.patch('pulp.server.controllers.repository.RepoPublishResult')
@mock.patch('pulp.server.controllers.repository.RepoDistributor')
class TestDoPublish(unittest.TestCase):
    """
    Tests that other collections are dealt with correctly when publishing a repository.
    """

    @mock.patch('pulp.server.controllers.repository.sys')
    @mock.patch('pulp.server.controllers.repository.pulp_exceptions.PulpCodedException')
    def test_invalid_publish_report(self, mock_e, mock_sys, mock_repo_dist, mock_repo_pub_result,
                                    mock_now, mock_sig_handler, mock_log, mock_text):
        """
        Test that invalid publish reports should raise.
        """
        mock_report = mock_sig_handler.return_value.return_value
        mock_report.success_flag = False
        mock_repo = mock.MagicMock()
        mock_inst = mock.MagicMock()
        expected_e = MockException()
        mock_e.side_effect = expected_e
        mock_dist = mock_repo_dist.get_collection().find_one.return_value
        args = [mock_repo, 'dist', mock_inst, 'transfer', 'conduit', 'config']
        self.assertRaises(MockException, repo_controller._do_publish, *args)

        mock_sig_handler.assert_called_once_with(mock_inst.publish_repo,
                                                 mock_inst.cancel_publish_repo)

        # Exception should be caught and rereaised. Test the cleanup.
        mock_repo_dist.get_collection().find_one.assert_called_once_with(
            {'repo_id': mock_repo.repo_id, 'id': 'dist'})
        mock_repo_dist.get_collection().save.assert_called_once_with(
            mock_repo_dist.get_collection().find_one.return_value, safe=True)
        mock_repo_pub_result.error_result.assert_called_once_with(
            mock_repo.repo_id, mock_dist['id'], mock_dist['distributor_type_id'], mock_now(),
            mock_now(), expected_e, mock_sys.exc_info()[2])

        mock_repo_pub_result.get_collection().save.assert_called_once_with(
            mock_repo_pub_result.error_result(), safe=True)
        mock_log.exception.assert_called_once_with(mock_text())

    @mock.patch('pulp.server.controllers.repository.datetime')
    def test_successful_publish(self, mock_dt, mock_repo_dist, mock_repo_pub_result, mock_now,
                                mock_sig_handler, mock_log, mock_text):
        """
        Test publish when everything is as expected.
        """
        fake_report = PublishReport(success_flag=True, summary='summary', details='details')
        mock_sig_handler.return_value.return_value = fake_report
        mock_repo = mock.MagicMock()
        mock_inst = mock.MagicMock()
        mock_dist = {'id': 'mock_id', 'distributor_type_id': 'mock_dist_type'}
        mock_repo_dist.get_collection().find_one.return_value = mock_dist
        result = repo_controller._do_publish(mock_repo, 'dist', mock_inst, 'transfer', 'conduit',
                                             'conf')
        self.assertTrue(mock_dist['last_publish'] is mock_dt.utcnow.return_value)
        mock_repo_pub_result.expected_result.assert_called_once_with(
            mock_repo.repo_id, 'mock_id', 'mock_dist_type', mock_now(), mock_now(), 'summary',
            'details', mock_repo_pub_result.RESULT_SUCCESS
        )
        mock_repo_pub_result.get_collection().save.assert_called_once_with(
            mock_repo_pub_result.expected_result(), safe=True)
        self.assertTrue(result is mock_repo_pub_result.expected_result.return_value)


class TestQueuePublish(unittest.TestCase):
    """
    Tests for queuing a publish task.
    """

    @mock.patch('pulp.server.controllers.repository.action_tag')
    @mock.patch('pulp.server.controllers.repository.resource_tag')
    @mock.patch('pulp.server.controllers.repository.publish')
    def test_expected(self, mock_publish, mock_r_tag, mock_a_tag):
        """
        Ensure that the correct args are passed to the dispatched publish task.
        """
        mock_tags = [mock_r_tag.return_value, mock_a_tag.return_value]
        mock_kwargs = {'repo_id': 'repo', 'dist_id': 'dist', 'publish_config_override': 'over'}
        result = repo_controller.queue_publish('repo', 'dist', overrides='over')
        mock_r_tag.assert_called_once_with(repo_controller.RESOURCE_REPOSITORY_TYPE, 'repo')
        mock_a_tag.assert_called_once_with('publish')
        mock_publish.apply_async_with_reservation.assert_called_once_with(
            repo_controller.RESOURCE_REPOSITORY_TYPE, 'repo', tags=mock_tags, kwargs=mock_kwargs)
        self.assertTrue(result is mock_publish.apply_async_with_reservation.return_value)


class TestAutoDistributors(unittest.TestCase):
    """
    Tests for retrieving a list of distributors with auto publish enabled.
    """

    @mock.patch('pulp.server.controllers.repository.RepoDistributor')
    def test_expected(self, mock_repo_dist):
        """
        Test that auto_distributors performs the correct search and returns a list.
        """
        result = repo_controller.auto_distributors('repo')
        mock_repo_dist.get_collection().find.assert_called_once_with(
            {'repo_id': 'repo', 'auto_publish': True})
        self.assertTrue(isinstance(result, list))


@mock.patch('pulp.server.controllers.repository.model.Repository.objects')
@mock.patch('pulp.server.controllers.repository.RepoSyncResult')
class TestSyncHistory(unittest.TestCase):
    """
    Tests for retrieving sync history.
    """

    def test_sync_history_minimal(self, mock_sync_result, mock_repo_qs):
        """
        Test that sync history is returned when optional parameters are not passed.
        """
        result = repo_controller.sync_history(None, None, 'mock_repo')
        mock_sync_result.get_collection().find.assert_called_once_with({'repo_id': 'mock_repo'})
        self.assertTrue(result is mock_sync_result.get_collection().find.return_value)

    def test_sync_history_with_all_options(self, mock_sync_result, mock_repo_qs):
        """
        Test that search includes all optional parameters.
        """
        result = repo_controller.sync_history('start', 'end', 'mock_repo')
        mock_sync_result.get_collection().find.assert_called_once_with(
            {'repo_id': 'mock_repo', 'started': {'$gte': 'start', '$lte': 'end'}})
        self.assertTrue(result is mock_sync_result.get_collection().find.return_value)


@mock.patch('pulp.server.controllers.repository.RepoDistributor')
@mock.patch('pulp.server.controllers.repository.model.Repository.objects')
@mock.patch('pulp.server.controllers.repository.RepoPublishResult')
class TestPublishHistory(unittest.TestCase):
    """
    Tests for retrieving publish history.
    """

    def test_missing_distributor(self, mock_publish, mock_repo_qs, mock_dist):
        """
        Ensure that a MissingResource is raised if the specified distributor does not exist.
        """
        mock_dist.get_collection().find_one.return_value = None
        self.assertRaises(pulp_exceptions.MissingResource, repo_controller.publish_history,
                          'start', 'end', 'repo', 'dist')

    def test_publish_history_minimal(self, mock_publish_result, mock_repo_qs, mock_dist):
        """
        Test that publish history is returned when optional parameters are not passed.
        """
        result = repo_controller.publish_history(None, None, 'mock_repo', 'mock_dist')
        mock_publish_result.get_collection().find.assert_called_once_with(
            {'repo_id': 'mock_repo', 'distributor_id': 'mock_dist'})
        self.assertTrue(result is mock_publish_result.get_collection().find.return_value)

    def test_publish_history_with_all_options(self, mock_publish_result, mock_repo_qs, mock_dist):
        """
        Test that search includes all optional parameters when passed.
        """
        result = repo_controller.publish_history('start', 'end', 'mock_repo', 'mock_dist')
        mock_publish_result.get_collection().find.assert_called_once_with({
            'repo_id': 'mock_repo', 'distributor_id': 'mock_dist',
            'started': {'$gte': 'start', '$lte': 'end'}
        })
        self.assertTrue(result is mock_publish_result.get_collection().find.return_value)


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
    @mock.patch('pulp.server.controllers.repository.auto_distributors')
    def test_autopublish(self, mock_auto_dists, mock_queue):
        """
        Assert that tasks are spawned for each distributor with auto publish enabled.
        """
        mock_auto_dists.return_value = [{'id': 'mock_dist'}]
        result = repo_controller._queue_auto_publish_tasks('mock_repo')
        mock_auto_dists.assert_called_once_with('mock_repo')
        mock_queue.assert_called_once_with('mock_repo', 'mock_dist')
        self.assertEqual(result, [mock_queue().task_id])


class TestQueueSyncWithAutoPublish(unittest.TestCase):
    """
    Tests for queuing sync repository tasks.
    """

    @mock.patch('pulp.server.controllers.repository.sync')
    @mock.patch('pulp.server.controllers.repository.RESOURCE_REPOSITORY_TYPE')
    @mock.patch('pulp.server.controllers.repository.action_tag')
    @mock.patch('pulp.server.controllers.repository.resource_tag')
    def test_queue_sync(self, mock_r_tag, mock_a_tag, mock_repo_type, mock_sync_task):
        """
        Ensure that the sync task is queued with the correct arguments.
        """
        result = repo_controller.queue_sync_with_auto_publish('repo')
        mock_r_tag.assert_called_once_with(mock_repo_type, 'repo')
        mock_a_tag.assert_called_once_with('sync')
        mock_sync_task.apply_async_with_reservation.assert_called_once_with(
            mock_repo_type, 'repo', tags=[mock_r_tag(), mock_a_tag()],
            kwargs={'repo_id': 'repo', 'sync_config_override': None}
        )
        self.assertTrue(result is mock_sync_task.apply_async_with_reservation.return_value)


class TestUpdateUnitCount(unittest.TestCase):
    """
    Tests for updating the unit count of a repository.
    """

    @mock.patch('pulp.server.controllers.repository.model.Repository.objects')
    def test_update_unit_count(self, mock_repo_qs):
        """
        Make sure the correct mongoengine key is used.
        """
        repo_controller.update_unit_count('mock_repo', 'mock_type', 2)
        expected_key = 'inc__content_unit_counts__mock_type'
        mock_repo_qs().update_one.assert_called_once_with(**{expected_key: 2})

    @mock.patch('pulp.server.controllers.repository.model.Repository.objects')
    def test_update_unit_count_errror(self, mock_repo_qs):
        """
        If update throws an error, catch it an reraise a PulpExecutionException.
        """
        mock_repo_qs().update_one.side_effect = mongoengine.OperationError
        self.assertRaises(pulp_exceptions.PulpExecutionException, repo_controller.update_unit_count,
                          'mock_repo', 'mock_type', 2)
        expected_key = 'inc__content_unit_counts__mock_type'
        mock_repo_qs().update_one.assert_called_once_with(**{expected_key: 2})
