"""
Functions for verifying files.
"""

import hashlib

from pulp.common import error_codes

from pulp.server.exceptions import PulpCodedException


# Number of bytes to read into RAM at a time when validating the checksum
VALIDATION_CHUNK_SIZE = 32 * 1024 * 1024

# Constants to pass in as the checksum type in verify_checksum
TYPE_MD5 = 'md5'
TYPE_SHA = 'sha'
TYPE_SHA1 = 'sha1'
TYPE_SHA256 = 'sha256'

HASHLIB_ALGORITHMS = (TYPE_MD5, TYPE_SHA, TYPE_SHA1, TYPE_SHA256)

CHECKSUM_FUNCTIONS = {
    TYPE_MD5: hashlib.md5,
    TYPE_SHA: hashlib.sha1,
    TYPE_SHA1: hashlib.sha1,
    TYPE_SHA256: hashlib.sha256,
}


class InvalidChecksumType(ValueError):
    """
    Raised when the specified checksum isn't one of the supported TYPE_* constants.
    """
    pass


class VerificationException(ValueError):
    """
    Raised when the verification of a file fails.
    """
    pass


def sanitize_checksum_type(checksum_type):
    """
    Sanitize and validate the checksum type.

    This function will always return the given checksum_type in lower case, unless it is sha, in
    which case it will return "sha1". SHA and SHA-1 are the same algorithm, and so we prefer to use
    "sha1", since it is a more specific name. For some unit types (such as RPM), this can cause
    conflicts inside of Pulp when repos or uploads use a mix of sha and sha1. See
    https://bugzilla.redhat.com/show_bug.cgi?id=1165355

    This function also validates that the checksum_type is a recognized one from the list of known
    hashing algorithms.

    :param checksum_type: The checksum type we are sanitizing
    :type  checksum_type: basestring

    :return: A sanitized checksum type, converting "sha" to "sha1", otherwise returning the given
             checksum_type in lowercase.
    :rtype:  basestring

    :raises PulpCodedException: if the checksum type is not recognized
    """
    lowercase_checksum_type = checksum_type.lower()
    if lowercase_checksum_type == "sha":
        lowercase_checksum_type = "sha1"
    if lowercase_checksum_type not in HASHLIB_ALGORITHMS:
        raise PulpCodedException(error_code=error_codes.PLP1005, checksum_type=checksum_type)
    return lowercase_checksum_type


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

    if checksum_type not in CHECKSUM_FUNCTIONS:
        raise InvalidChecksumType('Unknown checksum type [%s]' % checksum_type)

    hasher = CHECKSUM_FUNCTIONS[checksum_type]()

    file_object.seek(0)
    bits = file_object.read(VALIDATION_CHUNK_SIZE)
    while bits:
        hasher.update(bits)
        bits = file_object.read(VALIDATION_CHUNK_SIZE)

    if hasher.hexdigest() != checksum_value:
        raise VerificationException(hasher.hexdigest())
