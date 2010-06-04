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

__author__ = 'Pradeep Kilambi <pkilambi@redhat.com>'

import os
import util
import base64
import tempfile
import hashlib
from pulp.api.package import PackageApi
from pulp.api.package_version import PackageVersionApi
from repo_sync import BaseSynchronizer

class PackageUpload:
    def __init__(self, config, repo, pkginfo, payload):
        self.config = config
        self.repo = repo
        self.pkginfo = pkginfo
        self.stream = payload
        self.pkgname = pkginfo['pkgname']
        self.repo_dir = "%s/%s/" % (self.config.get('paths', 'local_storage'), repo['id'])

    def upload(self):
        pkg_path = self.repo_dir + "/" + self.pkgname
        hashtype = self.pkginfo['hashtype']
        if check_package_exists(pkg_path, self.pkginfo['hashtype'], self.pkginfo['checksum']):
            raise PackageExistsError(pkg_path)
        try:
            store_package(self.stream, pkg_path, self.pkginfo['size'], self.pkginfo['checksum'], self.pkginfo['hashtype'])
            self.bindPackageToRepo(pkg_path, self.repo)
        except IOError, ie:
            raise UploadError("Error writing to the file %s" % self.pkgname)
        except Exception, e:
            raise UploadError("Upload Failed due to unexpected Error ")

    def bindPackageToRepo(self, pkg_path, repo):
        bsync = BaseSynchronizer(self.config)
        bsync.import_package(pkg_path, repo)

def check_package_exists(pkg_path, hashtype, hashsum, force=0):
    if not os.path.exists(pkg_path):
        return False
    # File exists, same hash?
    curr_hash = util.getFileChecksum(hashtype, pkg_path)
    if curr_hash == hashsum and not force:
        return True
    if force:
        return False
    return False

def store_package(pkgstream, pkg_path, size, checksum, hashtype, force=None):
    """
    Write the package stream to a file under repo location
    """
    stream = base64.b64decode(pkgstream)
    dir = os.path.dirname(pkg_path)
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

class UploadError(Exception):
    pass

class PackageExistsError(Exception):
    pass

