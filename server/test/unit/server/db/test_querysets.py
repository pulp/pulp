import unittest

from mongoengine import Document
from mongoengine.queryset import DoesNotExist
import mock

from pulp.server import exceptions as pulp_exceptions
from pulp.server.db import querysets


class MockDocument(Document):
    meta = {'queryset_class': querysets.CriteriaQuerySet}


class TestCriteriaQuerySet(unittest.TestCase):
    """
    Tests for custom querysets that search with Criteria objects.
    """

    def test_find_by_criteria_no_translate(self):
        """
        Test that various QuerySet methods are called.
        """

        class MockDocument(Document):
            """Fake Mongoengine document"""
            meta = {'queryset_class': querysets.CriteriaQuerySet}

        mock_crit = mock.MagicMock()
        mock_crit.fields = ['field']
        mock_crit.sort = [('field', 1), ('other', 0)]
        qs = MockDocument.objects
        qs.filter = mock.MagicMock()
        qs.find_by_criteria(mock_crit)

        qs.filter.assert_called_once_with(__raw__=mock_crit.spec)
        qs_only = qs.filter.return_value.only
        qs_order_by = qs_only.return_value.order_by
        qs_skip = qs_order_by.return_value.skip
        qs_limit = qs_skip.return_value.limit

        qs_only.assert_called_once_with('field', 'id')
        qs_order_by.assert_called_once_with('+field', '-other')
        qs_skip.assert_called_once_with(mock_crit.skip)
        qs_limit.assert_called_once_with(mock_crit.limit)

    def test_find_by_criteria_translated(self):
        """
        Test that if the model can translate the criteria, it does.
        """

        class MockDocument(Document):
            """Fake Mongoengine document"""
            meta = {'queryset_class': querysets.CriteriaQuerySet}
            serializer = mock.MagicMock()
            mock_crit = serializer().translate_criteria.return_value
            mock_crit.spec = 'spec'
            mock_crit.fields = ['field']
            mock_crit.sort = [('field', 1), ('other', 0)]
            mock_crit.skip = 'skip'
            mock_crit.limit = 'limit'

        qs = MockDocument.objects
        qs.filter = mock.MagicMock()
        qs.find_by_criteria(mock.MagicMock())

        qs.filter.assert_called_once_with(__raw__='spec')
        qs_only = qs.filter.return_value.only
        qs_order_by = qs_only.return_value.order_by
        qs_skip = qs_order_by.return_value.skip
        qs_limit = qs_skip.return_value.limit

        qs_only.assert_called_once_with('field', 'id')
        qs_order_by.assert_called_once_with('+field', '-other')
        qs_skip.assert_called_once_with('skip')
        qs_limit.assert_called_once_with('limit')

    def test_get_or_404_as_expected(self):
        qs = querysets.CriteriaQuerySet(mock.MagicMock(), mock.MagicMock())
        mock_get = mock.MagicMock()
        qs.get = mock_get
        result = qs.get_or_404(field='value')
        mock_get.assert_called_once_with(field='value')
        self.assertTrue(result is mock_get.return_value)

    def test_get_or_404_missing_obj(self):
        qs = querysets.CriteriaQuerySet(mock.MagicMock(), mock.MagicMock())
        mock_get = mock.MagicMock()
        qs.get = mock_get
        mock_get.side_effect = DoesNotExist
        self.assertRaises(pulp_exceptions.MissingResource, qs.get_or_404, field='value')
        mock_get.assert_called_once_with(field='value')


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
