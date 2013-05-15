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
The manifest is a json encoded file that defines content units
associated with repository.  The total list of units is stored in separate
json encoded files.  The manifest contains a list of those file names and
the total count of units.  For performance reasons, the manifest and the unit
files are compressed.
"""

import os
import json
import shutil
import gzip

from logging import getLogger
from tempfile import mktemp, mkdtemp

from nectar.request import DownloadRequest

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
        Write a manifest file as a json encoded file that defines content units
        associated with repository.  The total list of units is stored in separate
        json encoded files.  The manifest contains a list of those file names and
        the total count of units.  For performance reasons, the manifest and the unit
        files are compressed.
        :param dir_path: The fully qualified path to a directory.
            The directory will be created as necessary.
        :type dir_path: str
        :param units: A list of content units. Each is a dictionary.
        :type units: list
        :raise IOError on I/O errors.
        :raise ValueError on json encoding errors
        """
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        unit_files = self._write_unit_files(dir_path, units)
        manifest = dict(total_units=len(units), unit_files=unit_files)
        path = os.path.join(dir_path, self.FILE_NAME)
        write_json_encoded(manifest, path)

    def read(self, url, downloader):
        """
        Open read the manifest file at the specified URL.
        The contents are uncompressed and unencoded.
        :param url: The URL to download the manifest.
        :type url: str
        :param downloader: A fully configured file downloader.
        :type downloader: nectar.downloaders.base.Downloader
        :return: The contents of the manifest document which is a
            list of content units.  Each unit is a dictionary.
        :rtype: UnitsIterator
        :raise HTTPError, URL errors.
        :raise ValueError, json decoding errors
        """
        manifest = self._read_manifest(url, downloader)
        base_url = url.rsplit('/', 1)[0]
        iterator = self._units_iterator(base_url, manifest, downloader)
        return iterator

    def _write_unit_files(self, dir_path, units):
        """
        Write the list units into json encoded and compressed files.
        The units list is split into sub-lists based on UNITS_PER_FILE.
        :param dir_path: The directory path to where the files are to be written.
        :type dir_path: str
        :param units: A list of content units.
        :type units: list
        :return: The list of file names created.
        :rtype: list
        :raise IOError on I/O errors.
        :raise ValueError on json encoding errors
        """
        n = 0
        unit_files = []
        for _units in split_list(units, self.UNITS_PER_FILE):
            file_name = 'units-%d.json.gz' % n
            path = os.path.join(dir_path, file_name)
            write_json_encoded(_units, path)
            unit_files.append(file_name)
            n += 1
        return unit_files

    def _read_manifest(self, url, downloader):
        """
        Download and return the content of a published manifest.
        :param url: The URL for the manifest.
        :type url: str
        :param downloader: The downloader to use.
        :type downloader: nectar.downloaders.base.Downloader
        :return: The manifest.
        :rtype: dict
        :raise HTTPError, URL errors.
        :raise ValueError, json decoding errors
        """
        tmp_dir = mkdtemp()
        try:
            destination = os.path.join(tmp_dir, self.FILE_NAME)
            request = DownloadRequest(str(url), destination)
            request_list = [request]
            downloader.download(request_list)
            fp = gzip.open(destination)
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
        :raise HTTPError, URL errors.
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
        :raise StopIteration when empty.
        :raise IOError on I/O errors.
        :raise ValueError on json decoding errors
        """
        if self.unit_index < len(self.units):
            unit = self.units[self.unit_index]
            self.unit_index += 1
            return unit
        else:
            self.load()
            return self.next()

    def load(self):
        """
        Load the next units file and populate the list of units.
        :raise StopIteration when empty.
        :raise IOError on I/O errors.
        :raise ValueError on json decoding errors
        """
        self.units = []
        self.unit_index = 0
        if self.file_index < len(self.unit_files):
            path = self.unit_files[self.file_index]
            self.units = self.read(path)
            self.file_index += 1
        if not len(self.units):
            shutil.rmtree(self.tmp_dir, ignore_errors=True)
            raise StopIteration()

    def read(self, path):
        """
        Read and json un-encode the units file at the specified path.
        :param path: Path to a json file containing a list of units.
        :type path: str
        :raise IOError on I/O errors.
        :raise ValueError on json decoding errors
        """
        fp = gzip.open(path)
        try:
            return json.load(fp)
        finally:
            fp.close()

    def __del__(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

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


def write_json_encoded(object_in, path, compressed=True):
    """
    Write the python object using json encoding to the specified path.
    :param object_in: An object to write.
    :type object_in: object
    :param path: A fully qualified path.
    :type path: str
    :param compressed: Indicated the written files should be gzipped.
    :type compressed: bool
    :raise IOError on I/O errors.
    :raise ValueError on json encoding errors
    """
    fp = open(path, 'w+')
    try:
        json.dump(object_in, fp, indent=2)
    finally:
        fp.close()
    if compressed:
        compress(path)


def compress(file_path):
    """
    In-place file compression using gzip.
    :param file_path: A fully qualified file path.
    :type file_path: str
    :raise IOError on I/O errors.
    """
    tmp_path = mktemp()
    shutil.move(file_path, tmp_path)
    fp_in = open(tmp_path)
    try:
        fp_out = gzip.open(file_path, 'wb')
        try:
            copy(fp_in, fp_out)
        finally:
            fp_out.close()
    finally:
        fp_in.close()
        os.unlink(tmp_path)


def copy(fp_in, fp_out):
    """
    Buffered copy between open file pointers using a 1 MB buffer.
    :param fp_in: Input file.
    :type fp_in: file-like
    :param fp_out: Output file.
    :type fp_out: file-like
    :raise IOError on I/O errors.
    """
    while True:
        buf = fp_in.read(0x100000)  # 1MB
        if buf:
            fp_out.write(buf)
        else:
            break
