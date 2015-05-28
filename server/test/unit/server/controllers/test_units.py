try:
    import unittest2 as unittest
except ImportError:
    import unittest


from mock import MagicMock, patch
import mongoengine

from pulp.server.controllers import units as units_controller
from pulp.server.db import model


class DemoModel(model.ContentUnit):
    key_field = mongoengine.StringField()
    unit_key_fields = ['key_field']
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
