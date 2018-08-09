# coding=utf-8
"""Tests for Pulp 3's authentication API.

For more information, see the documentation on `Authentication
<http://docs.pulpproject.org/en/3.0/nightly/integration_guide/rest_api/authentication.html>`_.
"""
import unittest
from urllib.parse import urljoin

from requests.auth import AuthBase, HTTPBasicAuth
from requests.exceptions import HTTPError

from pulp_smash import api, config, utils
from pulp_smash.pulp3.constants import BASE_PATH, JWT_PATH, USER_PATH

from tests.functional.utils import set_up_module as setUpModule  # noqa:F401


class AuthTestCase(unittest.TestCase):
    """Test Pulp3 Authentication."""

    def setUp(self):
        """Create class-wide variables."""
        self.cfg = config.get_config()

    def test_base_auth_success(self):
        """Perform HTTP basic authentication with valid credentials.

        Assert that a response indicating success is returned.
        """
        api.Client(self.cfg, api.json_handler).get(
            BASE_PATH,
            auth=HTTPBasicAuth(*self.cfg.pulp_auth),
        )

    def test_base_auth_failure(self):
        """Perform HTTP basic authentication with invalid credentials.

        Assert that a response indicating failure is returned.
        """
        self.cfg.pulp_auth[1] = utils.uuid4()  # randomize password
        with self.assertRaises(HTTPError):
            api.Client(self.cfg, api.json_handler).get(
                BASE_PATH,
                auth=HTTPBasicAuth(*self.cfg.pulp_auth),
            )

    @unittest.skip('https://pulp.plan.io/issues/3248')
    def test_jwt_success(self):
        """Perform JWT authentication with valid credentials.

        Assert that a response indicating success is returned.
        """
        token = _get_token(self.cfg)
        api.Client(self.cfg, api.json_handler).get(BASE_PATH, auth=JWTAuth(token))

    @unittest.skip('https://pulp.plan.io/issues/3248')
    def test_jwt_failure(self):
        """Perform JWT authentication with invalid credentials.

        Assert that a response indicating failure is returned.
        """
        self.cfg.pulp_auth[1] = utils.uuid4()  # randomize password
        with self.assertRaises(HTTPError):
            _get_token(self.cfg)


@unittest.skip('https://pulp.plan.io/issues/3248')
class JWTResetTestCase(unittest.TestCase):
    """Perform series of tests related to JWT reset."""

    def setUp(self):
        """Create a user and several JWT tokens for that user.

        Also, verify that the tokens are valid.
        """
        self.cfg = config.get_config()
        client = api.Client(self.cfg, api.json_handler)

        # Create a temporary user, so that we don't have to use the Pulp admin
        # user for this test.
        body = {key: utils.uuid4() for key in ('username', 'password')}
        self.tmp_user = client.post(USER_PATH, body)
        self.addCleanup(client.delete, self.tmp_user['_href'])

        # Create JWT tokens with the new user, and verify the tokens are
        # usable.
        self.tmp_cfg = config.get_config()
        self.tmp_cfg.pulp_auth = (body['username'], body['password'])
        self.tokens = tuple(_get_token(self.tmp_cfg) for _ in range(2))
        for token in self.tokens:
            client.get(BASE_PATH, auth=JWTAuth(token))

    def test_reset_tokens(self):
        """Repeatedly reset the user's tokens, and verify they're invalid.

        Repeatedly resetting tokens ensures that token resets work even when a
        user has no tokens.
        """
        client = api.Client(self.tmp_cfg)
        path = urljoin(self.tmp_user['_href'], 'jwt_reset/')
        for _ in range(10):
            client.post(path)
        for token in self.tokens:
            with self.assertRaises(HTTPError):
                client.get(BASE_PATH, auth=JWTAuth(token))

    def test_delete_user(self):
        """Delete the user, and verify their tokens are invalid."""
        self.doCleanups()
        client = api.Client(self.tmp_cfg)
        for token in self.tokens:
            with self.assertRaises(HTTPError):
                client.get(BASE_PATH, auth=JWTAuth(token))


class JWTAuth(AuthBase):  # pylint:disable=too-few-public-methods
    """A class that enables JWT authentication with the Requests library.

    For more information, see the Requests documentation on `custom
    authentication
    <http://docs.python-requests.org/en/latest/user/advanced/#custom-authentication>`_.
    """

    def __init__(self, token, header_format='Bearer'):
        """Initialize instance variables."""
        self.token = token
        self.header_format = header_format

    def __call__(self, request):
        """Modify ``request`` authorization header, and return ``request``."""
        request.headers['Authorization'] = ' '.join((
            self.header_format,
            self.token,
        ))
        return request


def _get_token(cfg, pulp_host=None):
    """Return a token for use with JWT authentication.

    A new token is created each time this method is called.

    :param pulp_smash.config.PulpSmashConfig: Information about a Pulp app.
    :param pulp_smash.config.PulpHost pulp_host: A specific host to talk to.
    :returns: A JWT token. This can be used by
        :class:`tests.functional.api.api_v3.test_auth.JWTAuth`.
    """
    return api.Client(cfg, api.json_handler, pulp_host).post(JWT_PATH, {
        'username': cfg.pulp_auth[0],
        'password': cfg.pulp_auth[1],
    })['token']
