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

"""
File upload classes.
Usage:

path = '/tmp/test.dat'

# open (initialize) the upload file
file = File.open(path, '0xFFFF', 30)

# grab the ID for use later..
id = file.id

# upload content (chunks)
fp = open(path)
offset = file.next()
if offset < 0:
  return # all chunks uploaded
fp.seek(offset)
while(1):
  buf = fp.read(4096) # 4k chunk
  file.append(buf)

# Now, lets use the uploaded file
file = File(id)
path = file.getpath()
...
# COPY/RENAME uploaded file
...
# clean up
file.delete()

Done!
"""

import logging
import os
import shutil
from uuid import uuid4

from pulp.server import util
from pulp.server.api.file import FileApi
from pulp.server.api.synchronizers import BaseSynchronizer
from pulp.server.compat import json
from pulp.server.event.dispatcher import event
from pulp.server.exceptions import PulpException


log = logging.getLogger(__name__)


class NotValid(Exception):
    def __init__(self, id):
        msg = 'upload file: (%s), not-valid' % id
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

    ROOT = '/var/lib/pulp/uploads'

    @classmethod
    def open(cls, name, checksum, size, uuid=None):
        """
        Open (initialize) a file upload and return a L{File} object.
        @param name: The file name.
        @type name: str
        @param checksum: The MD5 checksum.  Ensures uniqueness.
        @type checksum: str:hexdigest
        @param size: The file size (bytes).
        @param size: int
        @param uuid: The (optional) upload uuid used to resume upload.
        @type uuid: str
        """
        if not uuid:
            uuid = str(uuid4())
        else:
            log.info('upload resumed: %s (%s)', uuid, name)
        f = File(uuid)
        md = Metadata(f.__path())
        md.uuid = uuid
        md.name = name
        md.checksum = checksum
        md.size = size
        md.valid = 1
        md.write()
        f.md = md
        return f

    def __init__(self, uuid):
        """
        @param id: The file upload ID.
        @type id: str
        """
        self.uuid = uuid
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
            return - 1

    def append(self, content):
        """
        Append the specified content segment.
        @param content: The (byte) content of the uploaded segment.
        @type content: bytes
        @raise UploadAlreadyFinshed: When attempted on finished upload.
        """
        self.__valid()
        if self.__finished():
            raise UploadAlreadyFinished(self.md)
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
        self.md.valid = 0

    def __delete(self, dir):
        for fn in os.listdir(dir):
            path = os.path.join(dir, fn)
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
        return [os.path.join(dir, fn) for fn in files]

    def __afpath(self):
        path = os.path.join(self.__path(), self.md.name)
        return path

    def __path(self):
        path = os.path.join(self.ROOT, self.uuid)
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
        return (self.md.size <= uploaded)

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
        if not self.md.valid:
            raise NotValid(self.uuid)

    def __str__(self):
        return str(self.md)

PACKAGE_LOCATION = util.top_package_location()

class ImportUploadContent:
    def __init__(self, metadata, upload_id):
        self.metadata = metadata
        self.upload_id = upload_id

    def process(self):
        """
        import the content into pulp database
        """
        if self.metadata['type'] == 'rpm':
            return self.__import_rpm()
        if self.metadata['type'] == 'file':
            return self.__import_file()

    def __import_rpm(self):
        """
        import the rpms into pulp database
        """
        log.info("Importing rpm metadata content into pulp")

        # check required options
        try:
            (name, version, release, epoch, arch) = self.metadata['nvrea']
        except KeyError:
            raise PulpException("metadata is missing [nvrea] info to import an rpm")

        try:
            checksum = self.metadata['checksum']
            hashtype = self.metadata['hashtype']
        except:
            raise PulpException("metadata is missing rpm checksum or hashtype value")
        try:
            pkgname = self.metadata['pkgname']
        except KeyError:
            raise PulpException("metadata is missing rpm pkgname value")

        try:
            size = self.metadata['size']
        except KeyError:
            raise PulpException("metadata is missing rpm size value")
        
        description = None
        if self.metadata.has_key('description'):
            description = self.metadata['description']
        buildhost = None
        if self.metadata.has_key('buildhost'):
            buildhost = self.metadata['buildhost']
        license = None
        if self.metadata.has_key('license'):
            license = self.metadata['license']
        group = None
        if self.metadata.has_key('group'):
            group = self.metadata['group']
        vendor = None
        if self.metadata.has_key('vendor'):
            vendor = self.metadata['vendor']
        requires = []
        if self.metadata.has_key('requires'):
            requires = self.metadata['requires']
        provides = []
        if self.metadata.has_key('provides'):
            requires = self.metadata['provides']

        pkg_path = util.get_shared_package_path(name, version, release, arch, pkgname, checksum)
        if util.check_package_exists(pkg_path, checksum, hashtype):
            log.debug("Package %s Already Exists on the server skipping upload." % pkgname)
        # copy the content over to the package location
        if not self.__finalize_content(pkg_path):
            return None

        packageInfo = PackageInfo(name, version, release, epoch, \
                                  arch, description, checksum, pkgname, \
                                  requires, provides, size, buildhost, \
                                  license, group, vendor, hashtype)
        bsync = BaseSynchronizer()
        pkg = bsync.import_package(packageInfo)
        self.__package_imported(pkg['id'], pkg_path)
        return pkg

    @event(subject='package.uploaded')
    def __package_imported(self, id, path):
        # called to raise the event
        pass

    def __import_file(self):
        """
        import the files into pulp database
        """
        log.info("Importing file metadata content into pulp")
        file_path = "%s/%s/%s/%s/%s" % (util.top_file_location(), 
                                        self.metadata['pkgname'][:3], \
                                        self.metadata['pkgname'], 
                                        self.metadata['checksum'], \
                                        self.metadata['pkgname'])
        if util.check_package_exists(file_path, self.metadata['checksum'], self.metadata['hashtype']):
            log.debug("File %s Already Exists on the server skipping upload." % self.metadata['pkgname'])
        if not self.__finalize_content(file_path):
            return None
        f = FileApi()
        try:
            checksum = self.metadata['checksum']
            hashtype = self.metadata['hashtype']
        except:
            raise PulpException("metadata is missing file checksum or hashtype value")
        try:
            pkgname = self.metadata['pkgname']
        except KeyError:
            raise PulpException("metadata is missing file pkgname value")
        try:
            size = self.metadata['size']
        except KeyError:
            raise PulpException("metadata is missing file size value")
        description = None
        if self.metadata.has_key('description'):
            description = self.metadata['description']
        fobj = f.create(self.metadata['pkgname'], self.metadata['hashtype'],
                 self.metadata['checksum'], self.metadata['size'], self.metadata['description'])
        self.__file_imported(fobj['id'], file_path)
        return fobj

    @event(subject='file.uploaded')
    def __file_imported(self, id, path):
        # called to raise the event
        pass

    def __finalize_content(self, path):
        """
         Move the files to final location
        """
        log.info("Finalizing the pkg location %s" % path)
        f = File(self.upload_id)
        temp_file_path = f.getpath()
        if not os.path.exists(temp_file_path):
            log.error("Temporary package missing")
            return False
        try:
            pkg_dirname = os.path.dirname(path)
            if not os.path.exists(pkg_dirname):
                os.makedirs(pkg_dirname)
            shutil.copy(temp_file_path, path)
            log.debug("File copied from %s to %s" % (temp_file_path, path))
            f.delete()
        except Exception, e:
            log.error("Error occurred while copying the file to final location %s" % str(e))
            return False
        return True

class PackageInfo:
    def __init__(self, name, version, release, epoch, arch, description, \
                 checksum, relativepath, requires, provides, size, buildhost,\
                 license, group, vendor, checksum_type):
        self.name = name
        self.version = version
        self.release = release
        self.epoch = epoch
        self.arch = arch
        self.checksum = checksum
        self.checksum_type = checksum_type
        self.relativepath = relativepath
        self.description = description
        self.requires = requires
        self.provides = provides
        self.size = size
        self.buildhost = buildhost
        self.license = license
        self.group = group
        self.vendor = vendor

