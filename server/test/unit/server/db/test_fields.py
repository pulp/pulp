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


class TestDigestField(unittest.TestCase):

    def test_validate(self):
        field = fields.ChecksumField()
        # valid
        for alg in fields.ChecksumField.ALGORITHMS:
            field.validate('%s:1234' % alg)
        # invalid format
        self.assertRaises(ValueError, field.validate, 'xyz')
        # invalid algorithm
        self.assertRaises(ValueError, field.validate, 'xyz:1234')
        # invalid digest
        self.assertRaises(ValueError, field.validate, '%s:' % fields.ChecksumField.ALGORITHMS[0])
