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
import gzip
import errno

from logging import getLogger

from nectar.request import DownloadRequest
from nectar.listener import AggregatingEventListener

from pulp.server.compat import json

from pulp_node import pathlib
from pulp_node.error import ManifestDownloadError


log = getLogger(__name__)


# --- constants -------------------------------------------------------------------------

MANIFEST_VERSION = 2
MANIFEST_FILE_NAME = 'manifest.json'
UNITS_FILE_NAME = 'units.json.gz'

UNITS_PATH = 'path'
UNITS_TOTAL = 'total'
UNITS_SIZE = 'size'


# --- utils -----------------------------------------------------------------------------

def unzip(path, destination, bfrlen=65535):
    """
    Unzip the file at the specified path.
    :param path: The path to the file to be unzipped.
    :type path: str
    :param destination: The destination path.
    :type destination: str
    :param bfrlen: The buffer size in bytes.
    :type bfrlen: int
    :raise IOError: on any i/o error.
    """
    fp_in = gzip.open(path)
    try:
        with open(destination, 'w+') as fp_out:
            while True:
                bfr = fp_in.read(bfrlen)
                if bfr:
                    fp_out.write(bfr)
                else:
                    break
    finally:
        fp_in.close()


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
    :param publishing_details: Details of how units have been published.
    :type publishing_details: dict
    """

    def __init__(self, path, manifest_id=None):
        """
        :param path: The path to either a directory containing the standard
            named manifest or the absolute path to the manifest.
        :type path: str
        :param manifest_id: An optional manifest ID.
        :type manifest_id: str
        """
        self.id = manifest_id
        self.version = MANIFEST_VERSION
        self.units = {UNITS_PATH: None, UNITS_TOTAL: 0, UNITS_SIZE: 0}
        self.publishing_details = {}
        if os.path.isdir(path):
            path = pathlib.join(path, MANIFEST_FILE_NAME)
        self.path = path

    def write(self):
        """
        Write the manifest to a json encoded file at the specified path.
        :raise IOError: on I/O errors.
        :raise ValueError: on json encoding errors
        """
        state = dict(
            id=self.id,
            version=self.version,
            units=self.units,
            publishing_details=self.publishing_details)
        with open(self.path, 'w+') as fp:
            json.dump(state, fp, indent=2)

    def read(self, migration=None):
        """
        Read the manifest file at the specified path.
        The manifest is updated using the contents of the read json document.
        :param migration: Migration function used to migrate the document.
        :type migration: callable
        :raise IOError: on I/O errors.
        :raise ValueError: on json decoding errors
        """
        if migration:
            migration(self.path)
        with open(self.path) as fp:
            d = json.load(fp)
            self.__dict__.update(d)

    def get_units(self):
        """
        Get the content units referenced in the manifest.
        :return: An iterator used to read downloaded content units.
        :rtype: iterable
        :raise IOError: on I/O errors.
        :raise ValueError: json decoding errors
        """
        total = self.units[UNITS_TOTAL]
        if total:
            path = self.units_path()
            path = self.unzip_units(path)
            return UnitIterator(path, total)
        else:
            return []

    def units_published(self, unit_writer):
        """
        Update the manifest publishing information.
        :param unit_writer: A writer used to publish the units.
        :type unit_writer: UnitWriter
        """
        self.units[UNITS_TOTAL] = unit_writer.total_units
        self.units[UNITS_SIZE] = unit_writer.bytes_written

    def published(self, details):
        """
        Update the publishing details.
        :param details: Publishing details.
        :type details: dict
        """
        self.publishing_details.update(details)

    def is_valid(self):
        """
        Get whether the manifest is valid.
        To start with, compare the version number.
        :return: True if valid.
        :rtype: bool
        """
        try:
            return self.version == MANIFEST_VERSION
        except AttributeError:
            return False

    def has_valid_units(self):
        """
        Validate the associated units file by comparing the size of the
        units file to units_size in the manifest.
        :return: True if valid.
        :rtype: bool
        """
        try:
            path = self.units_path()
            size = os.path.getsize(path)
            return size == self.units[UNITS_SIZE]
        except OSError, e:
            if e.errno != errno.ENOENT:
                raise
        return False

    def unzip_units(self, path):
        """
        Uncompress the unit file at the specified path and update
        the path and size stored in the manifest.
        :param path: The path to a units file.
        :type path: str
        :return: The path to the unzipped file.
        :rtype:str
        :raise IOError: on any i/o error.
        """
        if not path.endswith('.gz'):
            return path
        if not self.has_valid_units():
            return path
        destination = path[:-3]
        unzip(path, destination)
        self.units[UNITS_PATH] = destination
        self.units[UNITS_SIZE] = os.path.getsize(destination)
        os.unlink(path)
        self.write()
        return destination

    def units_path(self):
        """
        Get the absolute path to the associated units file.
        The path is
        """
        return self.units[UNITS_PATH] or pathlib.join(os.path.dirname(self.path), UNITS_FILE_NAME)

    def __eq__(self, other):
        if isinstance(other, Manifest):
            return self.id == other.id
        else:
            return False

    def __ne__(self, other):
        return not self == other


class RemoteManifest(Manifest):
    """
    Represents a remote manifest.
    """

    def __init__(self, url, downloader, destination):
        """
        :param url: The URL to the remote manifest.
        :type url: str
        :param downloader: The downloader used for fetch methods.
        :type downloader: nectar.downloaders.base.Downloader
        :param destination: An absolute path to a file or directory.
        :type destination: str
        """
        if os.path.isdir(destination):
            destination = pathlib.join(destination, MANIFEST_FILE_NAME)
        Manifest.__init__(self, destination)
        self.url = str(url)
        self.downloader = downloader
        self.destination = destination

    def fetch(self, migration=None):
        """
        Fetch the manifest file using the specified URL.
        :param migration: Migration function used to migrate the document.
        :type migration: callable
        :raise ManifestDownloadError: on downloading errors.
        :raise HTTPError: on URL errors.
        :raise ValueError: on json decoding errors
        """
        listener = AggregatingEventListener()
        request = DownloadRequest(self.url, self.destination)
        self.downloader.event_listener = listener
        self.downloader.download([request])
        if listener.failed_reports:
            report = listener.failed_reports[0]
            raise ManifestDownloadError(self.url, report.error_msg)
        self.read(migration)

    def fetch_units(self):
        """
        Fetch the units file referenced in the manifest.
        :raise ManifestDownloadError: on downloading errors.
        :raise HTTPError: on URL errors.
        :raise ValueError: on json decoding errors
        """
        base_url = self.url.rsplit('/', 1)[0]
        url = pathlib.join(base_url, UNITS_FILE_NAME)
        destination = pathlib.join(os.path.dirname(self.path), UNITS_FILE_NAME)
        request = DownloadRequest(str(url), destination)
        listener = AggregatingEventListener()
        self.downloader.event_listener = listener
        self.downloader.download([request])
        if listener.failed_reports:
            report = listener.failed_reports[0]
            raise ManifestDownloadError(self.url, report.error_msg)


class UnitWriter(object):
    """
    Writes json encoded content units to a file.
    This approach is 30x faster than opening, appending, and closing for each unit.
    :ivar path:  The absolute path to a file or directory.  When a directory is specified,
        the standard file name is appended.
    :type path: str
    :ivar fp: The file pointer used to write units to the file.
    :type fp: A python file object.
    :ivar total_units: Tracks the total number of units written.
    :type total_units: int
    :ivar bytes_written: The total number of bytes written.
    :type bytes_written: int
    """

    def __init__(self, path):
        """
        :param path: The absolute path to a file or directory.
            When a directory is specified, the standard file name is appended.
        :type path: str
        :raise IOError: on I/O errors
        """
        if os.path.isdir(path):
            path = pathlib.join(path, UNITS_FILE_NAME)
        self.path = path
        self.fp = gzip.open(path, 'wb')
        self.total_units = 0
        self.bytes_written = 0

    @property
    def closed(self):
        """
        Determines if the file is closed or not. This exists because
        the gzip API changed drastically from python 2.6 to 2.7.
        :return: True if the file is closed.
        :rtype: bool
        """
        try:
            # python 2.7
            return self.fp.closed
        except AttributeError:
            # python 2.6
            return self.fp.fileobj.closed

    def add(self, unit):
        """
        Add (write) the specified unit to the file as a json encoded string.
        :param unit: A content unit.
        :type unit: dict
        :raise IOError: on I/O errors.
        :raise ValueError: json encoding errors
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
        if not self.closed:
            self.fp.close()
            self.bytes_written = os.path.getsize(self.path)
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
        :raise ValueError: json decoding errors
        """
        with open(self.path) as fp:
            fp.seek(self.offset)
            json_unit = fp.read(self.length)
            return json.loads(json_unit)
