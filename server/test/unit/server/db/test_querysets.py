import unittest

from mongoengine import DoesNotExist
import mock

from pulp.server import exceptions as pulp_exceptions
from pulp.server.db import querysets


class TestReqoQuerySet(unittest.TestCase):
    """
    Tests for the repository custom query set.
    """

    def test_get_repo(self):
        """
        get_repo_or_missing_resource should return self.get if the repo exists.
        """
        qs = querysets.RepoQuerySet(mock.MagicMock(), mock.MagicMock())
        mock_get = mock.MagicMock()
        qs.get = mock_get
        result = qs.get_repo_or_missing_resource('repo')
        mock_get.assert_called_once_with(repo_id='repo')
        self.assertTrue(result is mock_get.return_value)

    def test_get_missing_repo(self):
        """
        Raise a MissingResource if the repo does not exist.
        """
        qs = querysets.RepoQuerySet(mock.MagicMock(), mock.MagicMock())
        mock_get = mock.MagicMock()
        mock_get.side_effect = DoesNotExist
        qs.get = mock_get
        self.assertRaises(pulp_exceptions.MissingResource, qs.get_repo_or_missing_resource, 'repo')
        mock_get.assert_called_once_with(repo_id='repo')
