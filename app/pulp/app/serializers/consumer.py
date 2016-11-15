from gettext import gettext as _

from rest_framework import serializers

from pulp.app import models
from pulp.app.serializers import NotesKeyValueRelatedField, ModelSerializer


class ConsumerSerializer(ModelSerializer):
    _href = serializers.HyperlinkedIdentityField(
        view_name='consumers-detail',
        lookup_field='name',
    )

    name = serializers.CharField(
        help_text=_("The consumer common name.")
    )

    description = serializers.CharField(
        help_text=_("An optional description."),
        required=False
    )

    notes = NotesKeyValueRelatedField()

    publishers = serializers.HyperlinkedRelatedField(
        many=True,
        read_only=True,
        view_name='publishers-detail'
    )

    class Meta:
        model = models.Consumer
        fields = ModelSerializer.Meta.fields + ('name', 'description', 'notes')
