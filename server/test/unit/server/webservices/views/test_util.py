import httplib
import json
import mock
import unittest

from django.http import HttpResponse, HttpResponseNotFound

from pulp.server.exceptions import InputEncodingError, PulpCodedValidationException
from pulp.server.webservices.views import util
from pulp.server.webservices.views.util import (json_body_allow_empty, json_body_required,
                                                page_not_found, pulp_json_encoder)


class TestResponseGenerators(unittest.TestCase):
    """
    Test webservices utilities.
    """

    def test_generate_json_response_default_params(self):
        """
        Make sure that the response is correct under normal conditions.
        """
        test_content = {'foo': 'bar'}
        response = util.generate_json_response(test_content)
        self.assertTrue(isinstance(response, HttpResponse))
        self.assertEqual(response.status_code, httplib.OK)
        self.assertEqual(response._headers.get('content-type'),
                         ('Content-Type', 'application/json; charset=utf-8'))
        response_content = json.loads(response.content)
        self.assertEqual(response_content, test_content)

    def test_generate_json_response_not_found(self):
        """
        Test that response is correct for non-base HttpResponses
        """
        response = util.generate_json_response(None, HttpResponseNotFound)
        self.assertTrue(isinstance(response, HttpResponseNotFound))
        self.assertEqual(response.status_code, httplib.NOT_FOUND)
        self.assertEqual(response._headers.get('content-type'),
                         ('Content-Type', 'application/json; charset=utf-8'))

    def test_generate_json_response_invalid_response_class(self):
        """
        Test that an invalid response_class raises a TypeError.
        """

        class FakeResponse():
            pass

        self.assertRaises(TypeError, util.generate_json_response, FakeResponse)

    @mock.patch('pulp.server.webservices.views.util.json')
    def test_generate_json_response_with_pulp_encoder(self, mock_json):
        """
        Ensure that the shortcut function uses the specified encoder.
        """
        test_content = {'foo': 'bar'}
        util.generate_json_response_with_pulp_encoder(test_content)
        mock_json.dumps.assert_called_once_with(test_content, default=pulp_json_encoder)

    @mock.patch('pulp.server.webservices.views.util.iri_to_uri')
    def test_generate_redirect_response(self, mock_iri_to_uri):
        """
        Test HttpResponseRedirect.
        """
        test_content = {'foo': 'bar'}
        href = '/some/url/'
        response = HttpResponse(content=test_content)
        redirect_response = util.generate_redirect_response(response, href)
        self.assertEqual(redirect_response.status_code, httplib.CREATED)
        self.assertEqual(redirect_response.reason_phrase, 'CREATED')
        self.assertEqual(redirect_response._headers['location'][1],
                         str(mock_iri_to_uri.return_value))
        mock_iri_to_uri.assert_called_once_with(href)


class TestMustHaveJSONBody(unittest.TestCase):

    def test_json_body_required_valid(self):
        mock_request = mock.MagicMock()
        mock_request.body = '{"Valid": "JSON"}'

        @json_body_required
        def mock_function(self, request):
            return request

        final_request = mock_function(self, mock_request)
        self.assertEqual(final_request.body_as_json, {"Valid": "JSON"})

    def test_json_body_required_invalid(self):
        mock_request = mock.MagicMock()
        mock_request.body = '{"Invalid": "JSON"'

        @json_body_required
        def mock_function(self, request):
            return request

        try:
            mock_function(self, mock_request)
        except PulpCodedValidationException, response:
            pass
        else:
            raise AssertionError('PulpCodedValidationException shoudl be raised if invalid JSON'
                                 ' is passed.')

        self.assertEqual(response.http_status_code, httplib.BAD_REQUEST)
        self.assertEqual(response.error_code.code, 'PLP1009')

    def test_json_body_required_empty(self):
        mock_request = mock.MagicMock()
        mock_request.body = ''

        @json_body_required
        def mock_function(self, request):
            return request

        try:
            mock_function(self, mock_request)
        except PulpCodedValidationException, response:
            pass
        else:
            raise AssertionError('PulpCodedValidationException shoudl be raised if invalid JSON'
                                 ' is passed.')

        self.assertEqual(response.http_status_code, httplib.BAD_REQUEST)
        self.assertEqual(response.error_code.code, 'PLP1009')

    def test_json_body_allow_empty_valid(self):
        mock_request = mock.MagicMock()
        mock_request.body = '{"Valid": "JSON"}'

        @json_body_required
        def mock_function(self, request):
            return request

        final_request = mock_function(self, mock_request)
        self.assertEqual(final_request.body_as_json, {"Valid": "JSON"})

    def test_json_body_allow_empty_no_body(self):
        mock_request = mock.MagicMock()
        mock_request.body = ''

        @json_body_allow_empty
        def mock_function(self, request):
            return request

        final_request = mock_function(self, mock_request)
        self.assertEqual(final_request.body_as_json, {})

    def test_json_body_allow_empty_invalid(self):
        mock_request = mock.MagicMock()
        mock_request.body = '{"Invalid": "JSON"'

        @json_body_required
        def mock_function(self, request):
            return request

        try:
            mock_function(self, mock_request)
        except PulpCodedValidationException, response:
            pass
        else:
            raise AssertionError('PulpCodedValidationException shoudl be raised if invalid JSON'
                                 ' is passed.')

        self.assertEqual(response.http_status_code, httplib.BAD_REQUEST)
        self.assertEqual(response.error_code.code, 'PLP1009')


class TestEnsureInputEncoding(unittest.TestCase):

    def test_ensure_invalid_input_encoding(self):
        """
        Test invalid input encoding
        """
        input_data = {"invalid": "json\x81"}
        self.assertRaises(InputEncodingError, util._ensure_input_encoding, input_data)

    def test_ensure_valid_input_encoding(self):
        """
        Test valid input encoding.
        """
        input = {u'valid': u'json'}
        response = util._ensure_input_encoding(input)
        self.assertEqual(response, {'valid': 'json'})


class TestPageNotFound(unittest.TestCase):

    @mock.patch('pulp.server.webservices.views.util.generate_json_response')
    def test_status_code_is_set(self, mock_generate_json_response):
        returned_obj = page_not_found(mock.Mock())
        self.assertEqual(returned_obj.status_code, httplib.NOT_FOUND)

    @mock.patch('pulp.server.webservices.views.util.generate_json_response')
    def test_generate_json_response_is_returned(self, mock_generate_json_response):
        returned_obj = page_not_found(mock.Mock())
        mock_generate_json_response.assert_called_once_with()
        self.assertTrue(returned_obj is mock_generate_json_response.return_value)
