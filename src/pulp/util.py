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

log = logging.getLogger("pulp.util")

def getRPMInformation(rpmPath):
    """
    Get metadata about an RPM from the path passed in
    """
    log.debug("rpmPath: %s" % rpmPath)
    ts = rpm.ts();
    ts.setVSFlags(rpm._RPMVSF_NOSIGNATURES) 
    file_descriptor_number = os.open(rpmPath, os.O_RDONLY)
    rpmInfo = ts.hdrFromFdno(file_descriptor_number);
    os.close(file_descriptor_number)
    return rpmInfo

def randomString():
    # The characters to make up the random password
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for x in range(random.randint(8, 16)))     

def chunks(l, n):
    """
    Split an array into n# of chunks.  Taken from : http://tinyurl.com/y8v5q2j
    """
    return [l[i:i+n] for i in range(0, len(l), n)]

def loadConfig(filename, config=ConfigParser.SafeConfigParser()):
    config.read(filename)
    return config


def getFileChecksum(hashtype, filename=None, fd=None, file=None, buffer_size=None):
    """ Compute a file's checksum
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

