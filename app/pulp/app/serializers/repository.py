from rest_framework import serializers

from pulp.app import models
from pulp.app.serializers import GenericKeyValueRelatedField, ModelSerializer


class RepositorySerializer(ModelSerializer):
    # _href is normally provided by the base class, but Repository's
    # "name" lookup field means _href must be explicitly declared.
    _href = serializers.HyperlinkedIdentityField(
        view_name='repository-detail',
        lookup_field='name',
    )
    name = serializers.CharField(
        help_text='A unique name for this repository.'
    )

    notes = GenericKeyValueRelatedField(
        help_text='A mapping of string keys to string values.',
    )

    class Meta:
        model = models.Repository
        fields = ModelSerializer.Meta.fields + ('name', 'notes')
        filter_fields = ('name',)
