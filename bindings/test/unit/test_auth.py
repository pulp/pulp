import unittest

import mock

from pulp.bindings import auth


class TestUserCreate(unittest.TestCase):
    def setUp(self):
        self.server = mock.MagicMock()
        self.api = auth.UserAPI(self.server)

    def test_correct_passthrough(self):
        self.api.create('me', 'letmein', 'Mr. Me')

        self.server.POST.assert_called_once_with('/v2/users/',
                                                 {'login': 'me',
                                                  'password': 'letmein',
                                                  'name': 'Mr. Me'})
