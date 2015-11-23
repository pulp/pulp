import unittest
from datetime import datetime, timedelta, tzinfo

import mongoengine

from pulp.common import dateutils
from pulp.server.db import fields


class TestCustomFields(unittest.TestCase):

    def test_iso8601_string_field(self):
        iso8601_field = fields.ISO8601StringField()
        valid = dateutils.format_iso8601_datetime(datetime.now())
        iso8601_field.validate(valid)

        invalid_values = ['date', {}, [], 1, datetime.now()]
        for invalid in invalid_values:
            self.assertRaises(mongoengine.ValidationError, iso8601_field.validate, invalid)


class TestUTCDateTimeField(unittest.TestCase):
    class TestModel(mongoengine.Document):
        timestamp = fields.UTCDateTimeField()

    class EST(tzinfo):
        def utcoffset(self, dt):
            return timedelta(hours=-5)

        def tzname(self, dt):
            return 'EST'

        def dst(self, dt):
            return timedelta(0)

    def test_timezone_aware(self):
        """
        quoting docs [0]: "A datetime object d is aware if d.tzinfo is not None and
        d.tzinfo.utcoffset(d) does not return None."

        [0] https://docs.python.org/2/library/datetime.html#datetime.tzinfo
        """
        now = datetime.utcnow()
        self.assertTrue(now.tzinfo is None)
        model = self.TestModel(timestamp=now)

        self.assertTrue(model.timestamp.tzinfo is not None)
        self.assertTrue(model.timestamp.tzinfo.utcoffset(model.timestamp) is not None)

    def test_timezone_is_utc(self):
        now = datetime.utcnow()
        self.assertTrue(now.tzinfo is None)
        model = self.TestModel(timestamp=now)

        self.assertEqual(model.timestamp.tzinfo.utcoffset(model.timestamp), timedelta(0))

    def test_convert_other_timezone(self):
        timestamp = datetime(year=2015, month=11, day=23, hour=13, minute=52, tzinfo=self.EST())
        model = self.TestModel(timestamp=timestamp)

        self.assertEqual(model.timestamp.hour, 18)
        self.assertEqual(model.timestamp.tzinfo.utcoffset(model.timestamp), timedelta(0))
        self.assertEqual(timestamp, model.timestamp)
