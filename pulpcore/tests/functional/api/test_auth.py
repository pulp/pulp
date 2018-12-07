# coding=utf-8
"""Tests for Pulp 3's authentication API.

For more information, see the documentation on `Authentication
<http://docs.pulpproject.org/en/3.0/nightly/integration_guide/rest_api/authentication.html>`_.
"""
import unittest

from requests.auth import HTTPBasicAuth
from requests.exceptions import HTTPError

from pulp_smash import api, config, utils
from pulp_smash.pulp3.constants import USER_PATH

from pulpcore.tests.functional.utils import set_up_module as setUpModule  # noqa:F401


class AuthTestCase(unittest.TestCase):
    """Test Pulp3 Authentication."""

    def setUp(self):
        """Set common variable."""
        self.cfg = config.get_config()

    def test_base_auth_success(self):
        """Perform HTTP basic authentication with valid credentials.

        Assert that a response indicating success is returned.

        Assertion is made by the response_handler.
        """
        api.Client(self.cfg, api.json_handler).get(
            USER_PATH,
            auth=HTTPBasicAuth(*self.cfg.pulp_auth),
        )

    def test_base_auth_failure(self):
        """Perform HTTP basic authentication with invalid credentials.

        Assert that a response indicating failure is returned.
        """
        self.cfg.pulp_auth[1] = utils.uuid4()  # randomize password
        response = api.Client(self.cfg, api.echo_handler).get(
            USER_PATH,
            auth=HTTPBasicAuth(*self.cfg.pulp_auth),
        )
        with self.assertRaises(HTTPError):
            response.raise_for_status()
        for key in ('invalid', 'username', 'password'):
            self.assertIn(
                key,
                response.json()['detail'].lower(),
                response.json()
            )
