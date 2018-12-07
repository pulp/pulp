"""
This module contains custom filters that might be used by more than one ViewSet.
"""
from gettext import gettext as _
from urllib.parse import urlparse
from django.urls import resolve, Resolver404
from django_filters import Filter, DateTimeFilter
from django_filters.fields import IsoDateTimeField

from rest_framework import serializers


class HyperlinkRelatedFilter(Filter):
    """
    Enables a user to filter by a foreign key using that FK's href
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('help_text', _('Foreign Key referenced by HREF'))
        super().__init__(*args, **kwargs)

    def filter(self, qs, value):
        """
        Args:
            qs (django.db.models.query.QuerySet): The Queryset to filter
            value (string): href containing pk for the foreign key instance

        Returns:
            django.db.models.query.QuerySet: Queryset filtered by the foreign key pk
        """

        if value is None:
            # value was not supplied by the user
            return qs

        if not value:
            raise serializers.ValidationError(
                detail=_('No value supplied for {name} filter.').format(name=self.field_name))
        try:
            match = resolve(urlparse(value).path)
        except Resolver404:
            raise serializers.ValidationError(detail=_('URI not valid: {u}').format(u=value))

        pk = match.kwargs['pk']

        key = "{}__pk".format(self.field_name)
        return qs.filter(**{key: pk})


class IsoDateTimeFilter(DateTimeFilter):
    """
    Uses IsoDateTimeField to support filtering on ISO 8601 formated datetimes.
    For context see:
    * https://code.djangoproject.com/ticket/23448
    * https://github.com/tomchristie/django-rest-framework/issues/1338
    * https://github.com/alex/django-filter/pull/264
    """
    field_class = IsoDateTimeField

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('help_text', _('ISO 8601 formatted dates are supported'))
        super().__init__(*args, **kwargs)
