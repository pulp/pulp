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
import hashlib
import logging
import os
import tempfile
import commands

from api.repo_sync import BaseSynchronizer
from pexceptions import PulpException
import util

log = logging.getLogger(__name__)

class PackageUpload:
    def __init__(self, config, repo, pkginfo, payload):
        self.config = config
        self.pkginfo = pkginfo
        self.stream = payload
        self.pkgname = pkginfo['pkgname']
        self.repo_dir = "%s/%s/" % (self.config.get('paths', 'local_storage'), repo['id'])
        self.repo = repo

    def upload(self):
        pkg_path = self.repo_dir + "/" + self.pkgname
        hashtype = self.pkginfo['hashtype']
        if check_package_exists(pkg_path, self.pkginfo['hashtype'], self.pkginfo['checksum']):
            log.error("Package %s Already Exists on the server skipping upload." % self.pkgname)
            raise PackageExistsError(pkg_path)
        try:
            store_package(self.stream, pkg_path, self.pkginfo['size'], self.pkginfo['checksum'], self.pkginfo['hashtype'])
            # update/create the repodata for the repo
            create_repo(self.repo_dir)
            imp_pkg = self.bindPackageToRepo(self.repo_dir, pkg_path, self.repo)
        except IOError, ie:
            log.error("Error writing file to filesystem %s " % ie)
            raise UploadError("Error writing to the file %s" % self.pkgname)
        except CreateRepoError, cre:
            log.error("Error running createrepo on repo %s. Error: %s" % (self.repo['id'], ie))
        except Exception, e:
            log.error("UnExpected Error %s " % e)
            raise UploadError("Upload Failed due to unexpected Error ")
        return imp_pkg, self.repo
    
    def bindPackageToRepo(self, repo_path, pkg_path, repo):
        log.debug("Binding package [%s] to repo [%s]" % (pkg_path, repo))
        bsync = BaseSynchronizer(self.config)
        file_name = os.path.basename(pkg_path)
        packageInfo = util.get_repo_package(repo_path, file_name)
        pkg = bsync.import_package(packageInfo, repo)
        return pkg

def check_package_exists(pkg_path, hashtype, hashsum, force=0):
    if not os.path.exists(pkg_path):
        return False
    # File exists, same hash?
    curr_hash = util.get_file_checksum(hashtype, pkg_path)
    if curr_hash == hashsum and not force:
        return True
    if force:
        return False
    return False

def create_repo(dir, groups=None):
    cmd = "createrepo --update %s" % (dir)
    if groups:
        cmd = "createrepo -g %s --update %s" % (groups, dir)
    status, out = commands.getstatusoutput(cmd)
    
    if status != 0:
        log.error("createrepo on %s failed" % dir)
        raise CreateRepoError(out)
    log.info("createrepo on %s finished" % dir)
    return status, out

def modify_repo(dir, new_file):
    cmd = "modifyrepo %s %s" % (new_file, dir)
    status, out = commands.getstatusoutput(cmd)
    if status != 0:
        log.error("modifyrepo on %s failed" % dir)
        raise ModifyRepoError(out)
    log.info("modifyrepo with %s on %s finished" % (new_file, dir))
    return status, out



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


