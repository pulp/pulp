from datetime import datetime
from unittest import TestCase

from mock import patch

from pulp.common import dateutils
from pulp.server.webservices.serialization import content, db

LAST_UPDATED = '_last_updated'


class TestSerialization(TestCase):

    @patch('pulp.server.webservices.serialization.db.scrub_mongo_fields',
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
