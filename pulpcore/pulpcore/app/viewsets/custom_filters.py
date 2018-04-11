"""
This module contains custom filters that might be used by more than one ViewSet.
"""
from gettext import gettext as _
from urllib.parse import urlparse
from uuid import UUID

from django.urls import resolve, Resolver404
from django_filters import filters

from rest_framework import serializers


class NumberRangeFilter(filters.BaseRangeFilter, filters.NumberFilter):
    """
    Enables the user to filter a field by comma separated numbers, allowing them to retrieve more
    than one object in a single query.
    """
    pass


class CharInFilter(filters.BaseInFilter, filters.CharFilter):
    """
    Enables the user to filter a field by comma separated strings, allowing them to retrieve more
    than one object in a single query.
    """
    pass


class HyperlinkRelatedFilter(filters.Filter):
    """
    Enables a user to filter by a foreign key using that FK's href
    """

    def filter(self, qs, value):
        """
        Args:
            qs (django.db.models.query.QuerySet): The Queryset to filter
            value (string): href containing pk for the foreign key instance

        Returns:
            django.db.models.query.QuerySet: Queryset filtered by the foreign key pk
        """

        if not value:
            raise serializers.ValidationError(detail=_('No value supplied for {name} filter.').
                                              format(name=self.name))

        try:
            match = resolve(urlparse(value).path)
        except Resolver404:
            raise serializers.ValidationError(detail=_('URI not valid: {u}').format(u=value))

        pk = match.kwargs['pk']
        try:
            UUID(pk, version=4)
        except ValueError:
            raise serializers.ValidationError(detail=_('UUID invalid: {u}').format(u=pk))

        key = "{}__pk".format(self.name)
        return qs.filter(**{key: pk})
