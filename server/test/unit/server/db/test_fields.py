import unittest

from datetime import datetime

from mongoengine import ValidationError

from pulp.common import dateutils
from pulp.server.db import fields


class TestISODateField(unittest.TestCase):

    def test_validate(self):
        iso8601_field = fields.ISO8601StringField()
        valid = dateutils.format_iso8601_datetime(datetime.now())
        iso8601_field.validate(valid)

        invalid_values = ['date', {}, [], 1, datetime.now()]
        for invalid in invalid_values:
            self.assertRaises(ValidationError, iso8601_field.validate, invalid)
