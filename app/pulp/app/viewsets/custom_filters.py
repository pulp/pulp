"""
This module contains custom filters that might be used by more than one ViewSet.
"""
from django_filters import filters


class CharInFilter(filters.BaseInFilter, filters.CharFilter):
    """
    Enables the user filter a field by a comma separated list of strings, allowing them to retrieve
    more than one object in a single query.
    """
