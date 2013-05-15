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
from uuid import uuid4

from pulp.common.download.request import DownloadRequest

log = getLogger(__name__)


MANIFEST_FILE_NAME = 'manifest.json.gz'
UNITS_FILE_NAME = 'units.json.gz'

MANIFEST_ID = 'manifest_id'
UNIT_FILE = 'unit_file'


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
        self.unit_writer.close()
        manifest = {MANIFEST_ID: str(uuid4()), UNIT_FILE: UNITS_FILE_NAME}
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

    def __init__(self, path):
        self.path = path
        self.fp = open(path, 'w+')

    def add(self, unit):
        json_unit = json.dumps(unit)
        self.fp.write(json_unit)
        self.fp.write('\n')

    def close(self):
        if self.is_open():
            self.fp.close()
            compress(self.path)
            self.fp = None

    def is_open(self):
        return self.fp is not None

    def __del__(self):
        self.close()


class Manifest(object):

    def __init__(self, tmp_dir, manifest_id, unit_path):
        self.tmp_dir = tmp_dir
        self.manifest_id = manifest_id
        self.unit_path = unit_path

    def get_units(self):
        return UnitIterator(self.unit_path)

    def clean_up(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def __del__(self):
        self.clean_up()


class ManifestReader(object):

    def __init__(self, downloader):
        """
        :param downloader: The downloader to use.
        :type downloader: pulp.common.download.downloaders.base.PulpDownloader
        """
        self.tmp_dir = mkdtemp()
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
        return Manifest(self.tmp_dir, manifest_id, unit_path)

    def _download_manifest(self, url):
        destination = os.path.join(self.tmp_dir, MANIFEST_FILE_NAME)
        request = DownloadRequest(str(url), destination)
        request_list = [request]
        self.downloader.download(request_list)
        with gzip.open(destination) as fp:
            return json.load(fp)

    def _download_units(self, base_url, unit_file):
        destination = os.path.join(self.tmp_dir, unit_file)
        url = '/'.join((base_url, unit_file))
        request = DownloadRequest(str(url), destination)
        request_list = [request]
        self.downloader.download(request_list)
        return destination


class UnitIterator:

    @staticmethod
    def get_units(path):
        with gzip.open(path) as fp:
            while True:
                json_unit = fp.readline()
                if not json_unit:
                    break
                yield json.loads(json_unit)

    def __init__(self, path):
        self.unit_generator = UnitIterator.get_units(path)

    def next(self):
        return self.unit_generator.next()

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
