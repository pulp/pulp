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

import ConfigParser
import rpm
import os
import logging
import string
import random
import fnmatch
import sys
try:
    import hashlib
except:
    print "Please install python-hashlib"
    sys.exit(1)
import base64
from iniparse import INIConfig as Base

log = logging.getLogger(__name__)

def get_rpm_information(rpm_path):
    """
    Get metadata about an RPM.

    @param rpm_path: Full path to the RPM to inspect
    """
    log.debug("rpm_path: %s" % rpm_path)
    ts = rpm.ts();
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

def load_config(filename, config=ConfigParser.SafeConfigParser()):
    config.read(filename)
    return config

def get_file_checksum(hashtype, filename=None, fd=None, file=None, buffer_size=None):
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
    @param: filename path to file
    @return filename's timestamp
    """
    return int(os.stat(filename).st_mtime)

def listdir(directory):
    directory = os.path.abspath(os.path.normpath(directory))
    if not os.access(directory, os.R_OK | os.X_OK):
        raise Exception("Cannot read from directory %s" % directory)
    if not os.path.isdir(directory):
        raise Exception("%s not a directory" % directory)
    # Build the package list
    packagesList = []
    for f in os.listdir(directory):
        packagesList.append("%s/%s" % (directory, f))
    return packagesList

class Config(Base):
    """
    The pulp configuration.
    @cvar PATH: The absolute path to the config file.
    @type PATH: str
    """

    PATH = '/etc/pulp/pulp.ini'

    def __init__(self, path=PATH):
        """
        Open the configuration.
        """
        fp = open(path)
        try:
            Base.__init__(self, fp)
        finally:
            fp.close()
