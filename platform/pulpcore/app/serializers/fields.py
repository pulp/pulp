from rest_framework import serializers

from pulpcore.app import models
from pulpcore.app.serializers import DetailRelatedField


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


class ImporterRelatedField(DetailRelatedField):
    """
    Serializer Field for use when relating to Importer Detail Models
    """
    queryset = models.Importer.objects.all()


class PublisherRelatedField(DetailRelatedField):
    """
    Serializer Field for use when relating to Publisher Detail Models
    """
    queryset = models.Publisher.objects.all()
