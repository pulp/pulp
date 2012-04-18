#
# Copyright (c) 2011 Red Hat, Inc.
#
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
import gzip

import hashlib # 3rd party on RHEL 5
import logging
import os
import random
import re
import signal
import shlex
import shutil
import sre_constants
import stat
import string
import subprocess
import tempfile
import threading
import time
import commands
import rpm
import yum
import errno

from pulp.server import config, constants
from pulp.server.exceptions import PulpException
from pulp.server.tasking.exception import CancelException
from pulp.common.util import encode_unicode, decode_unicode
from grinder import GrinderUtils
from grinder import RepoFetch

log = logging.getLogger(__name__)

# We are seeing segmentation faults when multiple threads
# access yum/urlgrabber functionality concurrently.
# This lock is intended to serialize the requests
# We want to synchronize threads so that only one thread at a time is using yum's urlgrabber fetching
# See bz:695743 - Multiple concurrent calls to util.get_repo_packages() results in Segmentation fault
# Grinder is using yum functionality through ActiveObject in another process
#  this means we are only concerned with Pulp's usage of yum for synchronizing.
__yum_lock = threading.Lock()

# In memory lookup table for createrepo processes
# Responsible for 2 tasks.  1) Restrict only one createrepo per repo_dir, 2) Allow an async cancel of running createrepo
CREATE_REPO_PROCESS_LOOKUP = {}
CREATE_REPO_PROCESS_LOOKUP_LOCK = threading.Lock()

class CreateRepoError(PulpException):
    def __init__(self, output):
        self.output = output

    def __str__(self):
        return self.output

class CreateRepoAlreadyRunningError(PulpException):
    def __init__(self, repo_dir):
        self.repo_dir = repo_dir
    def __str__(self):
        return "Already running on %s" % (self.repo_dir)

class ModifyRepoError(CreateRepoError):
    pass

class RegularExpressionError(PulpException):
    pass

class Package:
    """
    Package data object used so the YumRepository and associated
    package sack(s) can be closed.
    """

    __slots__ = \
        ('relativepath',
         'checksum',
         'checksum_type',
         'name',
         'epoch',
         'version',
         'release',
         'arch',
         'description',
         'buildhost',
         'size',
         'group',
         'license',
         'vendor',
         'requires',
         'provides',)

    def __init__(self, p):
        for k in self.__slots__:
            v = getattr(p, k)
            setattr(self, k, v)


def top_repos_location():
    return "%s/%s" % (constants.LOCAL_STORAGE, "repos")

def top_gpg_location():
    return os.path.join(constants.LOCAL_STORAGE, 'published', 'gpg')

def top_package_location():
    return "%s/%s" % (constants.LOCAL_STORAGE, "packages")

def top_file_location():
    return "%s/%s" % (constants.LOCAL_STORAGE, "files")

def top_distribution_location():
    return os.path.join(constants.LOCAL_STORAGE, "distributions")

def tmp_cache_location():
    cache_dir = os.path.join(constants.LOCAL_STORAGE, "cache")
    if not os.path.exists(cache_dir):
        try:
            os.makedirs(cache_dir)
        except OSError, e:
            if e.errno != 17:
                log.critical(e)
                raise e
    return cache_dir

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
    @deprecated
    @param repomd_path: path to repomd.xml
    @return: List of available metadata types
    """
    rmd = yum.repoMDObject.RepoMD("temp_pulp", repomd_path)
    if rmd:
        return rmd.fileTypes()

def get_repomd_filetype_dump(repomd_path):
    """
    @deprecated
    @param repomd_path: path to repomd.xml
    @return: dump of metadata information
    """
    rmd = yum.repoMDObject.RepoMD("temp_pulp", repomd_path)
    ft_data = {}
    if rmd:
        for ft in rmd.fileTypes():
            ft_obj = rmd.repoData[ft]
            try:
                size = ft_obj.size
            except:
                # RHEL5 doesnt have this field
                size = None
            ft_data[ft_obj.type] = {'location'  : ft_obj.location[1],
                                    'timestamp' : ft_obj.timestamp,
                                    'size'      : size,
                                    'checksum'  : ft_obj.checksum,
                                    'dbversion' : ft_obj.dbversion}
    return ft_data


def _get_yum_repomd(path, temp_path=None):
    """
    @deprecated
    @param path: path to repo
    @param temp_path: optional parameter to specify temporary path
    @return yum.yumRepo.YumRepository object initialized for querying repodata
    """
    if not temp_path:
        temp_path = "/tmp/temp_repo-%s" % (time.time())
    r = yum.yumRepo.YumRepository(temp_path)
    try:
        r.baseurl = "file://%s" % (path.encode("ascii", "ignore"))
    except UnicodeDecodeError:
        r.baseurl = "file://%s" % (path)
    try:
        r.basecachedir = path.encode("ascii", "ignore")
    except UnicodeDecodeError:
        r.basecachedir = path
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
    Get a list of packages in the yum repo.
    A list of L{Package} data objects are returned so that the repo
    and associated resources can be closed.
    @param path: path to repo's base (not the repodatadir, this api
    expects a path/repodata underneath this path)
    @return: List of available packages (data) objects in the repo.
    """
    temp_path = tempfile.mkdtemp(prefix="temp_pulp_repo")
    # We want to limit yum operations to 1 per process.
    # When running with 5 threads calling this function we are seeing a Segmentation Fault
    # from yum/urlgrabber/libcurl.  Seen on Fedora 14.  yum 3.2.28, libcurl 7.21
    # https://bugzilla.redhat.com/show_bug.cgi?id=695743
    # Bug 695743 - Multiple concurrent calls to util.get_repo_packages() results in Segmentation fault
    __yum_lock.acquire()
    try:
        packages = []
        r = _get_yum_repomd(path, temp_path=temp_path)
        if not os.path.exists(os.path.join(path, r.repoMDFile)):
            # check if repomd.xml exists before loading package sack
            return []
        sack = r.getPackageSack()
        sack.populate(r, 'metadata', None, 0)
        for p in sack.returnPackages():
            packages.append(Package(p))
        r.close()
        return packages
    finally:
        __yum_lock.release()
        try:
            shutil.rmtree(temp_path)
        except Exception, e:
            log.warning("Unable to remove temporary directory: %s" % (temp_path))
            log.warning(e)


def get_repomd_filetype_path(path, filetype):
    """
    @deprecated
    @param path: path to repo
    @param filetype: metadata type to query, example "group", "primary", etc
    @return: Path for filetype, or None
    """
    rmd = yum.repoMDObject.RepoMD("temp_pulp", path)
    if rmd:
        try:
            data = rmd.getData(filetype)
            return data.location[1]
        except:
            return None
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

def check_package_exists(pkg_path, hashsum, hashtype="sha256", force=0):
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
        hash = checksum.values()[0]

    pkg_location = "%s/%s/%s/%s/%s/%s/%s" % (top_package_location(),
        name, version, release, arch, hash, filename)
    return pkg_location

def get_relative_path(source_path, dest_path):
    return GrinderUtils.get_relative_path(source_path, dest_path)

def create_rel_symlink(source_path, dest_path):
    rel_path = get_relative_path(source_path, dest_path)
    return create_symlinks(rel_path, dest_path)

def create_symlinks(source_path, link_path):
    link_path = encode_unicode(link_path)
    if not os.path.exists(os.path.dirname(link_path)):
        # Create published dir as well as
        # any needed dir parts if rel_path has multiple parts
        os.makedirs(os.path.dirname(link_path))
    if not os.path.exists(link_path):
        if os.path.lexists(link_path):
            # Clean up broken sym link
            os.unlink(link_path)
        log.debug("Create symlink for [%s] to [%s]" % (decode_unicode(source_path), decode_unicode(link_path)))
        os.symlink(encode_unicode(source_path), link_path)

def _create_repo(dir, groups=None, checksum_type="sha256"):
    try:
        cmd = "createrepo --database --checksum %s -g %s --update %s " % (checksum_type, groups, dir)
    except UnicodeDecodeError:
        checksum_type = decode_unicode(checksum_type)
        if groups:
            groups = decode_unicode(groups)
        dir = decode_unicode(dir)
        cmd = "createrepo --database --checksum %s -g %s --update %s " % (checksum_type, groups, dir)
    if not groups:
        cmd = "createrepo --database --checksum %s --update %s " % (checksum_type, dir)
        repodata_file = os.path.join(dir, "repodata", "repomd.xml")
        repodata_file = encode_unicode(repodata_file)
        if os.path.isfile(repodata_file):
            log.info("Checking what metadata types are available: %s" % \
                    (get_repomd_filetypes(repodata_file)))
            if "group" in get_repomd_filetypes(repodata_file):
                comps_ftype = get_repomd_filetype_path(
                    repodata_file, "group")
                filetype_path = os.path.join(dir,comps_ftype)
                # createrepo uses filename as mdtype, rename to type.<ext>
                # to avoid filename too long errors
                renamed_filetype_path = os.path.join(os.path.dirname(comps_ftype),
                                         "comps" + '.' + '.'.join(os.path.basename(comps_ftype).split('.')[1:]))
                renamed_comps_file = os.path.join(dir, renamed_filetype_path)
                os.rename(filetype_path, renamed_comps_file)
                if renamed_comps_file and os.path.isfile(renamed_comps_file):
                    cmd = "createrepo --database --checksum %s -g %s --update %s " % \
                        (checksum_type, renamed_comps_file, dir)

    # shlex now can handle unicode strings as well
    cmd = encode_unicode(cmd)
    try:
        cmd = shlex.split(cmd.encode('ascii', 'ignore'))
    except:
        cmd = shlex.split(cmd)

    log.info("started repo metadata update: %s" % (cmd))
    handle = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return handle

def create_repo(dir, groups=None, checksum_type="sha256"):
    handle = None
    # Lock the lookup and launch of a new createrepo process
    # Lock is released once createrepo is launched
    CREATE_REPO_PROCESS_LOOKUP_LOCK.acquire()
    try:
        if CREATE_REPO_PROCESS_LOOKUP.has_key(dir):
            raise CreateRepoAlreadyRunningError(dir)
        current_repo_dir = os.path.join(dir, "repodata")
        # Note: backup_repo_dir is used to store presto metadata and possibly other custom metadata types
        # they will be copied back into new 'repodata' if needed.
        backup_repo_dir = None
        current_repo_dir = encode_unicode(current_repo_dir)
        if os.path.exists(current_repo_dir):
            log.info("metadata found; taking backup.")
            backup_repo_dir = os.path.join(dir, "repodata.old")
            if os.path.exists(backup_repo_dir):
                log.debug("clean up any stale dirs")
                shutil.rmtree(backup_repo_dir)
            shutil.copytree(current_repo_dir, backup_repo_dir)
            os.system("chmod -R u+wX %s" % (backup_repo_dir))
        handle = _create_repo(dir, groups=groups, checksum_type=checksum_type)
        if not handle:
            raise CreateRepoError("Unable to execute createrepo on %s" % (dir))
        os.system("chmod -R ug+wX %s" % (dir))
        CREATE_REPO_PROCESS_LOOKUP[dir] = handle
    finally:
        CREATE_REPO_PROCESS_LOOKUP_LOCK.release()
    # Ensure we clean up CREATE_REPO_PROCESS_LOOKUP, surround all ops with try/finally
    try:
        # Block on process till complete (Note it may be async terminated)
        out_msg, err_msg = handle.communicate(None)
        if handle.returncode != 0:
            try:
                # Cleanup createrepo's temporary working directory
                cleanup_dir = os.path.join(dir, ".repodata")
                if os.path.exists(cleanup_dir):
                    shutil.rmtree(cleanup_dir)
            except Exception, e:
                log.warn(e)
                log.warn("Unable to remove temporary createrepo dir: %s" % (cleanup_dir))
            if handle.returncode == -9:
                log.warn("createrepo on %s was killed" % (dir))
                raise CancelException()
            else:
                log.error("createrepo on %s failed with returncode <%s>" % (dir, handle.returncode))
                log.error("createrepo stdout:\n%s" % (out_msg))
                log.error("createrepo stderr:\n%s" % (err_msg))
                raise CreateRepoError(err_msg)
        log.info("createrepo on %s finished" % (dir))
        if not backup_repo_dir:
            log.info("Nothing further to check; we got our fresh metadata")
            return
        #check if presto metadata exist in the backup
        repodata_file = os.path.join(backup_repo_dir, "repomd.xml")
        ftypes = get_repomd_filetypes(repodata_file)
        base_ftypes = ['primary', 'primary_db', 'filelists_db', 'filelists', 'other', 'other_db', 'group', 'group_gz']
        for ftype in ftypes:
            if ftype in base_ftypes:
                # no need to process these again
                continue
            filetype_path = os.path.join(backup_repo_dir, os.path.basename(get_repomd_filetype_path(repodata_file, ftype)))
            # modifyrepo uses filename as mdtype, rename to type.<ext>
            renamed_filetype_path = os.path.join(os.path.dirname(filetype_path), \
                                         ftype + '.' + '.'.join(os.path.basename(filetype_path).split('.')[1:]))
            os.rename(filetype_path,  renamed_filetype_path)
            if renamed_filetype_path.endswith('.gz'):
                # if file is gzipped, decompress before passing to modifyrepo
                data = gzip.open(renamed_filetype_path).read().decode("utf-8", "replace")
                renamed_filetype_path = '.'.join(renamed_filetype_path.split('.')[:-1])
                open(renamed_filetype_path, 'w').write(data.encode("UTF-8"))
            if os.path.isfile(renamed_filetype_path):
                log.info("Modifying repo for %s metadata" % ftype)
                modify_repo(current_repo_dir, renamed_filetype_path)
    finally:
        if backup_repo_dir:
            shutil.rmtree(backup_repo_dir)
        CREATE_REPO_PROCESS_LOOKUP_LOCK.acquire()
        try:
            del CREATE_REPO_PROCESS_LOOKUP[dir]
        finally:
            CREATE_REPO_PROCESS_LOOKUP_LOCK.release()

def cancel_createrepo(repo_dir):
    """
    Method will lookup a createrepo process associated to 'repo_dir'
    If a createrepo process is running we will send a SIGKILL to it and return True
    Else we return False to denote no process was found
    """
    CREATE_REPO_PROCESS_LOOKUP_LOCK.acquire()
    try:
        if CREATE_REPO_PROCESS_LOOKUP.has_key(repo_dir):
            handle = CREATE_REPO_PROCESS_LOOKUP[repo_dir]
            try:
                os.kill(handle.pid, signal.SIGKILL)
            except Exception, e:
                log.info(e)
                return False
            return True
        else:
            return False
    finally:
        CREATE_REPO_PROCESS_LOOKUP_LOCK.release()

def modify_repo(repodata_dir, new_file, remove=False):
    """
     run modifyrepo to add a new file to repodata directory
     @param repodata_dir: repodata directory path
     @type repodata_dir: string
     @param new_file: new file type to add or remove
     @type new_file: string
    """
    if remove:
        cmd = "modifyrepo --remove %s %s" % (new_file, repodata_dir)
    else:
        cmd = "modifyrepo %s %s" % (new_file, repodata_dir)
    cmd = encode_unicode(cmd)
    status, out = commands.getstatusoutput(cmd)
    if status != 0:
        log.error("modifyrepo on %s failed" % repodata_dir)
        raise ModifyRepoError(out)
    log.info("modifyrepo with %s on %s finished" % (new_file, repodata_dir))
    return status, out

def delete_empty_directories(dirname):
    if not os.path.isdir(dirname):
        log.error("%s is not a directory" % dirname)
        return
    empty = True
    try:
        top_level_dirs = [top_repos_location(), top_package_location(), top_file_location()]
        while empty:
            if dirname not in top_level_dirs and os.listdir(dirname) == []:
                os.rmdir(dirname)
                log.debug("Successfully cleaned up %s" % dirname)
                dirname = os.path.dirname(dirname)
                log.debug("Processing %s" % dirname)
            else:
                log.debug("Not an empty dir %s" % dirname)
                empty = False
    except Exception,e:
        # we can hit multiple conditions during remove
        log.error("Unable to delete empty directories due to the following error: %s" % e)

def translate_to_utf8(data, encoding=None):
    """
    This method will attempt to encode all strings in passed data to utf-8
    @param data: data document to pass into Mongo for storage
    @type data: BSON document
    @param encoding: if utf-8 encoding fails, will translated strings to unicode using this encoding.  Default is 'iso-8859-1'
    @type encoding: str
    @return: BSON document
    """
    if not encoding:
        encoding = 'iso-8859-1'
    for key in data.keys():
        try:
            value = data[key]
            if isinstance(value, basestring):
                # Attempt to encode to utf-8
                attempt = value.encode('utf-8')
        except Exception, e:
            translated_value = unicode(data[key], encoding)
            data[key] = translated_value
    return data

def compile_regular_expression(reg_exp):
    """
    This method will handle a sre_constants.error resulting from an invalid
    value for reg_exp.
    @param reg_exp: regular expression to validate
    @type reg_exp: str
    @return: the compiled regular expression
    @rtype: regular expression object
    @raise: L{RegularExpressionError} if reg_exp fails to validate.
    """
    try:
        return re.compile(reg_exp)
    except sre_constants.error, e:
        raise RegularExpressionError(
            "The regular expression '%s' is not valid: %s"
            % (reg_exp, str(e)))

def makedirs(path, mode=0777):
    """
    Make directory.
    Creates leaf directory and intermediate directories as needed.
    Mitigates: http://bugs.python.org/issue1675
    @param path: A directory path.
    @type path: str
    """
    leaf = 1
    if path.startswith('/'):
        root = path[0]
        path = path[1:]
    else:
        root = ''
    part = [p for p in path.split('/') if p]
    while leaf <= len(part):
        subpath = root+os.path.join(*part[0:leaf])
        leaf += 1
        try:
            os.mkdir(subpath, mode)
        except OSError, e:
            if e.errno == errno.EEXIST and os.path.isdir(subpath):
                pass # already exists
            else:
                raise

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


class subdict(dict):
    """
    A dictionary that posseses a subset of the keys in some other dictioary.
    """

    def __init__(self, d, keys=()):
        """
        @param d: mapping type to be a subdict of
        @param keys: list of keys to copy from d
        """
        n = dict((k, v) for k, v in d.items() if k in keys)
        super(subdict, self).__init__(n)
