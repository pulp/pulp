import jwt
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext as _
from rest_framework import exceptions
from rest_framework_jwt.authentication import JSONWebTokenAuthentication
from rest_framework_jwt.settings import api_settings


class PulpJSONWebTokenAuthentication(JSONWebTokenAuthentication):
    """
    Authenticate user by JWT token.
    """

    def authenticate(self, request):
        """
        Returns a two-tuple of `User` and token if a valid signature has been
        supplied using JWT-based authentication.  Otherwise returns `None`.
        """
        User = get_user_model()
        jwt_value = self.get_jwt_value(request)
        if jwt_value is None:
            return None

        try:
            payload = api_settings.JWT_DECODE_HANDLER(jwt_value)
        except User.DoesNotExist:
            msg = _('User not found.')
            raise exceptions.AuthenticationFailed(msg)
        except jwt.ExpiredSignature:
            msg = _('Token has expired.')
            raise exceptions.AuthenticationFailed(msg)
        except jwt.DecodeError:
            msg = _('Invalid token.')
            raise exceptions.AuthenticationFailed(msg)
        except jwt.InvalidTokenError:
            raise exceptions.AuthenticationFailed()

        user = self.authenticate_credentials(payload)

        return (user, jwt_value)

    def authenticate_credentials(self, payload):
        """
        Returns an active user that matches the payload's user id and email.
        """
        User = get_user_model()
        username = api_settings.JWT_PAYLOAD_GET_USERNAME_HANDLER(payload)

        if not username:
            msg = _('Invalid token.')
            raise exceptions.AuthenticationFailed(msg)

        try:
            user = User.objects.get_by_natural_key(username)
        except User.DoesNotExist:
            msg = _('Invalid token. User not found.')
            raise exceptions.AuthenticationFailed(msg)

        if not user.is_active:
            msg = _('Invalid token. User account is disabled.')
            raise exceptions.AuthenticationFailed(msg)

        return user
