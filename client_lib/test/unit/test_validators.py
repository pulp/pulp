# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import unittest

from pulp.client import validators


class TestPositiveInt(unittest.TestCase):
    def test_positive(self):
        validators.positive_int_validator(2)

    def test_zero(self):
        self.assertRaises(ValueError, validators.positive_int_validator, 0)

    def test_negative(self):
        self.assertRaises(ValueError, validators.positive_int_validator, -2)

    def test_string(self):
        self.assertRaises(ValueError, validators.positive_int_validator, 'a')

    def test_empty_string(self):
        self.assertRaises(ValueError, validators.positive_int_validator, '')

    def test_none(self):
        self.assertRaises(TypeError, validators.positive_int_validator, None)


class TestNonNegativeInt(unittest.TestCase):
    def test_positive(self):
        validators.non_negative_int_validator(2)

    def test_zero(self):
        validators.non_negative_int_validator(0)

    def test_negative(self):
        self.assertRaises(ValueError, validators.non_negative_int_validator, -2)

    def test_string(self):
        self.assertRaises(ValueError, validators.non_negative_int_validator, 'a')

    def test_empty_string(self):
        self.assertRaises(ValueError, validators.non_negative_int_validator, '')

    def test_none(self):
        self.assertRaises(TypeError, validators.non_negative_int_validator, None)


class TestIso8601DateTime(unittest.TestCase):
    def test_valid_datetime(self):
        # Assert no exception is raised for valid formats
        validators.iso8601_datetime_validator('2013-06-02T12:00:00Z')
        validators.iso8601_datetime_validator('2013-06-02T12:00:00-23:00')

    def test_invalid_datetime(self):
        #Incomplete date
        self.assertRaises(ValueError, validators.iso8601_datetime_validator, '2013-06-02')
        # Illegal month
        self.assertRaises(ValueError, validators.iso8601_datetime_validator, '2013-13-01T12:00:00Z')
        # Illegal day
        self.assertRaises(ValueError, validators.iso8601_datetime_validator, '2013-06-42T12:00:00Z')
        # Illegal hour
        self.assertRaises(ValueError, validators.iso8601_datetime_validator, '2013-06-03T25:00:00Z')
        # Illegal minute
        self.assertRaises(ValueError, validators.iso8601_datetime_validator, '2013-06-03T12:61:00Z')
        # Illegal second
        self.assertRaises(ValueError, validators.iso8601_datetime_validator, '2013-06-03T12:00:61Z')
        # Illegal timezone
        self.assertRaises(ValueError, validators.iso8601_datetime_validator, '2013-06-03T12:00:61-25:00')
        self.assertRaises(ValueError, validators.iso8601_datetime_validator, '')


class TestIso8601Interval(unittest.TestCase):

    def test_start_duration(self):
        validators.interval_iso6801_validator('2010-06-06T12:00:00Z/P1Y0M0DT0H0M')

    def test_duration_end(self):
        validators.interval_iso6801_validator('P1Y6M0DT0H0M/2011-12-06T12:00:00Z')

    def test_invalid_intervals(self):
        self.assertRaises(ValueError,
                          validators.interval_iso6801_validator, '2010-06-06T12:00:00Z/P-1Y0M0DT0H0M')
        self.assertRaises(ValueError, validators.interval_iso6801_validator, '')


class TestId(unittest.TestCase):

    def test_valid_ids(self):

        # Single input
        validators.id_validator('test123')
        validators.id_validator('test_123-')
        validators.id_validator('TesT-0')
        validators.id_validator('-_-_-')

        # Multiple input
        validators.id_validator(['test123', 'TesT-0'])

    def test_invalid_ids(self):

        # Single input
        self.assertRaises(ValueError, validators.id_validator, '**invalid**')
        self.assertRaises(ValueError, validators.id_validator, 'invalid-@')
        self.assertRaises(ValueError, validators.id_validator, '-_-_- ')

        # Multiple input
        self.assertRaises(ValueError, validators.id_validator, ['**invalid**', '!#$%'])
        self.assertRaises(ValueError, validators.id_validator, ['valid', '**invalid**'])


class TestIdAllowDots(unittest.TestCase):

    def test_valid_ids_allow_dots(self):

        # Single input
        validators.id_validator_allow_dots('test123')
        validators.id_validator_allow_dots('test.123')
        validators.id_validator_allow_dots('test_123-')
        validators.id_validator_allow_dots('test._123-')
        validators.id_validator_allow_dots('TesT-0')
        validators.id_validator_allow_dots('TesT.-0')
        validators.id_validator_allow_dots('-_-_-')
        validators.id_validator_allow_dots('-._.-._.-')

        # Multiple input
        validators.id_validator_allow_dots(['test123', 'TesT-0', 'test.123'])

    def test_invalid_ids_allow_dots(self):

        # Single input
        self.assertRaises(ValueError, validators.id_validator_allow_dots, '**invalid**')
        self.assertRaises(ValueError, validators.id_validator_allow_dots, '**inval.id**')
        self.assertRaises(ValueError, validators.id_validator_allow_dots, 'invalid-@')
        self.assertRaises(ValueError, validators.id_validator_allow_dots, '-_-_- ')

        # Multiple input
        self.assertRaises(ValueError, validators.id_validator_allow_dots, ['**invalid**', '!#$%'])
        self.assertRaises(ValueError, validators.id_validator_allow_dots, ['valid', '**invalid**'])
