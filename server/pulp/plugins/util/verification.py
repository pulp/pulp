# -*- coding: utf-8 -*-
# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""
Functions for verifying files.
"""

import hashlib


# Number of bytes to read into RAM at a time when validating the checksum
VALIDATION_CHUNK_SIZE = 32 * 1024 * 1024

# Constants to pass in as the checksum type in verify_checksum
TYPE_MD5    = 'md5'
TYPE_SHA    = 'sha'
TYPE_SHA1   = 'sha1'
TYPE_SHA256 = 'sha256'

HASHLIB_ALGORITHMS = (TYPE_MD5, TYPE_SHA, TYPE_SHA1, TYPE_SHA256)

CHECKSUM_FUNCTIONS = {
    TYPE_MD5    : hashlib.md5,
    TYPE_SHA    : hashlib.sha1,
    TYPE_SHA1   : hashlib.sha1,
    TYPE_SHA256 : hashlib.sha256,
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
