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
import json
import urllib

class Manifest:
    """
    An http based upstream units (json) document.
    Download the document and perform the JSON conversion.
    @ivar url: The URL for the manifest.
    @type url: str
    """

    FILE_NAME = 'units.json'

    def write(self, dir_path, units):
        path = os.path.join(dir_path, self.FILE_NAME)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        fp = open(path, 'w+')
        try:
            json.dump(units, fp, indent=2)
            return path
        finally:
            fp.close()

    def read(self, url):
        """
        Fetch the document.
        @return: The downloaded json document.
        @rtype: list
        """
        fp_in = urllib.urlopen(url)
        try:
            return json.load(fp_in)
        finally:
            fp_in.close()