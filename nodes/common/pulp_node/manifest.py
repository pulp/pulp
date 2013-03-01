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
Provides classes for managing the content unit manifest.
The unit(s) manifest is a json encoded file containing a list of all
content units associated with a pulp repository.
"""

import os
import json
import shutil
import gzip

from logging import getLogger
from tempfile import mktemp, mkdtemp

from pulp.common.download.request import DownloadRequest

log = getLogger(__name__)


# --- manifest --------------------------------------------------------------------------


class Manifest(object):
    """
    The manifest is a json encoded file that defines content units
    associated with repository.  The total list of units is stored in separate
    json encoded files.  The manifest contains a list of those file names and
    the total count of units.  For performance reasons, the manifest and the unit
    files are compressed.
    :cvar FILE_NAME: The name of the manifest file.
    :type FILE_NAME: str
    :cvar UNITS_PER_FILE: the number of units per file.
    :type UNITS_PER_FILE: int
    """

    FILE_NAME = 'manifest.json.gz'
    UNITS_PER_FILE = 1000

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
        """
        path = os.path.join(dir_path, self.FILE_NAME)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        fp = open(path, 'w+')
        try:
            n = 0
            unit_files = []
            for _units in split_list(units, self.UNITS_PER_FILE):
                file_name = 'units-%d.json.gz' % n
                _path = os.path.join(dir_path, file_name)
                self._write_units(_path, _units)
                unit_files.append(file_name)
                n += 1
            manifest = dict(total_units=len(units), unit_files=unit_files)
            json.dump(manifest, fp, indent=2)
        finally:
            fp.close()
        File.compress(path)

    def _write_units(self, path, units):
        """
        Write a json file containing the specified units.
        :param path: The file path.
        :param units: A list of units.
        """
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
        manifest = self._read_manifest(url, downloader)
        base_url = url.rsplit('/', 1)[0]
        iterator = self._units_iterator(base_url, manifest, downloader)
        return iterator

    def _read_manifest(self, url, downloader):
        """
        Download and return the content of a published manifest.
        :param url: The URL for the manifest.
        :type url: str
        :param downloader: The downloader to use.
        :type downloader: pulp.common.download.backends.base.DownloadBackend
        :return: The manifest.
        :rtype: dict
        """
        tmp_dir = mkdtemp()
        try:
            destination = os.path.join(tmp_dir, self.FILE_NAME)
            request = DownloadRequest(str(url), destination)
            request_list = [request]
            downloader.download(request_list)
            File.decompress(destination)
            fp = open(destination)
            try:
                return json.load(fp)
            finally:
                fp.close()
        finally:
            shutil.rmtree(tmp_dir)

    def _units_iterator(self, base_url, manifest, downloader):
        """
        Create and return a units iterator.
        :param base_url: The base URL used to download the unit files.
        :type base_url: str
        :param manifest: The manifest object.
        :type manifest: dict
        :param downloader: The downloader to use.
        :return: An initialized iterator.
        :rtype: UnitsIterator
        """
        request_list = []
        tmp_dir = mkdtemp()
        for file_name in manifest['unit_files']:
            destination = os.path.join(tmp_dir, file_name)
            url = '/'.join((base_url, file_name))
            request = DownloadRequest(str(url), destination)
            request_list.append(request)
        downloader.download(request_list)
        unit_files = [r.destination for r in request_list]
        for path in unit_files:
            File.decompress(path)
        total_units = manifest['total_units']
        return UnitsIterator(tmp_dir, total_units, unit_files)


class UnitsIterator:
    """
    Iterates a list of paths to files containing json encoded lists of units.
    """

    def __init__(self, tmp_dir, total_units, unit_files):
        """
        :param tmp_dir:  The directory containing the files.
         :type tmp_dir: str
        :param total_units: The aggregate number of units contained in the files.
        :type total_units: int
        :param unit_files: A list of unit file names.
        :type unit_files: list
        """
        self.tmp_dir = tmp_dir
        self.total_units = total_units
        self.unit_files = unit_files
        self.units = []
        self.file_index = 0
        self.unit_index = 0

    def next(self):
        """
        Get the next unit.
        Reads files as necessary to provide an aggregated list of units.
        :return: The next unit.
        :rtype: dict
        """
        if self.unit_index < len(self.units):
            unit = self.units[self.unit_index]
            self.unit_index += 1
            return unit
        if self.file_index < len(self.unit_files):
            self.unit_index = 1
            path = self.unit_files[self.file_index]
            self.units = self._read(path)
            self.file_index += 1
            if self.units:
                return self.units[0]
        self.close()
        raise StopIteration()

    def _read(self, path):
        fp = open(path)
        try:
            return json.load(fp)
        finally:
            fp.close()

    def close(self):
        try:
            shutil.rmtree(self.tmp_dir)
        except OSError:
            pass

    def __del__(self):
        self.close()

    def __len__(self):
        return self.total_units

    def __iter__(self):
        return self


# --- utils -----------------------------------------------------------------------------


def split_list(list_in, num_lists):
    """
    Split the list info into sub-lists.
    :param list_in: The list to split.
    :type list_in: list
    :param num_lists: The number of requested stub-lists.
    :type num_lists: int
    :return: A list of sub-lists.
    :rtype: list
    """
    return [list_in[x:x + num_lists] for x in xrange(0, len(list_in), num_lists)]


class File(object):

    @staticmethod
    def compress(file_path):
        """
        In-place file compression using gzip.
        :param file_path: A fully qualified file path.
        :type file_path: str
        """
        tmp_path = mktemp()
        shutil.move(file_path, tmp_path)
        fp_in = open(tmp_path)
        try:
            fp_out = gzip.open(file_path, 'wb')
            try:
                File.copy(fp_in, fp_out)
            finally:
                fp_out.close()
        finally:
            fp_in.close()
            os.unlink(tmp_path)

    @staticmethod
    def decompress(file_path):
        """
        In-place file decompression using gzip.
        :param file_path: A fully qualified file path.
        :type file_path: str
        """
        tmp_path = mktemp()
        shutil.move(file_path, tmp_path)
        fp_in = gzip.open(tmp_path)
        try:
            fp_out = open(file_path, 'wb')
            try:
                File.copy(fp_in, fp_out)
            finally:
                fp_out.close()
        finally:
            fp_in.close()
            os.unlink(tmp_path)

    @staticmethod
    def copy(fp_in, fp_out):
        """
        Buffered copy between open file pointers.
        :param fp_in: Input file.
        :type fp_in: file-like
        :param fp_out: Output file.
        :type fp_out: file-like
        """
        while True:
            buf = fp_in.read(0x100000)
            if buf:
                fp_out.write(buf)
            else:
                break


