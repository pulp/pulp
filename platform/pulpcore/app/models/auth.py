"""
Django models related to the Authentication system

The User and UserManager classes are based on Django documentation for creating custom User
objects. More information can be found here:
https://docs.djangoproject.com/en/1.8/topics/auth/customizing/#specifying-a-custom-user-model
"""
import random
from gettext import gettext as _

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core import validators
from django.db import models


def gen_random_jwt_secret():
    """
    Generate random 150 chars long string for usage as jwt_secret.

    Returns:
        str: random 150 chars long string
    """
    chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
    return ''.join(random.choice(chars) for i in range(150))


class UserManager(BaseUserManager):
    """
    A custom manager for User objects.
    """
    use_in_migrations = True

    def _create_user(self, username, password, is_superuser):
        """
        Creates and saves a User with the given username and password.
        """
        if not username:
            raise ValueError('The given username must be set')
        user = self.model(username=username, is_superuser=is_superuser)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username, password):
        return self._create_user(username, password, False)

    def create_superuser(self, username, password):
        return self._create_user(username, password, True)


class User(AbstractBaseUser, PermissionsMixin):
    """
    A custom Django User class for Pulp.
    """
    username = models.CharField(
        verbose_name=_('username'),
        max_length=150,
        unique=True,
        validators=[
            validators.RegexValidator(
                r'^[\w.@+-]+$',
                _('Enter a valid username. This value may contain only letters, numbers '
                  'and @/./+/-/_ characters.'),
                'invalid'),
        ],
        error_messages={
            'unique': _("A user with that username already exists.")
        }
    )

    jwt_secret = models.CharField(
        verbose_name=_("User's JWT authentication secret."),
        max_length=150,
        default=gen_random_jwt_secret,
    )

    objects = UserManager()

    USERNAME_FIELD = 'username'

    # Defined outside to be usable as default
    gen_random_jwt_secret = gen_random_jwt_secret

    def get_full_name(self):
        """
        A longer formal identifier for the user.
        :return: Username
        :rtype: str
        """
        return self.username

    def get_short_name(self):
        """
        Short, informal identifier for the user.
        :return: Username
        :rtype: str
        """
        return self.get_full_name()
