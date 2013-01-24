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

"""
Provides classes for managing the content unit manifest.
The unit(s) manifest is a json encoded file containing a list of all
content units associated with a pulp repository.
"""

import os
import json
import urllib2

from gzip import GzipFile
from cStringIO import StringIO
from logging import getLogger

log = getLogger(__name__)


class Manifest:
    """
    The unit(s) manifest is a json encoded file containing a
    list of all content units associated with a pulp repository.
    @cvar FILE_NAME: The name of the manifest file.
    @type FILE_NAME: str
    """

    FILE_NAME = 'units.json.gz'

    def write(self, dir_path, units):
        """
        Write a manifest file containing the specified
        content units into the indicated directory.  The file json
        encoded and compressed using GZIP.
        @param dir_path: The fully qualified path to a directory.
            The directory will be created as necessary.
        @type dir_path: str
        @param units: A list of content units. Each is a dictionary.
        @type units: list
        @return The path of the file written.
        @rtype: str
        """
        path = os.path.join(dir_path, self.FILE_NAME)
        log.debug('writing manifest to: %s', path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        fp = GzipFile(path, 'wb')
        try:
            json.dump(units, fp, indent=2)
            return path
        finally:
            fp.close()

    def read(self, url):
        """
        Open read the manifest file at the specified URL.
        The contents are uncompressed and unencoded.
        @return: The contents of the manifest document which is a
            list of content units.  Each unit is a dictionary.
        @rtype: list
        @raise HTTPError, URL errors.
        @raise ValueError, json decoding errors
        """
        log.debug('reading manifest at url: %s', url)
        fp_in = urllib2.urlopen(url)
        try:
            buf = StringIO(fp_in.read())
            gf_in = GzipFile(fileobj=buf)
            try:
                return json.loads(gf_in.read())
            finally:
                gf_in.close()
        finally:
            fp_in.close()