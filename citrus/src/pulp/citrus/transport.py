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


class FileReader:

    def open(self, repo_id, *path):
        pass


class HttpReader(FileReader):

    def __init__(self, base_url):
        self.base_url = base_url

    def open(self, repo_id, *path):
        url = self.join(self.base_url, repo_id, *path)
        fp_in = urllib.urlopen(url)
        return fp_in

    def download(self, repo_id, unit, unit_in):
        m = hashlib.sha256()
        m.update(unit['storage_path'])
        self.__mkdir(unit['storage_path'])
        self.__mkdir(unit_in.storage_path)
        fp_in = self.open(repo_id, 'content', m.hexdigest())
        try:
            fp_out = open(unit_in.storage_path, 'w+')
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

    def __mkdir(self, path):
        """
        Ensure the specified directory exists.
        @param path: The directory path.
        @type path: str
        """
        path = os.path.dirname(path)
        if not os.path.exists(path):
            os.makedirs(path)

    @staticmethod
    def join(*parts):
        return '/'.join(parts)


class Publisher:

    def publish(self, units):
        pass


class FilePublisher(Publisher):
    """
    The file-based publisher.
    @ivar publish_dir: The publish_dir directory for all repositories.
    @type publish_dir: str
    """

    def __init__(self, publish_dir, repo_id):
        """
        @param publish_dir: The publish_dir directory for all repositories.
        @type publish_dir: str
        @param repo_id: The repository ID.
        @type repo_id: str
        """
        self.publish_dir = os.path.join(publish_dir, repo_id)

    def publish(self, units):
        """
        Publish the specified units.
        Writes the units.json file and symlinks each of the
        files associated to the unit's 'storage_path'.
        @param units: A list of units.
        @type units: list
        """
        self.write(units)
        for u in units:
            self.link(u)

    def write(self, units):
        """
        Write the units.json for the specified list of units.
        Steps:
          1. ensure the directory exists.
          2. write the units.json.
          3. link files assocated with each unit.
        @param units: A list of units.
        @type units: list
        """
        self.__mkdir()
        path = os.path.join(self.publish_dir, 'units.json')
        fp = open(path, 'w+')
        try:
            json.dump(units, fp, indent=2)
        finally:
            fp.close()

    def link(self, unit):
        """
        Link file associated with the unit into the publish directory.
        The file name is the SHA256 of the 'storage_path'.
        @param unit: A content unit.
        @type unit: Unit
        """
        target_dir = self.__mkdir('content')
        source = unit.get('storage_path')
        m = hashlib.sha256()
        m.update(source)
        target = os.path.join(target_dir, m.hexdigest())
        if not os.path.islink(target):
            os.symlink(source, target)

    def __mkdir(self, subdir=None):
        """
        Ensure the I{publish_dir} directory exits.
        @param subdir: An optional sub directory to be created.
        @type str:
        """
        if subdir:
            path = os.path.join(self.publish_dir, subdir)
        else:
            path = self.publish_dir
        if not os.path.exists(path):
            os.makedirs(path)
        return path


class HttpPublisher(FilePublisher):
    pass
