#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © 2010 Red Hat, Inc.
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

import base64
import commands
import hashlib
import logging
import os
import tempfile

from pulp.server import util
from pulp.server.api.repo_sync import BaseSynchronizer
from pulp.server import config
from pulp.server.pexceptions import PulpException

log = logging.getLogger(__name__)

PACKAGE_LOCATION = util.top_package_location()

class PackageAlreadyExists(Exception):
    pass

class PackageUpload:
    def __init__(self, pkginfo, payload):
        self.pkginfo = pkginfo
        self.stream = payload
        self.pkgname = pkginfo['pkgname']
        
    def upload(self):
        (name, version, release, epoch, arch) = self.pkginfo['nvrea']
        pkg_path = "%s/%s/%s/%s/%s/%s/%s" % (PACKAGE_LOCATION, self.pkginfo['checksum'][:3], name, version, release, arch, self.pkgname)

        imp_pkg = None
        try:
            if util.check_package_exists(pkg_path, self.pkginfo['checksum'], self.pkginfo['hashtype']):
                log.error("Package %s Already Exists on the server skipping upload." % self.pkgname)
                raise PackageAlreadyExists("Package %s Already Exists on the server with checksum [%s]; skipping upload." % (self.pkgname, self.pkginfo['checksum']))
            else:
                store_package(self.stream, pkg_path, self.pkginfo['size'], self.pkginfo['checksum'], self.pkginfo['hashtype'])
            imp_pkg = self.import_package(pkg_path)
        except IOError, e:
            log.error("Error writing file to filesystem %s " % e)
            raise
        except Exception, e:
            log.error("Unexpected Error %s " % e)
            raise
        return imp_pkg   
    
    def import_package(self, pkg_path):
        file_name = os.path.basename(pkg_path)
        (name, version, release, epoch, arch) = self.pkginfo['nvrea']
        packageInfo = PackageInfo(name, version, release, epoch, arch,\
                                  self.pkginfo['description'], 
                                  self.pkginfo['checksum'], self.pkgname,
                                  self.pkginfo['requires'], self.pkginfo['provides'])
        bsync = BaseSynchronizer()
        pkg = bsync.import_package(packageInfo, repo=None)
        return pkg
    
class PackageInfo:
    def __init__(self, name, version, release, epoch, arch, \
                 description, checksum, relativepath, 
                 requires, provides):
        self.name = name
        self.version = version
        self.release = release
        self.epoch = epoch
        self.arch = arch
        self.checksum =  checksum
        self.relativepath = relativepath
        self.description = description
        self.requires = requires
        self.provides = provides

def store_package(pkgstream, pkg_path, size, checksum, hashtype, force=None):
    """
    Write the package stream to a file under repo location
    """
    stream = base64.b64decode(pkgstream)
    rel_dir = os.path.dirname(pkg_path)

    if not os.path.exists(rel_dir):
        try:
            os.makedirs(rel_dir)
        except IOError, e:
            log.error("Unable to create repo directory %s" % rel_dir)
    tmpstream = tempfile.TemporaryFile()
    tmpstream.write(stream)
    chunk_size = 65536
    total_bytes = 0
    hashsum = hashlib.new(hashtype)
    file = open(pkg_path, "wb")
    tmpstream.seek(0, 0)
    while 1:
        buffer = tmpstream.read(chunk_size)
        if not buffer:
            break
        file.write(buffer)
        hashsum.update(buffer)
        total_bytes += len(buffer)
    file.close()
    savedChecksum = hashsum.hexdigest()
    if total_bytes != int(size):
        os.remove(pkg_path)
        raise UploadError(" %s size mismatch, read: %s bytes, was expecting %s bytes" % (os.path.basename(pkg_path), str(total_bytes), str(size)))
    elif savedChecksum != checksum:
        os.remove(pkg_path)
        raise UploadError("%s md5sum mismatch, read md5sum of: %s expected md5sum of %s" % (os.path.basename(pkg_path), savedChecksum, checksum))


    
class UploadError(PulpException):
    pass

class PackageExistsError(PulpException):
    pass

class CreateRepoError(PulpException):
    def __init__(self, output):
        self.output = output

    def __str__(self):
        return self.output

class ModifyRepoError(CreateRepoError):
    pass


