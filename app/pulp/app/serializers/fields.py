from rest_framework import serializers

from pulp.app import models
from pulp.app.serializers import DetailRelatedField


class ContentRelatedField(DetailRelatedField):
    """
    Serializer Field for use when relating to Content Detail Models
    """
    queryset = models.Content.objects.all()


class RepositoryRelatedField(serializers.HyperlinkedRelatedField):
    """
    A serializer field with the correct view_name and lookup_field to link to a repository.
    """
    view_name = 'repositories-detail'
    lookup_field = 'name'
    queryset = models.Repository.objects.all()
