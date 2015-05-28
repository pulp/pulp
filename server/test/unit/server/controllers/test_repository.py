try:
    import unittest2 as unittest
except ImportError:
    import unittest

from mock import MagicMock, patch
import mongoengine

from pulp.server.controllers import repository as repo_controller
from pulp.server.db import model


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
