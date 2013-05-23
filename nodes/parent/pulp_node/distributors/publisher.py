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

import os

from uuid import uuid4

from pulp_node.manifest import Manifest, UnitWriter, MANIFEST_FILE_NAME, UNITS_FILE_NAME

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


def mkdir(path):
    """
    Ensure the directory at the specified path exists.
    :param file_path: The path to a file.
    :type file_path: str
    """
    if not os.path.exists(path):
        os.makedirs(path)


class Publisher(object):
    """
    The publisher does the heavy lifting for nodes distributor.
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
        :type units: iterable
        """

        dir_path = join(self.publish_dir, self.repo_id)
        units_path = os.path.join(dir_path, UNITS_FILE_NAME)
        manifest_path = os.path.join(dir_path, MANIFEST_FILE_NAME)
        mkdir(dir_path)
        with UnitWriter(units_path) as writer:
            for unit in units:
                self.link_unit(unit)
                writer.add(unit)
        manifest_id = str(uuid4())
        manifest = Manifest(manifest_id)
        manifest.set_units(writer)
        manifest_path = manifest.write(manifest_path)
        return manifest_path

    def link_unit(self, unit):
        """
        Link files associated with the unit into the publish directory.
        The file name is the SHA256 of the unit.storage_path.
        :param unit: A content unit.
        :type unit: dict
        :return: A tuple (unit, relative_path)
        :rtype: tuple
        """
        storage_path = unit.get('storage_path')
        if not storage_path:
            # not all units have associated files.
            return unit, None
        relative_path = join(self.repo_id, unit['relative_path'])
        published_path = join(self.publish_dir, relative_path)
        mkdir(os.path.dirname(published_path))
        if not os.path.islink(published_path):
            os.symlink(storage_path, published_path)
        return unit, relative_path
