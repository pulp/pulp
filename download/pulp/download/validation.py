import os
import hashlib


class ValidationError(Exception):
    """
    Downloaded file failed validation.

    Attributes:
        path (str): The absolute path to the file.
        reason (str): The reason why validation failed.

    """

    def __init__(self, path, reason=''):
        """
        Args:
            path (str): The absolute path to the file.
            reason (str, optional): The reason why validation failed.

        """
        self.path = path
        self.reason = reason


class ReadError(ValidationError):
    """
    File could not be opened for reading.
    """
    pass


class SizeMismatch(ValidationError):
    """
    The file size does not match what is expected.
    """
    pass


class DigestMismatch(ValidationError):
    """
    The digest (checksum) did not match what was expected.
    """
    pass


class FileValidator:
    """
    Validate downloaded file.
    """

    def __call__(self, request):
        """
        Validate the file downloaded by the request.
        Looks at the request.destination.

        Args:
            request (pulp3.download.Request): A download request.

        Raises:
            ValidationError: When validation has failed.

        Notes:
            Must be implemented by subclass.

        """
        raise NotImplementedError()


class SizeValidator(FileValidator):
    """
    Validate the size of the downloaded file matches what is expected.

    Attributes:
        size (int): The expected file size in bytes.

    """

    def __init__(self, size=None):
        """
        Args:
            size (int): The expected file size in bytes.

        """
        self.size = size

    def __call__(self, request):
        """
        Validate the file downloaded by the request.

        Args:
            request (pulp3.download.Request): A download request.

        Raises:
            SizeMismatch: When validation has failed.

        """
        path = request.destination
        if self.size != os.path.getsize(path):
            raise SizeMismatch(path)


class DigestValidator(FileValidator):
    """
    Validate the digest (checksum) of the downloaded file matches what is expected.

    Attributes:
        algorithm (hashlib.Algorithm): The hash algorithm.
        digest (str): The expected digest.

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
            return getattr(hashlib, name)
        except AttributeError:
            raise ValueError('Algorithm {} not supported'.format(name))

    def __init__(self, algorithm, digest):
        """
        Args:
            algorithm (str): The hash algorithm.
            digest (str): The expected digest.

        Raises:
            ValueError: When `algorithm` not supported by hashlib.

        """
        self.algorithm = self._find_algorithm(algorithm)
        self.digest = digest

    def __call__(self, request):
        """
        Validate the file downloaded by the request.

        Args:
            request (pulp3.download.Request): A download request.

        Raises:
            DigestMismatch: When validation has failed.

        """
        path = request.destination
        with open(path, 'rb') as fp:
            while True:
                bfr = fp.read(1024000)
                if bfr:
                    self.algorithm.update(bfr)
                else:
                    break
        if self.digest != self.algorithm.hexdigest():
            raise DigestMismatch(path)
