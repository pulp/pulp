from rest_framework import serializers

from pulp.app import models


class RepositoryRelatedField(serializers.HyperlinkedRelatedField):
    """
    A serializer field with the correct view_name and lookup_field to link to a repository.
    """
    view_name = 'repository-detail'
    lookup_field = 'name'
    queryset = models.Repository.objects.all()
