# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
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
from time import sleep
from logging import getLogger
from socket import error as SocketError
from M2Crypto.SSL import SSLError
from pulp.client.api.base import PulpAPI
from pulp.client.api.server import Bytes


log = getLogger(__name__)


class Memento:
    """
    Upload memento contains an upload uuid.
    """

    ROOT = '~/.pulp/upload'

    def __init__(self, path, checksum):
        """
        @param path: The memento absolute path.
        @type path: str
        @param checksum: The file checksum
        @type checksum: str
        """
        fn = os.path.basename(path)
        root = os.path.expanduser(self.ROOT)
        path = os.path.join(root, str(checksum))
        self.path = os.path.join(path, fn)

    def write(self, uuid):
        """
        Write the memento.
        @param uuid: The memento content.
        @type uuid: str
        """
        self.__mkdir()
        f = open(self.path, 'w')
        f.write(uuid)
        f.close()

    def read(self, delete=True):
        """
        Read the uuid from the memento.
        @param delete: Delete the memento after reading.
        @type delete: bool
        @return: The stored upload uuid.
        """
        try:
            f = open(self.path)
            uuid = f.read()
            f.close()
            if delete:
                self.delete()
            return uuid
        except IOError:
            # normal, may not exist
            pass

    def delete(self):
        """
        Delete (clean up) the memento.
        """
        try:
            os.unlink(self.path)
            os.rmdir(os.path.dirname(self.path))
        except OSError:
            # normal, may not exist
            pass

    def __mkdir(self):
        path = os.path.dirname(self.path)
        if not os.path.exists(path):
            os.makedirs(path)


class UploadAPI(PulpAPI):
    """
    Connection class to access upload related calls
    """
    
    DELAY = 5
    DELAY_INCREMENT = 5
    RETRIES = 5

    def upload(self, path, checksum=None, chunksize=0xA00000):
        """
        Upload a file at the specified path.
        @param path: The abs path to a file to upload.
        @type path: str
        @param checksum: The (optional) file checksum.
        @type checksum: str
        @param checksize: The upload chunking size.  Default=10M.
        @type chunksize: int
        @return: The file upload ID.
        @rtype: str
        """
        if not checksum:
            checksum = self.__checksum(path)
        else:
            checksum = str(checksum)
        memento = Memento(path, checksum)
        uuid = memento.read()
        try:
            uuid, offset = self.__start(path, checksum, uuid)
            if offset < 0:
                # already uploaded
                return uuid
            self.__upload(path, offset, uuid, chunksize)
        except KeyboardInterrupt, ke:
            memento.write(uuid)
            raise ke
        return uuid

    def __start(self, path, checksum, uuid):
        fn = os.path.basename(path)
        size = os.path.getsize(path)
        d = dict(name=fn, checksum=checksum, size=size, id=uuid)
        path = '/services/upload/'
        d = self.server.POST(path, d)[1]
        return (d['id'], int(d['offset']))

    def __upload(self, path, offset, uuid, bufsize):
        f = open(path)
        f.seek(offset)
        while(1):
            buf = f.read(bufsize)
            if buf:
                self.__append(uuid, Bytes(buf))
            else:
                break
        f.close()
        return self

    def __append(self, id, buf):
        delay = self.DELAY
        retries = self.RETRIES
        while True:
            try:
                path = '/services/upload/append/%s/' % id
                return self.server.PUT(path, buf)[1]
            except (SocketError, SSLError), ex:
                msg = 'upload (%s) append failed:%s [wait:%d, retries:%d]'
                log.warn(msg, id, ex, delay, retries)
                if retries:
                    sleep(delay)
                    delay = (delay+self.DELAY_INCREMENT)
                    retries = (retries-1)
                else:
                    raise ex

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
    
    def import_content(self, metadata, uploadid):
        uploadinfo = {'metadata': metadata,
                      'uploadid': uploadid}
        path = "/services/upload/import/"
        return self.server.POST(path, uploadinfo)[1]
