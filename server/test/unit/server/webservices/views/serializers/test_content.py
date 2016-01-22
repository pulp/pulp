from datetime import datetime
from unittest import TestCase

from mock import patch
from mongoengine import StringField

from pulp.common import dateutils
from pulp.server.db.model import ContentUnit
from pulp.server.webservices.views import serializers
from pulp.server.webservices.views.serializers import content, db

LAST_UPDATED = '_last_updated'


class TestSerialization(TestCase):

    @patch('pulp.server.webservices.views.serializers.db.scrub_mongo_fields',
           wraps=db.scrub_mongo_fields)
    def test_serialization(self, mock):
        dt = datetime(2012, 10, 24, 10, 20, tzinfo=dateutils.utc_tz())
        last_updated = dateutils.datetime_to_utc_timestamp(dt)
        unit = {'_last_updated': last_updated}
        serialized = content.content_unit_obj(unit)
        mock.assert_called_once_with(unit)
        self.assertTrue(LAST_UPDATED in serialized)
        self.assertEqual(serialized[LAST_UPDATED], '2012-10-24T10:20:00Z')

    def test_serialization_no_last_modified(self):
        serialized = content.content_unit_obj({})
        self.assertFalse(LAST_UPDATED in serialized)


class TestRemapFieldsFromSerializer(TestCase):
    @classmethod
    def setUpClass(self):
        class ContentUnitHelperSerializer(serializers.ModelSerializer):
            class Meta:
                remapped_fields = remapped_fields = {'type_specific_id': 'id'}

        class ContentUnitHelper(ContentUnit):
            _ns = StringField(default='dummy_content_name')
            _content_type_id = StringField(required=True, default='content_type')
            unit_key_fields = ()
            type_specific_id = StringField()
            SERIALIZER = ContentUnitHelperSerializer
        self.content_unit_model = ContentUnitHelper

    def setUp(self):
        self.content_unit = {
            '_content_type_id': 'content_type',
            'type_specific_id': 'foo',
        }

    @patch('pulp.plugins.loader.api.get_unit_model_by_id')
    def test_remap_fields(self, mock_get_model):
        mock_get_model.return_value = self.content_unit_model
        content.remap_fields_with_serializer(self.content_unit)
        self.assertTrue('type_specific_id' not in self.content_unit,
                        'type-specific ID field not remapped')
        self.assertTrue('id' in self.content_unit)
        self.assertEqual(self.content_unit['id'], 'foo')
