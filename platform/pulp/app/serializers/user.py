from gettext import gettext as _

from django.contrib.auth.hashers import make_password
from django.utils import six
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from pulp.app.models import User
from pulp.app.serializers import ModelSerializer


class PasswordSerializer(serializers.CharField):
    """
    Serializer for the password field of User object.
    """
    def to_internal_value(self, data):
        # We're lenient with allowing basic numerics to be coerced into strings,
        # but other types should fail. Eg. unclear if booleans should represent as `true` or `True`,
        # and composites such as lists are likely user error.
        if isinstance(data, bool) or \
                not isinstance(data, six.string_types + six.integer_types + (float,)):
            self.fail('invalid')
        value = six.text_type(make_password(data))
        return value


class UserSerializer(ModelSerializer):
    _href = serializers.HyperlinkedIdentityField(view_name='users-detail',
                                                 lookup_field='username')

    username = serializers.CharField(
        help_text=_("Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."),
        validators=[UniqueValidator(queryset=User.objects.all())],
    )

    is_superuser = serializers.BooleanField(
        help_text=_("Designates that this user has all permissions without explicitly assigning "
                    "them."),
        required=False
    )

    password = PasswordSerializer(write_only=True, help_text=_("Password"))

    class Meta:
        model = User
        fields = ModelSerializer.Meta.fields + ('username', 'is_superuser', 'password')
