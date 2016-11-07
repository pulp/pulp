from rest_framework import serializers

from pulp.app import models
from pulp.app.serializers import ModelSerializer


class UserSerializer(ModelSerializer):
    username = serializers.CharField(
        help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."
    )

    is_superuser = serializers.BooleanField(
        help_text="Designates that this user has all permissions without explicitly assigning "
                  "them."
    )

    class Meta:
        model = models.PulpUser
        fields = ModelSerializer.Meta.fields + ('username', 'is_superuser')
