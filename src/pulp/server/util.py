#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
#
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
#

import hashlib # 3rd party on RHEL 5
import logging
import os
import random
import string
import time

import rpm
import yum

from pulp.server import config
from pulp.server.pexceptions import PulpException


log = logging.getLogger(__name__)

def top_repos_location():
    return "%s/%s" % (config.config.get('paths', 'local_storage'), "repos")

def top_gpg_location():
    return "%s/%s" % (config.config.get('paths', 'local_storage'), "gpg")

def top_package_location():
    return "%s/%s" % (config.config.get('paths', 'local_storage'), "packages")

def relative_repo_path(path):
    """
    Convert the specified I{path} to a relative path
    within a repo storage directory.
    @type path: An absolute path to a repo file.
    @type path: str
    @return: The relative path.
    @rtype: str
    """
    top = top_repos_location()
    if path.startswith(top):
        path = path[len(top):]
    while path.startswith('/'):
        path = path[1:]
    return path 

def get_rpm_information(rpm_path):
    """
    Get metadata about an RPM.

    @param rpm_path: Full path to the RPM to inspect
    """
    log.debug("rpm_path: %s" % rpm_path)
    ts = rpm.ts()
    ts.setVSFlags(rpm._RPMVSF_NOSIGNATURES) 
    file_descriptor_number = os.open(rpm_path, os.O_RDONLY)
    rpm_info = ts.hdrFromFdno(file_descriptor_number);
    os.close(file_descriptor_number)
    return rpm_info


def random_string():
    '''
    Generates a random string suitable for using as a password.
    '''
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for x in range(random.randint(8, 16)))     


def chunks(l, n):
    """
    Split an array into n# of chunks.  Taken from : http://tinyurl.com/y8v5q2j
    """
    return [l[i:i+n] for i in range(0, len(l), n)]


def get_file_checksum(hashtype="sha", filename=None, fd=None, file=None, buffer_size=None):
    """
    Compute a file's checksum.
    """
    if hashtype in ['sha', 'SHA']:
        hashtype = 'sha1'

    if buffer_size is None:
        buffer_size = 65536

    if filename is None and fd is None and file is None:
        raise Exception("no file specified")
    if file:
        f = file
    elif fd is not None:
        f = os.fdopen(os.dup(fd), "r")
    else:
        f = open(filename, "r")
    # Rewind it
    f.seek(0, 0)
    m = hashlib.new(hashtype)
    while 1:
        buffer = f.read(buffer_size)
        if not buffer:
            break
        m.update(buffer)

    # cleanup time
    if file is not None:
        file.seek(0, 0)
    else:
        f.close()
    return m.hexdigest()


def get_string_checksum(hashtype, data):
    """
    Return checksum of a string
    @param hashtype: hashtype, example "sha256"
    @param data: string to get checksum
    @return: checksum
    """
    m = hashlib.new(hashtype)
    m.update(data)
    return m.hexdigest()


def get_file_timestamp(filename):
    """
    Returns a timestamp
    @param filename: filename path to file
    @return: filename's timestamp
    """
    return int(os.stat(filename).st_mtime)


def get_repomd_filetypes(repomd_path):
    """
    @param repomd_path: path to repomd.xml
    @return: List of available metadata types
    """
    rmd = yum.repoMDObject.RepoMD("temp_pulp", repomd_path)
    if rmd:
        return rmd.fileTypes()


def _get_yum_repomd(path):
    """
    @param path: path to repo
    @return yum.yumRepo.YumRepository object initialized for querying repodata
    """
    r = yum.yumRepo.YumRepository("/tmp/temp_repo-%s" % (time.time()))
    r.baseurl = "file://%s" % (path.encode("ascii", "ignore"))
    r.basecachedir = path.encode("ascii", "ignore")
    r.baseurlSetup()
    return r


def get_repo_package(repo_path, package_filename):
    """
    @param repo_path: The file system path to the repository you wish to fetch 
    the package metadata from
    @param package_filename: the filename of the package you want the metadata for
    """
    repoPackages = get_repo_packages(repo_path)
    found = None
    for p in repoPackages:
        if (p.relativepath == package_filename):
            found = p 
    if found is None:
        raise PulpException("No package with file name: %s found in repository: %s" 
                            % (package_filename, repo_path))
    return found


def get_repo_packages(path):
    """
    @param path: path to repo's base (not the repodatadir, this api 
    expects a path/repodata underneath this path)
    @return: List of available packages objects in the repo.  
    """
    r = _get_yum_repomd(path)
    if not r:
        return []
    r.sack.populate(r, 'metadata', None, 0)
    return r.getPackageSack().returnPackages()

def get_repomd_filetype_path(path, filetype):
    """
    @param path: path to repo
    @param filetype: metadata type to query, example "group", "primary", etc
    @return: Path for filetype, or None
    """
    rmd = yum.repoMDObject.RepoMD("temp_pulp", path)
    if rmd:
        data = rmd.getData(filetype)
        return data.location[1]
    return None

def listdir(directory):
    """
    List the files in the given directory and subdirectory.
    @type directory: str
    @param directory: name of the directory
    @return: list of 'directory/file'
    """
    directory = os.path.abspath(os.path.normpath(directory))
    if not os.access(directory, os.R_OK | os.X_OK):
        raise Exception("Cannot read from directory %s" % directory)
    if not os.path.isdir(directory):
        raise Exception("%s not a directory" % directory)
    filelist = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            filelist.append("%s/%s" % (root, file))
    return filelist

def compare_packages(pkgA, pkgB):
    """
     return 1: pkgA is newer than pkgB
     return 0: pkgA equals pkgB
     return -1: pkgB is newer than pkgA
    """
    def build_evr(pkg):
        evr = [pkg["epoch"], pkg["version"], pkg["release"]]
        evr = map(str, evr)
        if evr[0] == "":
            evr[0] = None
        return evr

    evrA, evrB = (build_evr(pkgA), build_evr(pkgB))
    return rpm.labelCompare(evrA, evrB)

def check_package_exists(pkg_path, hashsum, hashtype="sha", force=0):
    if not os.path.exists(pkg_path):
        return False
    # File exists, same hash?
    curr_hash = get_file_checksum(hashtype, pkg_path)
    if curr_hash == hashsum and not force:
        return True
    if force:
        return False
    return False

def get_repo_package_path(repo_relpath, pkg_filename):
    """
    Return the filepath to the package stored in the repos directory.
    This is most likely a symbolic link only, pointing to the shared package
    location.
    @param repo_relpath:  repository relative path
    @param pkg_filename: filename of the package
    """
    f = os.path.join(top_repos_location(), repo_relpath)
    return os.path.join(f, pkg_filename)

def get_shared_package_path(name, version, release, arch, filename, checksum):
    """
    Return the location in the package store for this particular package
    @param name: name string
    @param version: version string
    @param release: release string
    @param arch: arch string
    @param filename: filename string
    @param checksum: checksum can be string or dictionary
    """
    if isinstance(checksum, basestring):
        hash = checksum
    else:
        if checksum.has_key("sha256"):
            hash = checksum["sha256"]
        else:
            #unknown checksum type, grab first checksum type
            hash = checksum[hash.keys()[0]]

    pkg_location = "%s/%s/%s/%s/%s/%s/%s" % (top_package_location(),
        hash[:3], name, version, release, arch, filename)
    return pkg_location

class Singleton(type):
    """
    Singleton metaclass. To make a class instance a singleton, use this class
    as your class's metaclass as follows:
    
    class MyClass(object):
        __metaclass__ = Singleton
    
    Singletons are created by passing the exact same arguments to the
    constructor. For example:
    
    class T():
        __metaclass__ = Singleton
        
        def __init__(self, value=None):
            self.value = value
        
    t1 = T()
    t2 = T()
    t1 is t2
    True
    t3 = T(5)
    t4 = T(5)
    t3 is t4
    True
    t1 is t3
    False
    """
    def __init__(self, name, bases, ns):
        super(Singleton, self).__init__(name, bases, ns)
        self.instances = {}
        
    def __call__(self, *args, **kwargs):
        key = (tuple(args), tuple(sorted(kwargs.items())))
        return self.instances.setdefault(key, super(Singleton, self).__call__(*args, **kwargs))
