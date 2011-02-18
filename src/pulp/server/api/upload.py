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

"""
File upload classes.
"""

import os
import base64
import logging
from pulp.server.compat import json

log = logging.getLogger(__name__)


class NotFound(Exception):
    def __init__(self, id):
        msg = 'upload file: (%s), not-found' % id
        Exception.__init__(self, msg)

class UploadAlreadyFinished(Exception):
    def __init__(self, md):
        msg = '(%s) already finished, bad append()' % md.name
        Exception.__init__(self, msg)


class UploadNotFinished(Exception):
    def __init__(self, md):
        msg = '(%s) not finished, premature inspect()' % md.name
        Exception.__init__(self, msg)


class Metadata(dict):
    """
    Represents file upload metadata
    """

    FNAME = 'md.json'

    def __init__(self, path):
        """
        @param path: The directory used to read/write the md file.
        @type path: str
        """
        self.path = os.path.join(path, self.FNAME)
        if os.path.exists(self.path):
            f = open(self.path)
            d = json.load(f)
            f.close()
            self.update(d)

    def write(self):
        """
        Write I{self}.
        """
        f = open(self.path, 'w')
        json.dump(self, f)
        f.close()

    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


class File:
    """
    Uploaded file object.
    """

    ROOT = '/tmp/pulp/uploads'

    @classmethod
    def open(cls, name, checksum, size=0):
        """
        Open (initialize) a file upload and return a L{File} object.
        @param name: The file name.
        @type name: str
        @param checksum: The MD5 checksum.  Ensures uniqueness.
        @type checksum: str:hexdigest
        @param size: The file size (bytes).
        @param size: int 
        """
        id = '.'.join((name, str(checksum)))
        f = File(id)
        md = Metadata(f.__path(1))
        md.name = name
        md.checksum = checksum
        md.size = size
        md.write()
        return File(id)

    def __init__(self, id):
        """
        @param id: The file upload ID.
        @type id: str
        """
        self.id = id
        self.__valid()
        self.md = Metadata(self.__path())

    def next(self):
        """
        Get the offset (bytes) of the next segment to be uploaded.
        A value of (-1) indicates the file has already been uploaded
        and no further data should be I{appended}.
        @return: The file offset (bytes).
        @rtype: int 
        """
        self.__valid()
        if not self.__finished():
            return self.__segtotal()
        else:
            return -1

    def append(self, content):
        """
        Append the specified content segment.
        @param content: The (byte) content of the uploaded segment.
        @type content: bytes
        @raise UploadAlreadyFinshed: When attempted on finished upload.
        """
        self.__valid()
        if self.__finished():
            raise UploadAlreadyFinshed(self.md)
        seg = len(self.__segments())
        path = self.__segpath(seg)
        f = open(path, 'w')
        f.write(content)
        f.close()
        if self.__finished():
            self.__build()

    def getpath(self):
        """
        Get the absolute path of the complete uploaded file.
        @return: The path of the uploaded file.
        @rtype: str
        """
        self.__valid()
        path = self.__afpath()
        if not os.path.exists(path):
            if self.__finished():
                self.__build()
            else:
                raise UploadNotFinished(self.md)
        return path

    def delete(self):
        """
        Delete (cleanup) the uploaded file including the
        segments and metadata.
        """
        self.__delete(self.__path())
        
    def __delete(self, dir):
        for fn in os.listdir(dir):
            path = os.path.join(dir,fn)
            if os.path.isdir(path):
                self.__delete(path)
            else:
                os.unlink(path)
        os.rmdir(dir)

    def __build(self):
        af = open(self.__afpath(), 'w')
        for path in self.__segments():
            f = open(path)
            af.write(f.read())
            f.close()
        af.close()

    def __segments(self):
        dir = self.__segroot()
        files = os.listdir(dir)
        files.sort()
        return [os.path.join(dir,fn) for fn in files]

    def __afpath(self):
        fn = self.id.rsplit('.', 1)[0]
        path = os.path.join(self.__path(), fn)
        return path

    def __path(self, autocreate=0):
        path = os.path.join(self.ROOT, self.id)
        if not os.path.exists(path) and autocreate:
            os.makedirs(path)
        return path

    def __segroot(self):
        path = os.path.join(self.__path(), 'segment')
        if not os.path.exists(path):
            os.makedirs(path)
        return path

    def __finished(self):
        uploaded = self.__segtotal()
        return ( self.md.size <= uploaded )

    def __segtotal(self):
        total = 0
        for path in self.__segments():
            total += os.path.getsize(path)
        return total

    def __segpath(self, seg):
        fn = '%.4d.dat' % seg
        path = os.path.join(self.__segroot(), fn)
        return path
    
    def __valid(self):
        if not os.path.exists(self.__path()):
            raise NotFound(self.id)

    def __str__(self):
        return str(self.md)
