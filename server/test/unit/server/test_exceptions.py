# -*- coding: utf-8 -*-
#
# Copyright © 2014 Red Hat, Inc.
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

from pulp.devel.unit.util import compare_dict
from pulp.server.exceptions import PulpException, PulpCodedException
from pulp.common import error_codes


class TestPulpException(unittest.TestCase):

    def test_custom_message(self):
        test_exception = PulpException("foo_msg")
        self.assertEquals(str(test_exception), "foo_msg")

    def test_to_dict(self):
        test_exception = PulpException("foo_msg")
        test_exception.error_data = {"foo": "bar"}

        result = test_exception.to_dict()

        compare_dict(result, {'code': test_exception.error_code.code,
                              'description': str(test_exception),
                              'data': {"foo": "bar"},
                              'sub_errors': []})

    def test_to_dict_nested_pulp_exception(self):
        test_exception = PulpException("foo_msg")
        test_exception.error_data = {"foo": "bar"}

        test_exception.add_child_exception(PulpCodedException(error_codes.PLP0001))

        result = test_exception.to_dict()
        child_exception = result['sub_errors'][0]
        compare_dict(child_exception, {'code': error_codes.PLP0001.code,
                                       'description': error_codes.PLP0001.message,
                                       'data': {},
                                       'sub_errors': []})

    def test_to_dict_nested_general_exception(self):
        test_exception = PulpException("foo_msg")
        test_exception.error_data = {"foo": "bar"}

        test_exception.add_child_exception(Exception("Foo Message"))
        test_exception.add_child_exception(Exception("Bar Message"))

        result = test_exception.to_dict()
        child_exception = result['sub_errors'][0]
        compare_dict(child_exception, {'code': error_codes.PLP0000.code,
                                       'description': "Foo Message",
                                       'data': {},
                                       'sub_errors': []})
        child_exception = result['sub_errors'][1]
        compare_dict(child_exception, {'code': error_codes.PLP0000.code,
                                       'description': "Bar Message",
                                       'data': {},
                                       'sub_errors': []})


class TestPulpCodedException(unittest.TestCase):

    def test_field_validation_correct(self):
        """
        Test to ensure that the fields required by the error code are available in the error
        data.
        """
        PulpCodedException(error_codes.PLP0000, {'message': 'foo message', 'extra_field': 'bar'})

    def test_field_validation_fails(self):
        """
        Test to ensure that the fields required by the error code are available in the error
        data.
        """
        self.assertRaises(PulpCodedException, PulpCodedException, error_codes.PLP0000, {})

    def test_field_validation_fails_data_none(self):
        """
        Test to ensure that the fields required by the error code are available in the error
        data.
        """
        self.assertRaises(PulpCodedException, PulpCodedException, error_codes.PLP0000, None)
