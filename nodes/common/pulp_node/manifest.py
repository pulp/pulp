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
associated with repository.  The units themselves are stored in a separate
json encoded file.  For performance reasons, the unit files are compressed.
"""

import os
import json

from logging import getLogger

from nectar.request import DownloadRequest

from pulp_node.compression import compress, decompress, compressed


log = getLogger(__name__)


# --- constants -------------------------------------------------------------------------


MANIFEST_FILE_NAME = 'manifest.json'
UNITS_FILE_NAME = 'units.json.gz'


# --- manifest --------------------------------------------------------------------------


class Manifest(object):
    """
    Provides structured access to the information contained within the manifest
    and access to the content units associated with the manifest through
    and iterator to ensure a small memory footprint.
    :ivar id: The unique manifest ID.
    :type id: str
    :ivar total_units: The number of units in the units file.
    :type total_units: int
    :ivar unit_path: The path to the downloaded content units file.
    :type unit_path: str
    """

    def __init__(self, manifest_id=None):
        self.id = manifest_id
        self.total_units = 0
        self.units_path = None

    def fetch(self, url, dir_path, downloader):
        """
        Fetch the manifest file using the specified URL.
        :param url: The URL to the manifest.
        :type url: str
        :param dir_path: The absolute path to a directory for the downloaded manifest.
        :type dir_path: str
        :param downloader: The nectar downloader to be used.
        :type downloader: nectar.downloaders.base.Downloader
        :raise HTTPError: on URL errors.
-       :raise ValueError: on json decoding errors
        """
        destination = os.path.join(dir_path, MANIFEST_FILE_NAME)
        request = DownloadRequest(str(url), destination)
        request_list = [request]
        downloader.download(request_list)
        if compressed(destination):
            destination = decompress(destination)
        with open(destination) as fp:
            manifest = json.load(fp)
            self.__dict__.update(manifest)
            self.units_path = os.path.join(dir_path, os.path.basename(self.units_path))

    def fetch_units(self, url, downloader):
        """
        Fetch the units file referenced in the manifest.
        The file is decompressed and written to the path specified by units_path.
        :param url: The URL to the manifest.  Used as the base URL.
        :type url: str
        :param downloader: The nectar downloader to be used.
        :type downloader: nectar.downloaders.base.Downloader
        :raise HTTPError: on URL errors.
-       :raise ValueError: on json decoding errors
        """
        base_url = url.rsplit('/', 1)[0]
        url = '/'.join((base_url, os.path.basename(self.units_path)))
        request = DownloadRequest(str(url), self.units_path)
        request_list = [request]
        downloader.download(request_list)
        if compressed(self.units_path):
            self.units_path = decompress(self.units_path)

    def read(self, path):
        """
        Read the manifest file at the specified path.
        The manifest is updated using the contents of the read json document.
        :param path: The absolute path to a json encoded manifest file.
        :type path: str
        :raise IOError: on I/O errors.
        :raise ValueError: on json decoding errors
        """
        with open(path) as fp:
            manifest = json.load(fp)
            self.__dict__.update(manifest)

    def write(self, path):
        """
        Write the manifest to a json encoded file at the specified path.
        Returns the path to the written manifest just in case it's compressed in the future.
        :param path: The absolute path to the written json encoded manifest file.
        :type path: str
        :return: The absolute path to the written manifest.
        :rtype: str
        :raise IOError: on I/O errors.
        :raise ValueError: on json encoding errors
        """
        with open(path, 'w+') as fp:
            json.dump(self.__dict__, fp, indent=2)
        return path

    def set_units(self, writer):
        """
        Set the associated units file using the specified writer.
        Updates the units_path and total_units based on what was written by the writer.
        :param writer: The writer used to create the units file.
        :type writer: UnitWriter
        """
        self.units_path = writer.path
        self.total_units = writer.total_units

    def get_units(self):
        """
        Get the content units referenced in the manifest.
        :return: An iterator used to read downloaded content units.
        :rtype: iterable
        :raise IOError: on I/O errors.
-       :raise ValueError: json decoding errors
        """
        if self.total_units:
            return UnitIterator(self.units_path, self.total_units)
        else:
            return []


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
        :raise IOError: on I/O errors
        """
        self.path = path
        self.fp = open(path, 'w+')
        self.total_units = 0

    def add(self, unit):
        """
        Add (write) the specified unit to the file as a json encoded string.
        :param unit: A content unit.
        :type unit: dict
        :raise IOError: on I/O errors.
-       :raise ValueError: json encoding errors
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
            self.path = compress(self.path)
        return self.total_units

    def __enter__(self):
        return self

    def __exit__(self, *unused):
        self.close()
        return False

    def __del__(self):
        # just in case the writer is not properly closed.
        self.close()


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
        :raise IOError: on I/O errors.
-       :raise ValueError: json decoding errors
        """
        with open(self.path) as fp:
            fp.seek(self.offset)
            json_unit = fp.read(self.length)
            return json.loads(json_unit)
