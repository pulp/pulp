import hashlib

from gettext import gettext as _
from logging import getLogger

from .error import DownloadError


log = getLogger(__name__)


class ValidationError(DownloadError):
    """
    Downloaded file failed validation.
    """
    pass


class MismatchError(ValidationError):
    """
    Value mismatch.
    An error related to a difference between and expected and actual value.
    """

    def __init__(self, expected, actual):
        """
        Args:
            expected: The expected value.
            actual: The actual value.
        """
        super(MismatchError, self).__init__()
        self.expected = expected
        self.actual = actual


class SizeMismatch(MismatchError):
    """
    The file size does not match what is expected.
    """

    def __str__(self):
        return _('File size mismatch: expected={e} actual={a}'.format(
            e=self.expected,
            a=self.actual))


class DigestMismatch(MismatchError):
    """
    The digest (checksum) did not match what was expected.
    """

    def __str__(self):
        return _('Digest mismatch: expected={e} actual={a}'.format(
            e=self.expected,
            a=self.actual))


class Validation:
    """
    Validation.

    Attributes:
        enforced (bool): Validation enforced. When enforced, the failed
            validation results in raising a ValidationError.  When not enforced,
            only a warning is logged.
    """

    __slots__ = ('enforced',)

    def __init__(self, enforced=True):
        """
        Args:
            enforced (bool): Validation enforced. When enforced, the failed
                validation results in raising a ValidationError.  When not enforced,
                only a warning is logged.
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

    Examples:
        >>>
        >>> from pulpcore.download import HttpDownload
        >>>
        >>> download = HttpDownload(...)
        >>> download.validations.append(SizeValidation(100))  # Expected file size in bytes.
        >>>
        >>> try:
        >>>     download()
        >>> except ValidationError:
        >>>     # validation failed.
        >>> else:
        >>>     # Go read the downloaded file \o/
        >>>
    """

    __slots__ = ('expected', 'actual')

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
            SizeMismatch: When validation has failed.
        """
        if self.expected == self.actual:
            return
        error = SizeMismatch(expected=self.expected, actual=self.actual)
        if self.enforced:
            raise error
        else:
            log.warn(str(error))

    def __str__(self):
        return _(
            'SizeValidation: expected={e} actual={a}').format(e=self.expected,
                                                              a=self.actual)


class DigestValidation(Validation):
    """
    Validate the digest (checksum) of the downloaded file matches what is expected.

    Attributes:
        algorithm (hashlib.Algorithm): The hash algorithm.
        expected (int): The expected hex digest.
        actual (int): The actual (calculated) hex digest.

    Examples:
        >>>
        >>> from pulpcore.download import HttpDownload, ValidationError
        >>>
        >>> download = HttpDownload(...)
        >>> download.validations.append(DigestValidation('sha256', '..f17a599e4bf624a7c..'))
        >>>
        >>> try:
        >>>     download()
        >>> except ValidationError:
        >>>     # validation failed.
        >>> else:
        >>>     # Go read the downloaded file \o/
        >>>
    """

    __slots__ = (
        'algorithm',
        'expected',
        'actual'
    )

    # ordered by strength
    ALGORITHMS = (
        'sha512',
        'sha384',
        'sha256',
        'sha224',
        'sha1',
        'md5',
    )

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
        self.algorithm = hashlib.new(algorithm)
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
            DigestMismatch: When validation has failed.
        """
        if self.expected == self.actual:
            return
        error = DigestMismatch(expected=self.expected, actual=self.actual)
        if self.enforced:
            raise error
        else:
            log.warn(str(error))

    def __str__(self):
        description = _('DigestValidation: alg={al} expected={e} actual={a}')
        return description.format(
            al=self.algorithm,
            e=self.expected,
            a=self.actual)
