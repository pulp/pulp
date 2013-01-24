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

from pulp.citrus.manifest import Manifest

from logging import getLogger

log = getLogger(__name__)


def join(*parts):
    """
    Join URL and file path fragments.
    :param parts: A list of url fragments.
    :type parts: list
    :return: The joined result.
    :rtype: str
    """
    parts = list(parts)
    parts = parts[0:1]+[p.strip('/') for p in parts[1:]]
    return '/'.join(parts)

def mkdir(file_path):
    """
    Ensure the directory for the specified file path exists.
    :param file_path: The path to a file.
    :type file_path: str
    """
    dir_path = os.path.dirname(file_path)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    else:
        log.debug('directory at: %s, already exists', dir_path)


class Publisher:
    """
    The publisher does the heavy lifting for citrus distributor.
    """

    def publish(self, units):
        """
        Publish the specified units.
        Writes the units.json file and symlinks each of the files associated
        to the unit's "storage_path".
        :param units: A list of units to publish.
        :type units: list
        :return: The manifest and list of links created.
        :rtype: tuple(2)
        """
        raise NotImplementedError()


class FilePublisher(Publisher):
    """
    The file-based publisher.
    :ivar publish_dir: The publish_dir directory for all repositories.
    :type publish_dir: str
    """

    @staticmethod
    def encode_path(path):
        """
        Encode file path.  Encodes path as a SHA-256 hex digest.
        :param path: A file path.
        :type path: str
        :return: The encoded path.
        :rtype: str
        """
        m = hashlib.sha256()
        m.update(path)
        return m.hexdigest()

    def __init__(self, publish_dir, repo_id):
        """
        :param publish_dir: The publishing root directory.
        :type publish_dir: str
        :param repo_id: A repository ID.
        :type repo_id: str
        """
        self.publish_dir = publish_dir
        self.repo_id = repo_id

    def publish(self, units):
        """
        Publish the specified units.
        Writes the units.json file and symlinks each of the
        files associated to the unit.storage_path.
        :param units: A list of units to publish.
        :type units: list
        :return: The manifest and links created.
        :rtype: tuple(2)
        """
        links = self.link(units)
        manifest = self.write_manifest(units)
        return (manifest, links)

    def write_manifest(self, units):
        """
        Write the manifest (units.json) for the specified list of units.
        :param units: A list of units.
        :type units: list
        :return: The absolute path to the written manifest file.
        :rtype: str
        """
        manifest = Manifest()
        dir_path = join(self.publish_dir, self.repo_id)
        mkdir(dir_path)
        return manifest.write(dir_path, units)

    def link(self, units):
        """
        Link files associated with the units into the publish directory.
        The file name is the SHA256 of the unit.storage_path.
        :param units: A list of units to link.
        :type units: list
        :return: A list of (unit, relative_path)
        :rtype: tuple
        """
        links = []
        for unit in units:
            storage_path = unit.get('storage_path')
            if not storage_path:
                # not all units are associated with files.
                continue
            encoded_path = self.encode_path(storage_path)
            relative_path = join(self.repo_id, 'content', encoded_path)
            published_path = join(self.publish_dir, relative_path)
            mkdir(published_path)
            if not os.path.islink(published_path):
                os.symlink(storage_path, published_path)
            link = (unit, relative_path)
            links.append(link)
        return links
