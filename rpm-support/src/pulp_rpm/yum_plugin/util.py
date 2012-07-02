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
import hashlib
import urlparse
import yum
import time
import os
import logging
import gettext
from M2Crypto import X509
_LOG = logging.getLogger(__name__)
_ = gettext.gettext
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
