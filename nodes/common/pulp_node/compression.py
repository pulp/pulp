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
File compression utilities.
"""

import os
import gzip

from tempfile import mktemp


FILE_SUFFIX = '.gz'
TRANSFER_CHUNK_SIZE = 0x3200000  # 50MB


def compress(file_path):
    """
    On-disk file compression using GZIP.
    :param file_path: A fully qualified file path.
    :type file_path: str
    :return: The updated file path.
    :rtype: str
    :raise IOError: on I/O errors.
    """
    tmp_path = mktemp()
    try:
        with open(file_path) as fp_in:
            with gzip.open(tmp_path, 'wb') as fp_out:
                transfer(fp_in, fp_out)
        os.unlink(file_path)
        if not file_path.endswith(FILE_SUFFIX):
            file_path += FILE_SUFFIX
        os.link(tmp_path, file_path)
        return file_path
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def decompress(file_path):
    """
    On-disk file decompression using GZIP.
    :param file_path: A fully qualified file path.
    :type file_path: str
    :raise IOError: on I/O errors.
    """
    tmp_path = mktemp()
    try:
        with gzip.open(file_path) as fp_in:
            with open(tmp_path, 'w+') as fp_out:
                transfer(fp_in, fp_out)
        os.unlink(file_path)
        file_path = file_path.rstrip(FILE_SUFFIX)
        os.link(tmp_path, file_path)
        return file_path
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def compressed(path):
    """
    Get whether the specified path points to a compressed file.
    :param path: A file path.
    :type path: str
    :return: True if compressed.
    :rtype: bool
    """
    return os.path.isfile(path) and path.endswith(FILE_SUFFIX)


def transfer(fp_in, fp_out):
    """
    Transfer bytes between open file pointers using a buffer.
    :param fp_in: Input file.
    :type fp_in: file-like
    :param fp_out: Output file.
    :type fp_out: file-like
    :raise IOError: on I/O errors.
    """
    while True:
        buf = fp_in.read(TRANSFER_CHUNK_SIZE)
        if buf:
            fp_out.write(buf)
        else:
            break