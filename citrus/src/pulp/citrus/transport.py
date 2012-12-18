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

import os
import hashlib
import urllib
import json

from logging import getLogger

log = getLogger(__name__)


def join(*parts):
    """
    Join URL and file path fragments.
    @param parts: A list of url fragments.
    @type parts: list
    @return: The joined result.
    @rtype: str
    """
    parts = list(parts)
    parts = parts[0:1]+[p.strip('/') for p in parts[1:]]
    return '/'.join(parts)

def make_directory(file_path):
    """
    Ensure the directory for the specified file path exists.
    @param file_path: The path to a file.
    @type file_path: str
    """
    dir_path = os.path.dirname(file_path)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)


class FileReader:
    """
    A file-based reader.
    Defines the API for reading and downloading upstream files.
    """

    def open(self, repo_id, *path):
        """
        Open a repository file for reading.
        @param repo_id: A repository ID.
        @type repo_id: str
        @param path: A list of path components relative the base_url.
        @type path: list
        @return: A file-like object that may be used to
            read the contents of the specified file.  The caller
            is responsible for calling close() on the returned object.
        """
        pass

    def download(self, unit, storage_path):
        """
        Download the file referenced in the unit's storage_path to
        the specified location.
        @param unit: A content unit defined in the manifest.
        @type unit: dict
        @param storage_path: The fully qualified file path where downloaded
            file will be stored.
        @type storage_path: str
        """
        pass


class HttpReader(FileReader):
    """
    An HTTP file reader.
    @ivar base_url: The base URL.  Prepended to all paths.
    @type base_url: str
    """

    def __init__(self, base_url):
        """
        @param base_url: The base URL.  Prepended to all paths.
        @type base_url: str
        """
        self.base_url = base_url

    def open(self, *path):
        url = join(self.base_url, *path)
        fp_in = urllib.urlopen(url)
        return fp_in

    def download(self, unit, storage_path):
        url = join(self.base_url, unit['relative_url'])
        fp_in = urllib.urlopen(url)
        try:
            make_directory(storage_path)
            fp_out = open(storage_path, 'w+')
            try:
                while True:
                    bfr = fp_in.read(0x100000)
                    if bfr:
                        fp_out.write(bfr)
                    else:
                        break
            finally:
                fp_out.close()
        finally:
            fp_in.close()


class Publisher:

    def publish(self, units):
        pass


class FilePublisher(Publisher):
    """
    The file-based publisher.
    @ivar publish_dir: The publish_dir directory for all repositories.
    @type publish_dir: str
    """

    @staticmethod
    def encode_path(path):
        """
        Encode file path.
        Encodes path as a SHA-256 hex digest.
        @param path: A file path.
        @type path: str
        @return: The encoded path.
        @rtype: str
        """
        m = hashlib.sha256()
        m.update(path)
        return m.hexdigest()

    def __init__(self, publish_dir, repo_id):
        """
        @param publish_dir: The publishing root directory.
        @type publish_dir: str
        @param repo_id: A repository ID.
        @type repo_id: str
        """
        self.publish_dir = publish_dir
        self.repo_id = repo_id

    def publish(self, units):
        """
        Publish the specified units.
        Writes the units.json file and symlinks each of the
        files associated to the unit's 'storage_path'.
        @param units: A list of units.
        @type units: list
        """
        units = [dict(u) for u in units]
        self.link(units)
        self.write_manifest(units)

    def write_manifest(self, units):
        """
        Write the manifest (units.json) for the specified list of units.
        @param units: A list of units.
        @type units: list
        """
        path = join(self.publish_dir, self.repo_id, 'units.json')
        make_directory(path)
        fp = open(path, 'w+')
        try:
            json.dump(units, fp, indent=2)
        finally:
            fp.close()

    def link(self, units):
        """
        Link file associated with the unit into the publish directory.
        The file name is the SHA256 of the 'storage_path'.
        @param units: A list of units to link.
        @type units: list
        @return: A list of (unit, relative_path)
        @rtype: tuple
        """
        links = []
        for unit in units:
            storage_path = unit.get('storage_path')
            encoded_path = self.encode_path(storage_path)
            relative_path = join(self.repo_id, 'content', encoded_path)
            published_path = join(self.publish_dir, relative_path)
            make_directory(published_path)
            if not os.path.islink(published_path):
                os.symlink(storage_path, published_path)
            link = (unit, relative_path)
            links.append(link)
        return links


class HttpPublisher(FilePublisher):
    """
    The HTTP publisher.
    @ivar repo_id: A repository ID.
    @type repo_id: str
    @ivar virtual_host: The virtual host (base_url, directory)
    @type virtual_host: tuple(2)
    """

    def __init__(self, repo_id, virtual_host):
        """
        @param repo_id: A repository ID.
        @type repo_id: str
        @param virtual_host: The virtual host (base_url, publish_dir)
        @type virtual_host: tuple(2)
        """
        self.virtual_host = virtual_host
        publish_dir = self.virtual_host[1]
        FilePublisher.__init__(self, publish_dir, repo_id)

    def link(self, units):
        #
        # Add the URL to each unit.
        #
        links = FilePublisher.link(self, units)
        for unit, relative_path in links:
            url = join(self.virtual_host[0], relative_path)
            unit['relative_url'] = url
        return links

    def manifest_path(self):
        """
        Get the relative URL path to the manifest.
        @return: The path component of the URL.
        @rtype: str
        """
        return join(self.virtual_host[0], self.repo_id, 'units.json')
