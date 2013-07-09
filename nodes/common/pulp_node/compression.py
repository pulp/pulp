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


# --- API --------------------------------------------------------------------


def compress(file_path):
    """
    Compress the file at the specified path using GZIP.
    :param file_path: A fully qualified file path.
    :type file_path: str
    :return: The updated file path.
    :rtype: str
    :raise IOError: on I/O errors.
    """
    tmp_path = mktemp(dir=os.path.dirname(file_path))
    try:
        with open(file_path) as fp_in:
            fp_out = gzip.open(tmp_path, 'wb')
            try:
                transfer(fp_in, fp_out)
            finally:
                fp_out.close()
        if not file_path.endswith(FILE_SUFFIX):
            file_path += FILE_SUFFIX
        if os.path.exists(file_path):
            os.unlink(file_path)
        os.link(tmp_path, file_path)
        return file_path
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def decompress(file_path):
    """
    Decompress the file at the specified path using GZIP.
    :param file_path: A fully qualified file path.
    :type file_path: str
    :raise IOError: on I/O errors.
    """
    tmp_path = mktemp(dir=os.path.dirname(file_path))
    try:
        with open(tmp_path, 'w+') as fp_out:
            fp_in = gzip.open(file_path)
            try:
                transfer(fp_in, fp_out)
            finally:
                fp_in.close()
        file_path = file_path.rstrip(FILE_SUFFIX)
        if os.path.exists(file_path):
            os.unlink(file_path)
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


# --- utils ------------------------------------------------------------------


def transfer(fp_in, fp_out, bufsize=65535):
    while True:
        buf = fp_in.read(bufsize)
        if buf:
            fp_out.write(buf)
        else:
            break
