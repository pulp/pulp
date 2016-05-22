"""
Functions for verifying files.
"""

from pulp.server.util import calculate_checksums


class VerificationException(ValueError):
    """
    Raised when the verification of a file fails.
    """
    pass


def verify_size(file_object, expected_size):
    """
    Returns whether or not the size of the contents of the given file-like object match
    the expectation.

    :param file_object: file-like object to verify
    :param expected_size: size to verify the contents of file_object against
    :type  expected_size: int

    :raises VerificationException: if the file did not pass the verification
    """

    # Validate the size by seeking to the end to find the file size with tell()
    file_object.seek(0, 2)
    found_size = file_object.tell()

    if found_size != expected_size:
        raise VerificationException(found_size)


def verify_checksum(file_object, checksum_type, checksum_value):
    """
    Returns whether or not the checksum of the contents of the given file-like object match
    the expectation.

    :param file_object: file-like object to verify
    :type  file_object: file-like object

    :param checksum_type: type of checksum to calculate; must be one of the TYPE_* constants in
                          this module
    :type  checksum_type: str

    :param checksum_value: expected checksum to verify against
    :type  checksum_value: str

    :raises ValueError: if the checksum_type isn't one of the TYPE_* constants
    """
    calculated_sum = calculate_checksums(file_object, [checksum_type])[checksum_type]

    if calculated_sum != checksum_value:
        raise VerificationException(calculated_sum)
