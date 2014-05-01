import unittest
from xml.etree import ElementTree

from mock import Mock

from pulp.common import error_codes
from pulp.devel.unit.server import util
from pulp.devel.unit.server.util import compare_element
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


class TestCompareEtree(unittest.TestCase):

    def test_compare_element_equality(self):
        source_string = '<foo alpha="bar">some text <baz></baz></foo>'
        source = ElementTree.fromstring(source_string)
        target = ElementTree.fromstring(source_string)
        compare_element(source, target)

    def test_compare_element_inequality_tags(self):
        source_string = '<foo></foo>'
        target_string = '<bar></bar>'
        source = ElementTree.fromstring(source_string)
        target = ElementTree.fromstring(target_string)
        self.assertRaises(AssertionError, compare_element, source, target)

    def test_compare_element_inequality_text(self):
        source_string = '<foo>alpha</foo>'
        target_string = '<foo>beta</foo>'
        source = ElementTree.fromstring(source_string)
        target = ElementTree.fromstring(target_string)
        self.assertRaises(AssertionError, compare_element, source, target)

    def test_compare_element_inequality_keys(self):
        source_string = '<foo alpha="bar"></foo>'
        target_string = '<foo beta="bar"></foo>'
        source = ElementTree.fromstring(source_string)
        target = ElementTree.fromstring(target_string)
        self.assertRaises(AssertionError, compare_element, source, target)

    def test_compare_element_inequality_values(self):
        source_string = '<foo alpha="bar"></foo>'
        target_string = '<foo alpha="foo"></foo>'
        source = ElementTree.fromstring(source_string)
        target = ElementTree.fromstring(target_string)
        self.assertRaises(AssertionError, compare_element, source, target)

    def test_compare_element_source_not_element(self):
        source_string = '<foo alpha="bar"></foo>'
        target_string = '<foo alpha="foo"></foo>'
        target = ElementTree.fromstring(target_string)
        self.assertRaises(AssertionError, compare_element, source_string, target)

    def test_compare_element_target_not_element(self):
        source_string = '<foo alpha="bar"></foo>'
        target_string = '<foo alpha="foo"></foo>'
        source = ElementTree.fromstring(source_string)
        self.assertRaises(AssertionError, compare_element, source, target_string)

    def test_compare_element_child_different(self):
        source_string = '<foo alpha="bar">some text <baz>qux</baz></foo>'
        target_string = '<foo alpha="bar">some text <baz>zap</baz></foo>'
        source = ElementTree.fromstring(source_string)
        target = ElementTree.fromstring(target_string)
        self.assertRaises(AssertionError, compare_element, source, target)

    def test_compare_element_child_different_number(self):
        source_string = '<foo alpha="bar">some text <baz>qux</baz></foo>'
        target_string = '<foo alpha="bar">some text <baz>zap</baz><fuz></fuz></foo>'
        source = ElementTree.fromstring(source_string)
        target = ElementTree.fromstring(target_string)
        self.assertRaises(AssertionError, compare_element, source, target)
