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

import mock

from pulp.common import error_codes, auth_utils
from pulp.devel.unit.util import compare_dict
from pulp.server import exceptions


class TestPulpException(unittest.TestCase):

    def test_custom_message(self):
        test_exception = exceptions.PulpException("foo_msg")
        self.assertEquals(str(test_exception), "foo_msg")

    def test_to_dict(self):
        test_exception = exceptions.PulpException("foo_msg")
        test_exception.error_data = {"foo": "bar"}

        result = test_exception.to_dict()

        compare_dict(result, {'code': test_exception.error_code.code,
                              'description': str(test_exception),
                              'data': {"foo": "bar"},
                              'sub_errors': []})

    def test_to_dict_nested_pulp_exception(self):
        test_exception = exceptions.PulpException("foo_msg")
        test_exception.error_data = {"foo": "bar"}

        test_exception.add_child_exception(exceptions.PulpCodedException(error_codes.PLP0001))

        result = test_exception.to_dict()
        child_exception = result['sub_errors'][0]
        compare_dict(child_exception, {'code': error_codes.PLP0001.code,
                                       'description': error_codes.PLP0001.message,
                                       'data': {},
                                       'sub_errors': []})

    def test_to_dict_nested_general_exception(self):
        test_exception = exceptions.PulpException("foo_msg")
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
        exceptions.PulpCodedException(error_codes.PLP0000, message='foo message', extra_field='bar')

    def test_field_validation_fails(self):
        """
        Test to ensure that the fields required by the error code are available in the error
        data.
        """
        self.assertRaises(exceptions.PulpCodedException, exceptions.PulpCodedException, error_codes.PLP0000, baz='q')

    def test_field_validation_fails_data_none(self):
        """
        Test to ensure that the fields required by the error code are available in the error
        data.
        """
        self.assertRaises(exceptions.PulpCodedException, exceptions.PulpCodedException, error_codes.PLP0000)


class TestPulpCodedValidationException(unittest.TestCase):

    def test_init(self):
        """
        Test basic init with no values
        """
        e = exceptions.PulpCodedValidationException()
        self.assertEquals(e.error_code, error_codes.PLP1000)

    def test_with_child_exceptions(self):
        """
        Test initialization with child exceptions
        """
        e = exceptions.PulpCodedValidationException([exceptions.PulpCodedException(),
                                                     exceptions.PulpCodedException()])
        self.assertEquals(e.error_code, error_codes.PLP1000)
        self.assertEquals(len(e.child_exceptions), 2)


class TestPulpCodedAuthenticationException(unittest.TestCase):
    def test_init(self):
        """
        Test basic init with no values
        """
        e = exceptions.PulpCodedAuthenticationException()
        self.assertEquals(e.error_code, error_codes.PLP0025)

    def test_init_custom_code(self):
        """
        Test init with a custom authentication failure error code. This also tests that the
        old error code is placed in the error data for backward compatibility.
        """
        e = exceptions.PulpCodedAuthenticationException(error_code=error_codes.PLP0027, user='test')
        self.assertEquals(e.error_code, error_codes.PLP0027)
        self.assertTrue(auth_utils.CODE_KEY in e.data_dict())
        self.assertEquals(auth_utils.CODE_INVALID_SSL_CERT, e.data_dict()[auth_utils.CODE_KEY])


class TestNoWorkers(unittest.TestCase):
    """
    Tests for the NoWorkers Exception class.
    """
    @mock.patch('pulp.server.exceptions.PulpExecutionException.__init__')
    def test___init__(self, super___init__):
        """
        Ensure correct operation of __init__().
        """
        e = exceptions.NoWorkers()

        self.assertEqual(e.error_code, error_codes.PLP0024)
        super___init__.assert_called_once_with()

    def test___str__(self):
        """
        Ensure correct operation of __str__().
        """
        e = exceptions.NoWorkers()

        msg = str(e)

        self.assertEqual(msg, error_codes.PLP0024.message)

    def test_data_dict(self):
        """
        Ensure that data_dict returns {}.
        """
        e = exceptions.NoWorkers()

        d = e.data_dict()

        self.assertEqual(d, {})
