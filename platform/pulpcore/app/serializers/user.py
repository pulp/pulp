from gettext import gettext as _

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.utils import six
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from pulpcore.app.models import User
from pulpcore.app.serializers import ModelSerializer


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

    password = PasswordSerializer(
        help_text=_("Password"),
        write_only=True
    )

    jwt_secret = serializers.CharField(
        help_text=_("User JWT authentication secret"),
        required=False,
        write_only=not settings.DEBUG  # If pulp in DEBUG mode secret is visible
    )

    reset_jwt_secret = serializers.BooleanField(
        help_text=_("Rest user JWT secret."),
        required=False,
        write_only=True,
    )

    def __init__(self, *args, **kwargs):
        """
        Remove ability to read/set jwt_secret if disabled in settings.
        """
        super(UserSerializer, self).__init__(*args, **kwargs)

        if not settings.JWT_AUTH.get("JWT_ALLOW_SETTING_USER_SECRET"):
            self.fields.pop('jwt_secret')

    def validate(self, data):
        """
        If reset_jwt_secret is True generate user random jwt secret.
        """
        if data["reset_jwt_secret"]:
            data["jwt_secret"] = User.gen_random_jwt_secret()
        return data

    class Meta:
        model = User
        fields = ModelSerializer.Meta.fields + (
            'username', 'is_superuser', 'password', 'jwt_secret', 'reset_jwt_secret')
