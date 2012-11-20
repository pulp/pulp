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
