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

from pulp.common.download.request import DownloadRequest

log = getLogger(__name__)


MANIFEST_FILE_NAME = 'manifest.json.gz'
UNITS_FILE_NAME = 'units-%d.json.gz'
KEYS_FILE_NAME = 'keys.json.gz'
MAX_UNITS_FILE_SIZE = 0x40000000  # 1GB

URL = 'url'
UNIT_FILES = 'unit_files'
TOTAL_UNITS = 'total_units'

UNIT_ID = 'unit_id'
TYPE_ID = 'type_id'
UNIT_KEY = 'unit_key'


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
        self.units = 0
        self.unit_files = []
        self.unit_writer = None
        self.unit_catalog = []

    def open(self):
        if not os.path.exists(self.dir_path):
            os.makedirs(self.dir_path)
        self.open_unit_writer()

    def open_unit_writer(self):
        file_name = UNITS_FILE_NAME % len(self.unit_files)
        path = os.path.join(self.dir_path, file_name)
        self.unit_files.append(file_name)
        self.unit_writer = UnitWriter(path)

    def close(self):
        self.unit_writer.close()
        manifest = dict(
            total_units=self.units,
            unit_catalog=self.unit_catalog,
            unit_files=self.unit_files)
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
        self.update_catalog(unit)
        json_unit = json.dumps(unit)
        if self.unit_writer.capacity() < len(json_unit):
            self.unit_writer.close()
            self.open_unit_writer()
        self.unit_writer.add(json_unit)
        self.units += 1

    def update_catalog(self, unit):
        """
        Update the unit catalog.
        :param unit: A content unit.
        :type unit: dict
        """
        entry = {}
        for key in (UNIT_ID, TYPE_ID, UNIT_KEY):
            entry[key] = unit[key]
        self.unit_catalog.append(entry)


class UnitWriter(object):

    def __init__(self, path):
        self.path = path
        self.bytes_written = 0
        self.fp = open(path, 'w+')

    def add(self, json_unit):
        self.bytes_written += len(json_unit)
        self.fp.write(json_unit)
        self.fp.write('\n')

    def close(self):
        self.fp.close()
        compress(self.path)

    def capacity(self):
        return MAX_UNITS_FILE_SIZE - self.bytes_written

    def __len__(self):
        return self.bytes_written


class ManifestReader(object):

    def read_manifest(self, url, downloader):
        """
        Download and return the content of a published manifest.
        :param url: The URL for the manifest.
        :type url: str
        :param downloader: The downloader to use.
        :type downloader: pulp.common.download.downloaders.base.PulpDownloader
        :return: The manifest.
        :rtype: dict
        :raise HTTPError, URL errors.
        :raise ValueError, json decoding errors
        """
        tmp_dir = mkdtemp()
        try:
            destination = os.path.join(tmp_dir, MANIFEST_FILE_NAME)
            request = DownloadRequest(str(url), destination)
            request_list = [request]
            downloader.download(request_list)
            fp = gzip.open(destination)
            try:
                manifest = json.load(fp)
                manifest[URL] = url
                return manifest
            finally:
                fp.close()
        finally:
            shutil.rmtree(tmp_dir)

    def unit_iterator(self, manifest, downloader):
        """
        Create and return a units iterator.
        :param manifest: The manifest object.
        :type manifest: dict
        :param downloader: The downloader to use.
        :return: An initialized iterator.
        :rtype: UnitsIterator
        :raise HTTPError, URL errors.
        """
        request_list = []
        tmp_dir = mkdtemp()
        base_url = manifest[URL].rsplit('/', 1)[0]
        for file_name in manifest[UNIT_FILES]:
            destination = os.path.join(tmp_dir, file_name)
            url = '/'.join((base_url, file_name))
            request = DownloadRequest(str(url), destination)
            request_list.append(request)
        downloader.download(request_list)
        unit_files = [r.destination for r in request_list]
        total_units = manifest[TOTAL_UNITS]
        return UnitsIterator(tmp_dir, total_units, unit_files)


class UnitsIterator:
    """
    Iterates a list of paths to files containing json encoded lists of units.
    """

    @staticmethod
    def get_unit_files(paths):
        for path in paths:
            yield gzip.open(path)

    @staticmethod
    def get_units(paths):
        for fp in UnitsIterator.get_unit_files(paths):
            with fp:
                while True:
                    json_unit = fp.readline()
                    if not json_unit:
                        break
                    yield json.loads(json_unit)

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
        paths = [os.path.join(tmp_dir, fn) for fn in unit_files]
        self.unit_generator = UnitsIterator.get_units(paths)

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
        return self.unit_generator.next()

    def __del__(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def __len__(self):
        return self.total_units

    def __iter__(self):
        return self


# --- utils -----------------------------------------------------------------------------


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
