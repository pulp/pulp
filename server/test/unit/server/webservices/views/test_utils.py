import json
import unittest

from django.http import HttpResponse, HttpResponseNotFound

from pulp.server.webservices.views import utils


class TestWebservicesUtils(unittest.TestCase):
    """
    Test webservices utilities.
    """

    def test_generate_django_response_default_params(self):
        """
        Make sure that the response is correct under normal conditions.
        """
        test_content = """{'foo': 'bar'}"""
        response = utils.generate_django_response(HttpResponse, test_content)
        self.assertTrue(isinstance(response, HttpResponse))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response._headers.get('content-type'),
                         ('Content-Type', 'application/json'))
        response_content = json.loads(response.content)
        self.assertEqual(response_content, test_content)

    def test_generate_django_response_not_found(self):
        """
        Test that response is correct for non-base HttpResponses
        """
        response = utils.generate_django_response(HttpResponseNotFound)
        self.assertTrue(isinstance(response, HttpResponse))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response._headers.get('content-type'),
                         ('Content-Type', 'application/json'))

    def test_generate_django_response_invalid_response_class(self):
        """
        generate_django_response should raise a TypeError for any responses that are not a
        Django HttpResponse object.
        """

        class FakeResponse():
            pass

        self.assertRaises(TypeError, utils.generate_django_response, FakeResponse)
