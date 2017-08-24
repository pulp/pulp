from gettext import gettext as _

from rest_framework import serializers

from pulpcore.app import models
from pulpcore.app.serializers import GenericKeyValueRelatedField, ModelSerializer


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

    notes = GenericKeyValueRelatedField(
        help_text=_('A mapping of string keys to string values, for storing notes on this object.'),
        required=False
    )

    publishers = serializers.HyperlinkedRelatedField(
        many=True,
        read_only=True,
        view_name='publishers-detail'
    )

    class Meta:
        model = models.Consumer
        fields = ModelSerializer.Meta.fields + ('name', 'description', 'notes')
