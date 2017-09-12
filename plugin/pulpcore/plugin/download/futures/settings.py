"""
Settings represent optional and most likely protocol specific *configuration*.
They are modeled separately and using composition to provide the most flexibility
and re-usability.  Each settings group optionally supports validation.
"""
import os

from gettext import gettext as _


class Settings:
    """
    Download settings.
    """

    __slots__ = ()

    def validate(self):
        """
        Validate the settings.

        Raises:
            ValueError: When validation fails.
        """
        pass

    def _path_readable(self, attribute):
        """
        Validate that the path (value) for specified attribute can be read.

        Args:
            attribute (str): The name of an attribute to validate.

        Raises:
            ValueError: when validation fails.
        """
        path = getattr(self, attribute)
        if not path:
            return
        if os.access(path, os.R_OK):
            return
        raise ValueError(
            _('{a}: "{p}" not found or [READ] permission denied.').format(
                a=attribute,
                p=path))

    def __str__(self):
        return ''


class SSL(Settings):
    """
    SSL/TLS Settings.

    Attributes:
        ca_certificate (str): An optional absolute path to an PEM
            encoded CA certificate.
        client_certificate (str): An optional absolute path to an PEM
            encoded client certificate.
        client_key (str): An optional absolute path to an PEM encoded
            client private key.
        validation (bool): Validate the server SSL certificate.
    """

    __slots__ = (
        'ca_certificate',
        'client_certificate',
        'client_key',
        'validation'
    )

    def __init__(self,
                 ca_certificate=None,
                 client_certificate=None,
                 client_key=None,
                 validation=True):
        """
        Args:
            ca_certificate (str): An optional absolute path to an PEM
                encoded CA certificate.
            client_certificate (str): An optional absolute path to an PEM
                encoded client certificate.  May also contain the private key.
            client_key (str): An optional absolute path to an PEM encoded
                client private key.
            validation (bool): Validate the server SSL certificate.

        Raises:
            ValueError: when validation fails.
        """
        self.ca_certificate = ca_certificate
        self.client_certificate = client_certificate
        self.client_key = client_key
        self.validation = validation

    def validate(self):
        """
        Validate the certificate paths can be read.

        Raises:
            ValueError: When validation fails.
        """
        attributes = (
            'ca_certificate',
            'client_certificate',
            'client_key'
        )
        for attr in attributes:
            self._path_readable(attr)

    def __str__(self):
        description = _('ssl: validation={v} CA={a} key={k} certificate={c}')
        return description.format(
            v=self.validation,
            a=self.ca_certificate,
            k=self.client_key,
            c=self.client_certificate)


class User(Settings):
    """
    User settings used for authentication/authorization.

    Attributes:
        name (str): A username.
        password (str): A password.
    """

    __slots__ = (
        'name',
        'password'
    )

    def __init__(self, name=None, password=None):
        """
        Args:
            name (str): A username.
            password (str): A password.
        """
        self.name = name
        self.password = password

    def __str__(self):
        description = _('User: name={n} password={p}')
        return description.format(
            n=self.name,
            p=self.password)


class Timeout(Settings):
    """
    Timeout settings.

    Attributes:
        connect (int): Connection timeout in seconds.
        read (int): Read timeout in seconds.
    """

    # Default connect timeout (seconds).
    CONNECT = 10
    # Default read timeout (seconds).
    READ = 30

    __slots__ = (
        'connect',
        'read'
    )

    def __init__(self, connect=CONNECT, read=READ):
        """
        Args:
            connect (int): Connection timeout in seconds.
            read (int): Read timeout in seconds.
        """
        self.connect = connect
        self.read = read

    def __str__(self):
        description = _('timeout: connect={c} read={r}')
        return description.format(
            c=self.connect,
            r=self.read)
