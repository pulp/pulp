from datetime import datetime, timedelta

import jwt
from django.contrib.auth import get_user_model
from rest_framework_jwt.settings import api_settings


def get_user_key(user):
    """
    Get JWT secret key from user model.

    Args:
        user (pulpcore.app.models.User): User

    Returns:
        str: JWT secret key of user.

    """
    return user.jwt_secret


def payload_handler(username, exp_delta=None):
    """
    Generate token payload.

    The default exp_delta is made from number of seconds in
    `settings.JWT_AUTH.JWT_EXPIRATION_DELTA.`

    Args:
        username (str or pulpcore.app.models.User): users username. Case sensitive.
        exp_delta (datetime.timedelta, optional):
            Token expiration time delta. This will be added to `datetime.utcnow()` to set
            the expiration time.

    Returns:
        dict: payload of JWT token.

    """
    if isinstance(username, get_user_model()):
        username = username.username

    if not exp_delta:
        exp_delta = timedelta(seconds=int(api_settings.JWT_EXPIRATION_DELTA))
    return {
        'username': username,
        'exp': datetime.utcnow() + exp_delta
    }


def get_secret_key(payload):
    """
    Get user secret key from payload.

    Args:
        payload (dict): JWT token payload.

    Returns:
        str: user's secret key

    """
    return get_user_key(get_user_model().objects.get(username=payload.get("username")))


def encode_handler(payload, secret_key=None):
    """
    Generate token from payload.

    Args:
        payload (dict): JWT token payload
        secret_key (str, optional): User's secret key if empty will be derived from payload.

    Returns:
        str: JWT token

    """
    return jwt.encode(
        payload,
        secret_key or get_secret_key(payload),
        api_settings.JWT_ALGORITHM,
    ).decode("utf-8")


def decode_handler(token):
    """
    Decode JWT token into payload.

    Args:
        token (str): JWT token

    Returns:
        dict: payload of JWT token

    """
    return jwt.decode(
        token,
        # Get secret key of user from token to verify token
        get_secret_key(jwt.decode(token, None, False)),
        api_settings.JWT_VERIFY,
        options={
            'verify_exp': api_settings.JWT_VERIFY_EXPIRATION,
        },
        leeway=api_settings.JWT_LEEWAY,
        audience=api_settings.JWT_AUDIENCE,
        issuer=api_settings.JWT_ISSUER,
        algorithms=[api_settings.JWT_ALGORITHM]
    )


def generate_token_offline(username, jwt_secret, exp_delta=timedelta(days=14)):
    """
    Generate JWT token offline from username and secret.

    This function can be used for JWT token generation on client without the need of connection to
    server. The only things you need to know are `username` and `jwt_secret`.

    Args:
        username (str): username
        jwt_secret (str): User's JWT token secret
        exp_delta (datetime.timedelta, optional):
            Token expiration time delta. This will be added to `datetime.utcnow()` to set
            the expiration time. If not set default 14 days is used no matter config.

    Returns:
        str: JWT token

    """
    return encode_handler(
        payload_handler(username, exp_delta),
        jwt_secret
    )
