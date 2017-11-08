from django.test import TestCase

from pulpcore.app import models, viewsets


class TestGetQuerySet(TestCase):
    def test_adds_filters(self):
        """
        Using ImporterViewSet as an example, tests to make sure the correct lookup
        is being added to the queryset based on its "parent_lookup_kwargs" value.
        """
        viewset = viewsets.ImporterViewSet()
        viewset.kwargs = {'repository_name': 'foo'}
        queryset = viewset.get_queryset()

        expected = models.Importer.objects.filter(repository__name='foo')

        self.assertQuerysetEqual(queryset, expected)

    def test_does_not_add_filters(self):
        """
        Using RepositoryViewSet as an example, tests to make sure no filters are applied,
        based on its empty "parent_lookup_kwargs" value.
        """
        viewset = viewsets.RepositoryViewSet()
        viewset.kwargs = {'name': 'foo'}
        queryset = viewset.get_queryset()

        expected = models.Repository.objects.all()

        self.assertQuerysetEqual(queryset, expected)
