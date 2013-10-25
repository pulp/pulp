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
import tarfile

from uuid import uuid4
from tempfile import mkdtemp
from logging import getLogger

from pulp_node import constants
from pulp_node import pathlib
from pulp_node.manifest import Manifest, UnitWriter


log = getLogger(__name__)


# --- utils --------------------------------------------------------

def tar_path(path):
    """
    Construct the tarball path.
    :param path: A path
    :type path: str
    :return: The modified path
    """
    return path + '.TGZ'


def tar_dir(dir_path, tar_path, bufsize=65535):
    """
    Tar up the directory at the specified path.
    :param dir_path: The absolute path to a directory.
    :type dir_path: str
    :param tar_path: The target path.
    :type tar_path: str
    :param bufsize: The buffer size to be used.
    :type bufsize: int
    :return: The path to the tarball
    """
    tb = tarfile.open(tar_path, 'w', bufsize=bufsize)
    try:
        for name in os.listdir(dir_path):
            path = os.path.join(dir_path, name)
            tb.add(path, arcname=name)
        return tar_path
    finally:
        tb.close()


# --- publisher ----------------------------------------------------


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

    def commit(self):
        """
        Commit publishing.
        Supports 2-stage publishing.
        """
        pass


class FilePublisher(Publisher):
    """
    The file-based publisher.
    :ivar publish_dir: The publish_dir directory for all repositories.
    :type publish_dir: str
    :ivar repo_id: The ID of a repository to be published.
    :type repo_id: str
    :ivar tmp_dir: The absolute path to the temporary publishing directory.
    :type tmp_dir: str
    :ivar staged: A flag indicating that publishing has been staged and needs commit.
    :type staged: bool
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
        self.tmp_dir = None
        self.staged = False

    def publish(self, units):
        """
        Publish the specified units.
        Writes the units.json file and symlinks each of the files associated
        to the unit.storage_path.  Publishing is staged in a temporary directory and
        must use commit() to make the publishing permanent.
        :param units: A list of units to publish.
        :type units: iterable
        :return: The absolute path to the manifest.
        :rtype: str
        """
        pathlib.mkdir(self.publish_dir)
        self.tmp_dir = mkdtemp(dir=self.publish_dir)
        with UnitWriter(self.tmp_dir) as writer:
            for unit in units:
                self.publish_unit(unit)
                writer.add(unit)
        manifest_id = str(uuid4())
        manifest = Manifest(self.tmp_dir, manifest_id)
        manifest.units_published(writer)
        manifest.write()
        self.staged = True
        return manifest.path

    def publish_unit(self, unit):
        """
        Publish the file associated with the unit into the publish directory.
        :param unit: A content unit.
        :type unit: dict
        """
        storage_path = unit.get(constants.STORAGE_PATH)
        if not storage_path:
            # not all units have associated files.
            return unit, None
        relative_path = unit[constants.RELATIVE_PATH]
        published_path = pathlib.join(self.tmp_dir, relative_path)
        pathlib.mkdir(os.path.dirname(published_path))
        unit[constants.FILE_SIZE] = os.path.getsize(storage_path)
        if os.path.isdir(storage_path):
            tar_dir(storage_path, tar_path(published_path))
            unit[constants.TARBALL_PATH] = tar_path(relative_path)
        else:
            os.symlink(storage_path, published_path)

    def commit(self):
        """
        Commit publishing.
        Move the tmp_dir to the publish_dir.
        """
        if not self.staged:
            # nothing to commit
            return
        dir_path = pathlib.join(self.publish_dir, self.repo_id)
        os.system('rm -rf %s' % dir_path)
        os.rename(self.tmp_dir, dir_path)
        self.staged = False

    def unstage(self):
        """
        Un-stage publishing.
        """
        os.system('rm -rf %s' % self.tmp_dir)
        self.staged = False

    def __enter__(self):
        return self

    def __exit__(self, *unused):
        self.unstage()
