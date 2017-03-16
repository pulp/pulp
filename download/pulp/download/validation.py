import hashlib

from gettext import gettext as _
from logging import getLogger


log = getLogger(__name__)


class ValidationError(Exception):
    """
    Downloaded file failed validation.
    """
    pass


class MismatchError(ValidationError):

    def __init__(self, expected, actual):
        super(MismatchError, self).__init__()
        self.expected = expected
        self.actual = actual


class SizeMismatch(MismatchError):
    """
    The file size does not match what is expected.
    """

    def __str__(self):
        return _(
            'File size mismatch: expected={e} actual={a}'.format(
                e=self.expected,
                a=self.actual))


class DigestMismatch(MismatchError):
    """
    The digest (checksum) did not match what was expected.
    """

    def __str__(self):
        return _(
            'Digest mismatch: expected={e} actual={c}'.format(
                e=self.expected,
                a=self.actual))


class Validation:
    """
    Validation.

    Attributes:
        enforced (bool): Validation enforced.
    """

    def __init__(self, enforced=True):
        """
        Args:
            enforced (bool): Validation enforced.
        """
        self.enforced = enforced

    def update(self, bfr):
        """
        Update collected information.

        Args:
            bfr (str): The actual bytes downloaded.

        Notes:
            Must be implemented by subclass.
        """
        raise NotImplementedError()

    def apply(self):
        """
        Apply the validation.

        Raises:
            ValidationError: When validation has failed.

        Notes:
            Must be implemented by subclass.
        """
        raise NotImplementedError()


class SizeValidation(Validation):
    """
    Validate the size of the downloaded file matches what is expected.

    Attributes:
        expected (int): The expected size in bytes.
        actual (int): The actual size in bytes.
    """

    def __init__(self, expected, enforced=True):
        """
        Args:
            expected (int): The expected file size in bytes.
            enforced (bool): Validation enforced.
        """
        super(SizeValidation, self).__init__(enforced)
        self.expected = expected
        self.actual = 0

    def update(self, bfr):
        """
        Update collected information.

        Args:
            bfr (str): The actual bytes downloaded.
        """
        self.actual += len(bfr)

    def apply(self):
        """
        Apply the validation.

        Raises:
            ValidationError: When validation has failed.
        """
        if not self.enforced:
            return
        if self.expected != self.actual:
            raise SizeMismatch(expected=self.expected, actual=self.actual)


class DigestValidation(Validation):
    """
    Validate the digest (checksum) of the downloaded file matches what is expected.

    Attributes:
        algorithm (hashlib.Algorithm): The hash algorithm.
        expected (int): The expected hex digest.
        actual (int): The actual (calculated) hex digest.
    """

    # ordered by strength
    ALGORITHMS = (
        'sha512',
        'sha384',
        'sha256',
        'sha224',
        'sha1',
        'md5',
    )

    @staticmethod
    def _find_algorithm(name):
        """
        Find the hash algorithm by name in hashlib.

        Args:
            name: The algorithm name.

        Returns:
            hashlib.Algorithm: The algorithm object.

        Raises:
            ValueError: When not found.
        """
        try:
            return getattr(hashlib, name.lower())()
        except AttributeError:
            raise ValueError('Algorithm {} not supported'.format(name))

    def __init__(self, algorithm, digest, enforced=True):
        """
        Args:
            algorithm (str): The hash algorithm.
            digest (str): The expected digest.
            enforced (bool): Validation enforced.

        Raises:
            ValueError: When `algorithm` not supported by hashlib.
        """
        super(DigestValidation, self).__init__(enforced)
        self.algorithm = self._find_algorithm(algorithm)
        self.expected = digest
        self.actual = None

    def update(self, bfr):
        """
        Update collected information.

        Args:
            bfr (str): The actual bytes downloaded.
        """
        self.algorithm.update(bfr)
        self.actual = self.algorithm.hexdigest()

    def apply(self):
        """
        Apply the validation.

        Raises:
            ValidationError: When validation has failed.
        """
        if not self.enforced:
            return
        if self.expected != self.actual:
            raise DigestMismatch(expected=self.expected, actual=self.actual)
