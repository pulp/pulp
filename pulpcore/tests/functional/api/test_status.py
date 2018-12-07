# coding=utf-8
"""Test the status page."""
import unittest

from jsonschema import validate
from requests.exceptions import HTTPError

from pulp_smash import api, config
from pulp_smash.pulp3.constants import STATUS_PATH

from pulpcore.tests.functional.utils import set_up_module as setUpModule  # noqa:F401

STATUS = {
    '$schema': 'http://json-schema.org/schema#',
    'title': 'Pulp 3 status API schema',
    'description': (
        "Derived from Pulp's actual behaviour and various Pulp issues."
    ),
    'type': 'object',
    'properties': {
        'database_connection': {
            'type': 'object',
            'properties': {'connected': {'type': 'boolean'}},
        },
        'redis_connection': {
            'type': 'object',
            'properties': {'connected': {'type': 'boolean'}},
        },
        'missing_workers': {
            'type': 'array',
            'items': {'type': 'object'},
        },
        'online_workers': {
            'type': 'array',
            'items': {'type': 'object'},
        },
        'versions': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'component': {'type': 'string'},
                    'version': {'type': 'string'},
                }
            },
        },
    }
}


class StatusTestCase(unittest.TestCase):
    """Tests related to the status page.

    This test explores the following issues:

    * `Pulp #2804 <https://pulp.plan.io/issues/2804>`_
    * `Pulp #2867 <https://pulp.plan.io/issues/2867>`_
    * `Pulp #3544 <https://pulp.plan.io/issues/3544>`_
    * `Pulp Smash #755 <https://github.com/PulpQE/pulp-smash/issues/755>`_
    """

    def setUp(self):
        """Make an API client."""
        self.client = api.Client(config.get_config(), api.json_handler)

    def test_get_authenticated(self):
        """GET the status path with valid credentials.

        Verify the response with :meth:`verify_get_response`.
        """
        self.verify_get_response(self.client.get(STATUS_PATH))

    def test_get_unauthenticated(self):
        """GET the status path with no credentials.

        Verify the response with :meth:`verify_get_response`.
        """
        del self.client.request_kwargs['auth']
        self.verify_get_response(self.client.get(STATUS_PATH))

    def test_post_authenticated(self):
        """POST the status path with valid credentials.

        Assert an error is returned.
        """
        with self.assertRaises(HTTPError):
            self.client.post(STATUS_PATH)

    def verify_get_response(self, status):
        """Verify the response to an HTTP GET call.

        Verify that several attributes and have the correct type or value.
        """
        validate(status, STATUS)
        self.assertTrue(status['database_connection']['connected'])
        self.assertTrue(status['redis_connection']['connected'])
        self.assertEqual(status['missing_workers'], [])
        self.assertNotEqual(status['online_workers'], [])
        self.assertNotEqual(status['versions'], [])
