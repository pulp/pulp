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
import commands
import hashlib
import shutil
import traceback
import urlparse
import yum
import time
import os
import logging
import gettext
import rpmUtils
from M2Crypto import X509
_ = gettext.gettext

LOG_PREFIX_NAME="pulp.plugins"
def getLogger(name):
    log_name = LOG_PREFIX_NAME + "." + name 
    return logging.getLogger(log_name)
_LOG = getLogger(__name__)

def get_repomd_filetypes(repomd_path):
    """
    @param repomd_path: path to repomd.xml
    @return: List of available metadata types
    """
    rmd = yum.repoMDObject.RepoMD("temp_pulp", repomd_path)
    if rmd:
        return rmd.fileTypes()

def get_repomd_filetype_dump(repomd_path):
    """
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

def get_repomd_filetype_path(path, filetype):
    """
    @param path: path to repomd.xml
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

def is_valid_checksum_type(checksum_type):
    """
    @param checksum_type: checksum type to validate
    @type checksum_type str
    @return: True if valid, else False
    @rtype bool
    """
    VALID_TYPES = ['sha256', 'sha', 'sha1', 'md5', 'sha512']
    if checksum_type not in VALID_TYPES:
        return False
    return True

def validate_feed(feed_url):
    """
    @param feed_url: feed url to validate
    @type feed_url str
    @return: True if valid, else False
    @rtype bool
    """
    proto, netloc, path, params, query, frag = urlparse.urlparse(feed_url)
    if proto not in ['http', 'https', 'ftp', 'file']:
        return False
    return True

def get_file_checksum(filename=None, fd=None, file=None, buffer_size=None, hashtype="sha256"):
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

def validate_cert(cert_pem):
    """
    @param cert_pem: certificate pem to verify
    @type cert_pem str
    @return: True if valid, else False
    @rtype bool
    """
    try:
        cert = X509.load_cert_string(cert_pem)
    except X509.X509Error:
        return False
    return True

def verify_exists(file_path, checksum=None, checksum_type="sha256", size=None, verify_options={}):
    """
    Verify if the rpm existence; checks include
     - exists on the filesystem
     - size match
     - checksums match

    @param file_path rpm file path on filesystem
    @type missing_rpms str

    @param checksum checksum value of the rpm
    @type checksum str

    @param checksum_type type used to calculate checksum
    @type checksum_type str

    @param size size of the file
    @type size int

    @param verify_options dict of checksum of size verify options
    @type size dict

    @return True if all checks pass; else False
    @rtype bool
    """
    _LOG.debug("Verify path [%s] exists" % file_path)
    if not os.path.exists(file_path):
        # file path not found
        return False
    verify_size = verify_options.get("size") or False
    # compute the size
    if verify_size and size is not None:
        f_stat = os.stat(file_path)
        if int(size) and f_stat.st_size != int(size):
            cleanup_file(file_path)
            return False
    verify_checksum = verify_options.get("checksum") or False
    # compute checksum
    if verify_checksum and checksum is not None:
        computed_checksum = get_file_checksum(filename=file_path, hashtype=checksum_type)
        if computed_checksum != checksum:
            cleanup_file(file_path)
            return False
    return True

def cleanup_file(file_path):
    try:
        os.remove(file_path)
    except (OSError, IOError), e:
        _LOG.info("Error [%s] trying to clean up file path [%s]" % (e, file_path))

def create_symlink(source_path, symlink_path):
    """
    @param source_path source path
    @type source_path str

    @param symlink_path path of where we want the symlink to reside
    @type symlink_path str

    @return True on success, False on error
    @rtype bool
    """
    if symlink_path.endswith("/"):
        symlink_path = symlink_path[:-1]
    if os.path.lexists(symlink_path):
        if not os.path.islink(symlink_path):
            _LOG.error("%s is not a symbolic link as expected." % (symlink_path))
            return False
        existing_link_target = os.readlink(symlink_path)
        if existing_link_target == source_path:
            return True
        _LOG.warning("Removing <%s> since it was pointing to <%s> and not <%s>"\
        % (symlink_path, existing_link_target, source_path))
        os.unlink(symlink_path)
        # Account for when the relativepath consists of subdirectories
    if not create_dirs(os.path.dirname(symlink_path)):
        return False
    _LOG.debug("creating symlink %s pointing to %s" % (symlink_path, source_path))
    os.symlink(source_path, symlink_path)
    return True

def create_copy(source_path, target_path):
    """
    @param source_path source path
    @type source_path str

    @param target_path path of where we want the copy the file
    @type target_path str

    @return True on success, False on error
    @rtype bool
    """
    if not os.path.isdir(os.path.dirname(target_path)):
        os.makedirs(os.path.dirname(target_path))
    if os.path.isfile(source_path):
        _LOG.debug("Copying file from source %s to target path %s" % (source_path, target_path))
        shutil.copy(source_path, target_path)
        print "copying %s %s" % (source_path, target_path)
        return True
    if os.path.isdir(source_path):
        _LOG.debug("Copying directory from source %s to target path %s" % (source_path, target_path))
        shutil.copytree(source_path, target_path)
        return True
    return False

def create_dirs(target):
    """
    @param target path
    @type target str

    @return True - success, False - error
    @rtype bool
    """
    try:
        os.makedirs(target)
    except OSError, e:
        # Another thread may have created the dir since we checked,
        # if that's the case we'll see errno=17, so ignore that exception
        if e.errno != 17:
            _LOG.error("Unable to create directories for: %s" % (target))
            tb_info = traceback.format_exc()
            _LOG.error("%s" % (tb_info))
            return False
    return True

def get_relpath_from_unit(unit):
    """
    @param unit
    @type AssociatedUnit

    @return relative path
    @rtype str
    """
    filename = ""
    if unit.metadata.has_key("relativepath"):
        relpath = unit.metadata["relativepath"]
    elif unit.metadata.has_key("filename"):
        relpath = unit.metadata["filename"]
    elif unit.unit_key.has_key("fileName"):
        relpath = unit.unit_key["fileName"]
    else:
        relpath = os.path.basename(unit.storage_path)
    return relpath

def remove_symlink(publish_dir, link_path):
    """
    @param publish_dir: full http/https publish directory for all repos
    @type publish_dir: str

    @param link_path: full publish path for this specific repo
    @type link_path: str

    Intent is to remove all the specific link and all unique sub directories used to create it
    """
    # Remove the symlink from filesystem
    link_path = link_path.rstrip('/')
    os.unlink(link_path)
    # Adjust the link_path and removal the symlink from it
    link_path = os.path.split(link_path)[0]
    common_pieces = [x for x in publish_dir.split('/') if x] # remove empty pieces
    link_pieces = [x for x in link_path.split('/') if x]
    # Determine what are the non shared pieces from this link
    potential_to_remove = link_pieces[len(common_pieces):]
    num_pieces = len(potential_to_remove)
    # Start removing the end pieces of the path and work our way back
    # If we encounter a non-empty directory stop removal and return
    for index in range(num_pieces, 0, -1):
        path_to_remove = os.path.join(publish_dir, *potential_to_remove[:index])  #Start with all then work back
        if len(os.listdir(path_to_remove)):
            # Directory is not empty so stop removal quit
            break
        os.rmdir(path_to_remove)

def is_rpm_newer(a, b):
    """
    @var a: represents rpm metadata
    @type a: dict with keywords: name, arch, epoch, version, release

    @var b: represents rpm metadata
    @type b: dict with keywords: name, arch, epoch, version, release
    
    @return true if RPM is a newer, false if it's not
    @rtype: bool
    """
    if a["name"] != b["name"]:
        return False
    if a["arch"] != b["arch"]:
        return False
    value = rpmUtils.miscutils.compareEVR(
            (a["epoch"], a["version"], a["release"]), 
            (b["epoch"], b["version"], b["release"]))
    if value > 0:
        return True
    return False

