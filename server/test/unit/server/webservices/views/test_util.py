import json
import mock
import unittest

from django.http import HttpResponse, HttpResponseNotFound

from pulp.server.webservices.controllers.base import json_encoder as pulp_json_encoder
from pulp.server.webservices.views import util


class TestWebservicesUtils(unittest.TestCase):
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
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response._headers.get('content-type'),
                         ('Content-Type', 'application/json'))
        response_content = json.loads(response.content)
        self.assertEqual(response_content, test_content)

    def test_generate_json_response_not_found(self):
        """
        Test that response is correct for non-base HttpResponses
        """
        response = util.generate_json_response(None, HttpResponseNotFound)
        self.assertTrue(isinstance(response, HttpResponseNotFound))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response._headers.get('content-type'),
                         ('Content-Type', 'application/json'))

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
