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


class UploadAlreadyFinished(Exception):
    def __init__(self, md):
        msg = '(%s) already finished, bad append()' % md.name
        Exception.__init__(self, msg)


class UploadNotFinished(Exception):
    def __init__(self, md):
        msg = '(%s) not finished, premature inspect()' % md.name
        Exception.__init__(self, msg)


class Metadata(dict):

    FNAME = 'md.json'

    def __init__(self, path):
        self.path = os.path.join(path, self.FNAME)
        if os.path.exists(self.path):
            f = open(self.path)
            d = json.load(f)
            f.close()
            self.update(d)

    def write(self):
        f = open(self.path, 'w')
        json.dump(self, f)
        f.close()

    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


class File:

    ROOT = '/tmp/pulp/uploads'

    @classmethod
    def open(cls, name, checksum, size=0):
        id = '.'.join((name, str(checksum)))
        f = File(id)
        md = Metadata(f.__path())
        md.name = name
        md.checksum = checksum
        md.size = size
        md.write()
        return File(id)

    def __init__(self, id):
        self.id = id
        self.md = Metadata(self.__path())

    def next(self):
        if not self.__finished():
            return self.__segtotal()
        else:
            return -1

    def append(self, content):
        if self.__finished():
            raise UploadAlreadyFinshed(self.md)
        seg = len(self.__segments())
        path = self.__segpath(seg)
        f = open(path, 'w')
        f.write(content)
        f.close()
        if self.__finished():
            self.__build()

    def inspect(self):
        path = self.__afpath()
        if not os.path.exists(path):
            if self.__finished():
                self.__build()
            else:
                raise UploadNotFinished(self.md)
        return (path, self.md.size, self.md.checksum)

    def delete(self, dir=None):
        if not dir:
            dir = self.__path()
        for fn in os.listdir(dir):
            path = os.path.join(dir,fn)
            if os.path.isdir(path):
                self.delete(path)
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

    def __path(self):
        path = os.path.join(self.ROOT, self.id)
        if not os.path.exists(path):
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
        fn = '%d.dat' % seg
        path = os.path.join(self.__segroot(), fn)
        return path

    def __str__(self):
        return str(self.md)
