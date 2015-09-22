from mock import MagicMock, patch
import mongoengine

from pulp.common.compat import unittest
from pulp.server.controllers import units as units_controller
from pulp.server.db import models


class DemoModel(models.ContentUnit):
    key_field = mongoengine.StringField()
    unit_key_fields = ('key_field',)
    unit_type_id = 'demo_model'
    objects = MagicMock()
    save = MagicMock()


class FindUnitsTests(unittest.TestCase):

    @patch('pulp.server.controllers.units.misc.paginate')
    def test_paginate(self, mock_paginate):
        """
        ensure that paginate is used
        """
        model_1 = DemoModel(key_field='a')
        model_2 = DemoModel(key_field='B')
        units_iterable = (model_1, model_2)

        # turn into list so the generator will be evaluated
        list(units_controller.find_units(units_iterable))

        mock_paginate.assert_called_once_with(units_iterable, 50)

    def test_query(self):
        """
        Test that the mongo query generated is the one we expect
        """
        model_1 = DemoModel(key_field='a')
        model_2 = DemoModel(key_field='B')
        units_iterable = (model_1, model_2)

        # turn into list so the generator will be evaluated
        list(units_controller.find_units(units_iterable))
        query_dict = DemoModel.objects.call_args[0][0].to_query(DemoModel)
        expected_result = {'$or': [{'key_field': u'a'}, {'key_field': u'B'}]}
        self.assertDictEqual(query_dict, expected_result)

    def test_results(self):
        """
        Test that the mongo query generated is the one we expect
        """
        model_1 = DemoModel(key_field='a')
        model_2 = DemoModel(key_field='B')
        units_iterable = (model_1, model_2)
        model_2_defined = DemoModel(key_field='B', id='foo')
        DemoModel.objects.return_value = [model_2_defined]

        # turn into list so the generator will be evaluated
        result = list(units_controller.find_units(units_iterable))
        self.assertEqual(result, [model_2_defined])


@patch('pulp.plugins.loader.api.get_unit_model_by_id', spec_set=True)
@patch('pulp.plugins.types.database.type_definition', spec_set=True)
class TestGetUnitKeyFieldsForType(unittest.TestCase):
    def test_returns_from_model(self, mock_type_def, mock_get_model):
        """
        test when the requested type is a mongoengine model
        """
        mock_get_model.return_value = DemoModel
        mock_type_def.return_value = None

        ret = units_controller.get_unit_key_fields_for_type(DemoModel.type_id)

        self.assertEqual(ret, DemoModel.unit_key_fields)

    def test_returns_from_typedb(self, mock_type_def, mock_get_model):
        """
        test when the requested type is defined the old way
        """
        mock_get_model.return_value = None
        mock_type_def.return_value = {'unit_key': ['id']}

        ret = units_controller.get_unit_key_fields_for_type('faketype')

        self.assertEqual(ret, ('id',))

    def test_not_found(self, mock_type_def, mock_get_model):
        """
        test when the requested type is not found
        """
        mock_get_model.return_value = None
        mock_type_def.return_value = None

        self.assertRaises(ValueError, units_controller.get_unit_key_fields_for_type, 'faketype')
