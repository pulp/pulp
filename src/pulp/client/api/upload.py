# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

import os
import hashlib
import base64
from pulp.client.api.base import PulpAPI


class UploadAPI(PulpAPI):
    """
    Connection class to access upload related calls
    """

    CHUNKSIZE = 0xA00000 # 10 MB

    def upload(self, path):
        """
        Upload a file at the specified path.
        @param path: The abs path to a file to upload.
        @type path: str
        @return: The file upload ID.
        @rtype: str
        """
        id, offset = self.__start(path)
        if offset < 0:
            # already uploaded
            return id
        f = open(path)
        f.seek(offset)
        while(1):
            buf = f.read(self.CHUNKSIZE)
            if buf:
                self.__append(id, buf)
            else:
                break
        f.close()
        return id

    def __append(self, id, buf):
        path = '/uploads/%s/' % id
        buf = base64.b64encode(buf)
        d = dict(encoding='b64', content=buf)
        return self.server.POST(path, d)[1]

    def __start(self, path):
        fn = os.path.basename(path)
        checksum = self.__checksum(path)
        size = os.path.getsize(path)
        d = dict(name=fn, checksum=checksum,size=size)
        path = '/uploads/'
        d = self.server.POST(path, d)[1]
        return (d['id'], int(d['offset']))

    def __checksum(self, path):
        f = open(path)
        checksum = hashlib.md5()
        while(1):
            buf = f.read(8196)
            if buf:
                checksum.update(buf)
            else:
                break
        f.close()
        return checksum.hexdigest()
