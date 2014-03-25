# -*- coding: utf-8 -*-
# Copyright (c) 2014 Red Hat, Inc.
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

from mock import Mock

from pulp.common import error_codes
from pulp.devel.unit.server import util
from pulp.server.exceptions import PulpCodedValidationException, PulpCodedException


class TestAssertValidationExceptionRaised(unittest.TestCase):

    def test_calls_method_no_args(self):
        mock_method = Mock(side_effect=PulpCodedValidationException())
        util.assert_validation_exception(mock_method, [])
        mock_method.assert_called_once_with()

    def test_calls_method_with_args(self):
        mock_method = Mock(side_effect=PulpCodedValidationException())
        util.assert_validation_exception(mock_method, [], "foo")
        mock_method.assert_called_once_with("foo")

    def test_calls_method_with_kwargs(self):
        mock_method = Mock(side_effect=PulpCodedValidationException())
        util.assert_validation_exception(mock_method, [], baz="qux")
        mock_method.assert_called_once_with(baz="qux")

    def test_calls_method_with_child_exceptions(self):
        mock_method = Mock(side_effect=PulpCodedValidationException(
            validation_exceptions=[PulpCodedException()]))
        util.assert_validation_exception(mock_method, error_codes=[error_codes.PLP0001])

    def test_error_codes_no_child_exceptions(self):
        mock_method = Mock(side_effect=PulpCodedValidationException())
        self.assertRaises(AssertionError, util.assert_validation_exception, mock_method,
                          error_codes=[error_codes.PLP1002])

    def test_child_exceptions_no_error_codes(self):
        mock_method = Mock(side_effect=PulpCodedValidationException(
            validation_exceptions=[PulpCodedException()]))
        self.assertRaises(AssertionError, util.assert_validation_exception, mock_method, [])

    def test_validates_error_codes_not_present(self):
        mock_method = Mock(side_effect=PulpCodedValidationException(
            validation_exceptions=[PulpCodedException()]))
        self.assertRaises(AssertionError, util.assert_validation_exception, mock_method,
                          error_codes=[error_codes.PLP0001, error_codes.PLP0012])

    def test_validates_child_errors_not_present(self):
        mock_method = Mock(side_effect=PulpCodedValidationException(
            validation_exceptions=[PulpCodedException(), PulpCodedException(error_codes.PLP0012)]))
        self.assertRaises(AssertionError, util.assert_validation_exception, mock_method,
                          error_codes=[error_codes.PLP0001])

    def test_raises_validation_exception(self):
        mock_method = Mock()
        self.assertRaises(AssertionError, util.assert_validation_exception, mock_method,
                          error_codes=[error_codes.PLP0001])
