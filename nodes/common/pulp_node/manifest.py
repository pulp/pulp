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
from tempfile import mktemp
from uuid import uuid4

from nectar.request import DownloadRequest

log = getLogger(__name__)


# --- constants -------------------------------------------------------------------------

# files
MANIFEST_FILE_NAME = 'manifest.json.gz'
UNITS_FILE_NAME = 'units.json.gz'

# fields within the manifest
MANIFEST_ID = 'manifest_id'
UNIT_FILE = 'unit_file'
TOTAL_UNITS = 'total_units'


# --- manifest --------------------------------------------------------------------------


class ManifestWriter(object):
    """
    The manifest is a json encoded file that defines content units
    associated with repository.  The total list of units is stored in separate
    json encoded files.  The manifest contains a list of those file names and
    the total count of units.  For performance reasons, the manifest and the unit
    files are compressed.
    """

    def __init__(self, dir_path):
        self.dir_path = dir_path
        self.unit_writer = UnitWriter(os.path.join(dir_path, UNITS_FILE_NAME))

    def open(self):
        if not os.path.exists(self.dir_path):
            os.makedirs(self.dir_path)

    def close(self):
        total_units = self.unit_writer.close()
        manifest = {MANIFEST_ID: str(uuid4()), UNIT_FILE: UNITS_FILE_NAME, TOTAL_UNITS: total_units}
        path = os.path.join(self.dir_path, MANIFEST_FILE_NAME)
        json_manifest = json.dumps(manifest, indent=2)
        with open(path, 'w+') as fp:
            fp.write(json_manifest)
        compress(path)

    def add_unit(self, unit):
        """
        Add a unit to the manifest.
        :raise IOError on I/O errors.
        :raise ValueError on json encoding errors
        """
        self.unit_writer.add(unit)


class UnitWriter(object):
    """
    Writes json encoded content units to a file.
    This approach is 30x faster than opening, appending, and closing for each unit.
    :ivar path: The absolute path to the file to be written.
    :type path: str
    :ivar fp: The file pointer used to write units to the file.
    :type fp: A python file object.
    :ivar total_units: Tracks the total number of units written.
    :type total_units: int
    """

    def __init__(self, path):
        """
        :param path: The absolute path to the file to be written.
        :type path: str
        """
        self.path = path
        self.fp = open(path, 'w+')
        self.total_units = 0

    def add(self, unit):
        """
        Add (write) the specified unit to the file as a json encoded string.
        :param unit: A content unit.
        :type unit: dict
        """
        self.total_units += 1
        json_unit = json.dumps(unit)
        self.fp.write(json_unit)
        self.fp.write('\n')

    def close(self):
        """
        Close and compress the associated file.  This method is idempotent.
        :return: The number of units written.
        :rtype: int
        """
        if not self.fp.closed:
            self.fp.close()
            compress(self.path)
        return self.total_units

    def __del__(self):
        # just in case the writer is not properly closed.
        self.close()


class ManifestReader(object):
    """
    :ivar tmp_dir: The path to a directory used for downloaded files.
    :type tmp_dir: str
    :ivar downloader: The downloader to use.
    :type downloader: pulp.common.download.downloaders.base.PulpDownloader
    """

    def __init__(self, downloader, tmp_dir):
        """
        :param tmp_dir: The path to a directory used for downloaded files.
        :type tmp_dir: str
        :param downloader: The downloader to use.
        :type downloader: pulp.common.download.downloaders.base.PulpDownloader
        """
        self.tmp_dir = tmp_dir
        self.downloader = downloader

    def read(self, url):
        """
        Download and return the content of a published manifest.
        :param url: The URL for the manifest.
        :type url: str
        :return: The manifest.
        :rtype: Manifest
        :raise HTTPError, URL errors.
        :raise ValueError, json decoding errors
        """
        manifest = self._download_manifest(url)
        base_url = url.rsplit('/', 1)[0]
        manifest_id = manifest[MANIFEST_ID]
        unit_path = self._download_units(base_url, manifest[UNIT_FILE])
        total_units = manifest[TOTAL_UNITS]
        return Manifest(manifest_id, unit_path, total_units)

    def _download_manifest(self, url):
        """
        Download the manifest at the specified URL.
        :param url: The URL used to download the manifest.
        :type url: str
        :return: The json decoded manifest content.
        :rtype: dict
        """
        destination = os.path.join(self.tmp_dir, MANIFEST_FILE_NAME)
        request = DownloadRequest(str(url), destination)
        request_list = [request]
        self.downloader.download(request_list)
        with gzip.open(destination) as fp:
            return json.load(fp)

    def _download_units(self, base_url, unit_file):
        """
        Download the file containing content units associated with the a manifest
        using the specified base URL and file name.
        :param base_url: The base URL used to download the file.
        :type base_url: str
        :param unit_file: The name of the unit file relative to the base URL.
        :type unit_file: str
        :return: The absolute path to the downloaded file.
        :rtype: str
        """
        destination = os.path.join(self.tmp_dir, unit_file)
        url = '/'.join((base_url, unit_file))
        request = DownloadRequest(str(url), destination)
        request_list = [request]
        self.downloader.download(request_list)
        decompress(destination)
        return destination


class Manifest(object):
    """
    The manifest returned by the ManifestReader.
    Provides structured access to the information contained within the manifest
    and access to the content units associated with the manifest through
    and iterator to ensure a small memory footprint.
    :ivar manifest_id: The unique manifest ID.
    :type manifest_id: str
    :ivar unit_path: The path to the downloaded content units file.
    :type unit_path: str
    :ivar total_units: The number of units in the units file.
    :type total_units: int
    """

    def __init__(self, manifest_id, unit_path, total_units):
        """
        :param tmp_dir: The directory containing the content units.
        :type tmp_dir: str
        :param manifest_id: The unique manifest ID.
        :type manifest_id: str
        :param unit_path: The path to the downloaded content units file.
        :type unit_path: str
        :param total_units: The number of units in the units file.
        :type total_units: int
        """
        self.manifest_id = manifest_id
        self.unit_path = unit_path
        self.total_units = total_units

    def get_units(self):
        """
        Get the content units referenced in the manifest.
        :return: An iterator used to read downloaded content units.
        :rtype: UnitIterator
        """
        return UnitIterator(self.unit_path, self.total_units)


class UnitIterator:
    """
    Used to iterate content units inventory file associated with a manifest.
    The file contains (1) json encoded unit per line.  The total number
    of units in the file is reported by __len__().
    """

    @staticmethod
    def get_units(path):
        with open(path) as fp:
            while True:
                begin = fp.tell()
                json_unit = fp.readline()
                end = fp.tell()
                if json_unit:
                    unit = json.loads(json_unit)
                    length = (end - begin)
                    ref = UnitRef(path, begin, length)
                    yield (unit, ref)
                else:
                    break

    def __init__(self, path, total_units):
        """
        :param path: The absolute path to the units file to be iterated.
        :type path: str
        :param total_units: The number of units contained in the units file.
        :type total_units: int
        """
        self.unit_generator = UnitIterator.get_units(path)
        self.total_units = total_units

    def next(self):
        return self.unit_generator.next()

    def __iter__(self):
        return self

    def __len__(self):
        return self.total_units


class UnitRef(object):
    """
    Reference to a unit within the downloaded units file.
    :ivar path: The absolute path to the units file.
    :type path: str
    :ivar offset: The offset for a specific unit with the file.
    :type offset: int
    :ivar length: The length of a specific unit within the file.
    :type length: int
    """

    def __init__(self, path, offset, length):
        """
        :param path: The absolute path to the units file.
        :type path: str
        :param offset: The offset for a specific unit with the file.
        :type offset: int
        :param length: The length of a specific unit within the file.
        :type length: int
        """
        self.path = path
        self.offset = offset
        self.length = length

    def fetch(self):
        """
        Fetch referenced content unit from the units file.
        :return: The json decoded unit.
        :rtype: dict
        """
        with open(self.path) as fp:
            fp.seek(self.offset)
            json_unit = fp.read(self.length)
            return json.loads(json_unit)


# --- utils -----------------------------------------------------------------------------


def compress(file_path):
    """
    In-place file compression using gzip.
    :param file_path: A fully qualified file path.
    :type file_path: str
    :raise IOError on I/O errors.
    """
    tmp_path = mktemp()
    try:
        shutil.move(file_path, tmp_path)
        with open(tmp_path) as fp_in:
            with gzip.open(file_path, 'wb') as fp_out:
                copy(fp_in, fp_out)
    finally:
        os.unlink(tmp_path)


def decompress(file_path):
    """
    In-place file decompression using gzip.
    :param file_path: A fully qualified file path.
    :type file_path: str
    :raise IOError on I/O errors.
    """
    tmp_path = mktemp()
    try:
        shutil.move(file_path, tmp_path)
        with gzip.open(tmp_path) as fp_in:
            with open(file_path, 'wb') as fp_out:
                copy(fp_in, fp_out)
    finally:
        os.unlink(tmp_path)


def copy(fp_in, fp_out):
    """
    Buffered copy between open file pointers using a 5 MB buffer.
    :param fp_in: Input file.
    :type fp_in: file-like
    :param fp_out: Output file.
    :type fp_out: file-like
    :raise IOError on I/O errors.
    """
    while True:
        buf = fp_in.read(0x500000)  # 5MB
        if buf:
            fp_out.write(buf)
        else:
            break
