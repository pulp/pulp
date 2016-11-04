"""
Django models related to the Authentication system

The PulpUser and PulpUserManager classes are based on Django documentation for creating custom User
objects. More information can be found here:
https://docs.djangoproject.com/en/1.8/topics/auth/customizing/#specifying-a-custom-user-model
"""
from gettext import gettext as _

from django.core import validators
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
from django.db import models


class PulpUserManager(BaseUserManager):
    """
    A custom manager for PulpUser objects.
    """
    use_in_migrations = True

    def _create_user(self, username, password, is_superuser):
        """
        Creates and saves a PulpUser with the given username and password.
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


class PulpUser(AbstractBaseUser, PermissionsMixin):
    """
    A custom Django User class for Pulp.
    """
    username = models.CharField(
        _('username'),
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

    is_admin = models.BooleanField(default=False)

    objects = PulpUserManager()

    USERNAME_FIELD = 'username'

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
