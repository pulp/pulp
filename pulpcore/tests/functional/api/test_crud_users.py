# coding=utf-8
"""Tests that CRUD users."""
import unittest

from requests.exceptions import HTTPError

from pulp_smash import api, config, utils
from pulp_smash.pulp3.constants import USER_PATH

from tests.functional.api.utils import gen_username
from tests.functional.utils import set_up_module as setUpModule  # noqa:F401
from tests.functional.utils import skip_if


class UsersCRUDTestCase(unittest.TestCase):
    """CRUD users."""

    @classmethod
    def setUpClass(cls):
        """Create class-wide variables."""
        cls.cfg = config.get_config()
        cls.user = {}

    def setUp(self):
        """Create an API client."""
        self.client = api.Client(self.cfg, api.json_handler)

    def test_01_create_user(self):
        """Create a user."""
        attrs = _gen_verbose_user_attrs()
        type(self).user = self.client.post(USER_PATH, attrs)
        for key, val in attrs.items():
            with self.subTest(key=key):
                if key == 'password':
                    self.assertNotIn(key, self.user)
                else:
                    self.assertEqual(self.user[key], val)

    @skip_if(bool, 'user', False)
    def test_02_read_user(self):
        """Read a user byt its _href."""
        user = self.client.get(self.user['_href'])
        for key, val in user.items():
            with self.subTest(key=key):
                self.assertEqual(val, self.user[key])

    @skip_if(bool, 'user', False)
    def test_02_read_user_with_specific_fields(self):
        """Read a user byt its _href providing specific field name."""
        for field in ('_href', 'username'):
            user = self.client.get(
                self.user['_href'],
                params={'fields': field}
            )
            with self.subTest(key=field):
                self.assertEqual((field,), tuple(user.keys()))

    @skip_if(bool, 'user', False)
    def test_02_read_user_without_specific_fields(self):
        """Read a user by its href excluding specific fields."""
        # requests doesn't allow the use of != in parameters.
        url = '{}?fields!=username'.format(self.user['_href'])
        user = self.client.get(url)
        self.assertNotIn('username', user.keys())

    @skip_if(bool, 'user', False)
    def test_02_read_username(self):
        """Read a user by its username.

        See: `Pulp Issue #3142 <https://pulp.plan.io/issues/3142>`_
        """
        page = self.client.get(USER_PATH, params={
            'username': self.user['username']
        })
        for key, val in self.user.items():
            with self.subTest(key=key):
                self.assertEqual(page['results'][0][key], val)

    @skip_if(bool, 'user', False)
    def test_02_read_users(self):
        """Read all users. Verify that the created user is in the results."""
        users = [
            user for user in self.client.get(USER_PATH)['results']
            if user['_href'] == self.user['_href']
        ]
        self.assertEqual(len(users), 1, users)
        for key, val in users[0].items():
            with self.subTest(key=key):
                self.assertEqual(val, self.user[key])

    @skip_if(bool, 'user', False)
    def test_03_fully_update_user(self):
        """Update a user info using HTTP PUT."""
        attrs = _gen_verbose_user_attrs()
        self.client.put(self.user['_href'], attrs)
        user = self.client.get(self.user['_href'])
        for key, val in attrs.items():
            with self.subTest(key=key):
                if key == 'password':
                    self.assertNotIn(key, user)
                else:
                    self.assertEqual(user[key], val)

    @skip_if(bool, 'user', False)
    def test_03_partially_update_user(self):
        """Update a user info using HTTP PATCH."""
        attrs = _gen_verbose_user_attrs()
        self.client.patch(self.user['_href'], attrs)
        user = self.client.get(self.user['_href'])
        for key, val in attrs.items():
            with self.subTest(key=key):
                if key == 'password':
                    self.assertNotIn(key, user)
                else:
                    self.assertEqual(user[key], val)

    @skip_if(bool, 'user', False)
    def test_04_delete_user(self):
        """Delete an user."""
        self.client.delete(self.user['_href'])
        with self.assertRaises(HTTPError):
            self.client.get(self.user['_href'])

    def test_negative_create_user_with_invalid_parameter(self):
        """Attempt to create user passing invalid parameter.

        Assert response returns an error 400 including ["Unexpected field"].
        """
        attrs = _gen_verbose_user_attrs()
        attrs['foo'] = 'bar'
        response = api.Client(self.cfg, api.echo_handler).post(
            USER_PATH, attrs
        )
        assert response.status_code == 400
        assert response.json()['foo'] == ['Unexpected field']


class InvalidUserCreateTestCase(unittest.TestCase):
    """Invalid user test creation.

    This test targets the followig issues:

    * `Pulp Smash #882 <https://github.com/PulpQE/pulp-smash/issues/882>`_
    * `Pulp Issue #2984 <https://pulp.plan.io/issues/2984>`_
    """

    @classmethod
    def setUpClass(cls):
        """Create class-wide variables."""
        cls.cfg = config.get_config()
        cls.client = api.Client(cls.cfg, api.echo_handler)

    def test_long_username(self):
        """Create a user with long username."""
        attrs = _gen_verbose_user_attrs()
        attrs['username'] = gen_username(151)
        response = self.client.post(USER_PATH, json=attrs)
        error_message = response.json()['username'][0]
        for key in ('150', 'length', 'username', 'less'):
            self.assertIn(key, error_message)
        self.assertEqual(response.status_code, 400)

    def test_invalid_characters(self):
        """Create a user with an username with invalid characters."""
        attrs = _gen_verbose_user_attrs()
        attrs['username'] = gen_username(150, False)
        response = self.client.post(USER_PATH, json=attrs)
        error_message = response.json()['username'][0]
        for key in ('valid', 'username', 'letters', 'numbers', 'characters'):
            self.assertIn(key, error_message)
        self.assertEqual(response.status_code, 400)


def _gen_verbose_user_attrs():
    """Generate a dict with lots of user attributes.

    For most tests, it's desirable to create users with as few attributes as
    possible, so that the tests can specifically target and attempt to break
    specific features. This module specifically targets users, so it makes
    sense to provide as many attributes as possible.
    """
    return {
        'username': utils.uuid4(),
        'password': utils.uuid4(),
    }
