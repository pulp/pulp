# Copyright (c) 2012 Red Hat, Inc.
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
Provides classes for managing the content unit manifest.
The unit(s) manifest is a json encoded file containing a list of all
content units associated with a pulp repository.
"""

import os
import json
import tempfile
import shutil
import gzip

from logging import getLogger

from pulp.common.download.request import DownloadRequest

log = getLogger(__name__)


# --- manifest --------------------------------------------------------------------------


class Manifest:
    """
    The unit(s) manifest is a json encoded file containing a
    list of all content units associated with a pulp repository.
    :cvar FILE_NAME: The name of the manifest file.
    :type FILE_NAME: str
    """

    FILE_NAME = 'units.json.gz'

    def write(self, dir_path, units):
        """
        Write a manifest file containing the specified
        content units into the indicated directory.  The file json
        encoded and compressed using GZIP.
        :param dir_path: The fully qualified path to a directory.
            The directory will be created as necessary.
        :type dir_path: str
        :param units: A list of content units. Each is a dictionary.
        :type units: list
        :return The path of the file written.
        :rtype: str
        """
        path = os.path.join(dir_path, self.FILE_NAME)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        fp = open(path, 'w+')
        try:
            json.dump(units, fp, indent=2)
        finally:
            fp.close()
        File.compress(path)

    def read(self, url, downloader):
        """
        Open read the manifest file at the specified URL.
        The contents are uncompressed and unencoded.
        :param url: The URL to download the manifest.
        :type url: str
        :param downloader: A fully configured file downloader.
        :type downloader: pulp.common.download.backends.base.DownloadBackend
        :return: The contents of the manifest document which is a
            list of content units.  Each unit is a dictionary.
        :rtype: list
        :raise HTTPError, URL errors.
        :raise ValueError, json decoding errors
        """
        tmp_dir = tempfile.mkdtemp()
        try:
            file_path = os.path.join(tmp_dir, self.FILE_NAME)
            request = DownloadRequest(str(url), file_path)
            request_list = [request]
            downloader.download(request_list)
            File.decompress(file_path)
            fp = open(file_path)
            try:
                return json.load(fp)
            finally:
                fp.close()
        finally:
            shutil.rmtree(tmp_dir)


# --- tools -----------------------------------------------------------------------------

class File:

    @staticmethod
    def decompress(file_path):
        fp_in = gzip.open(file_path)
        try:
            tmp_path = tempfile.mktemp()
            fp_out = open(tmp_path, 'w+')
            try:
                File.copy(fp_in, fp_out)
                os.unlink(file_path)
                os.rename(tmp_path, file_path)
            finally:
                fp_out.close()
        finally:
            fp_in.close()

    @staticmethod
    def compress(file_path):
        fp_in = open(file_path)
        try:
            tmp_path = tempfile.mktemp()
            fp_out = gzip.open(tmp_path, 'wb')
            try:
                File.copy(fp_in, fp_out)
                os.unlink(file_path)
                os.rename(tmp_path, file_path)
            finally:
                fp_out.close()
        finally:
            fp_in.close()

    @staticmethod
    def copy(fp_in, fp_out):
        while True:
            buf = fp_in.read(0x100000)
            if buf:
                fp_out.write(buf)
            else:
                break
