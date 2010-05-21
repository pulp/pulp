#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: Mike McCune
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
import rpm
import os
import logging
import string
import random
import fnmatch

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


def random_string():
    # The characters to make up the random password
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for x in range(random.randint(8, 16)))     

def chunks(l, n):
    """
    Split an array into n# of chunks.  Taken from : http://tinyurl.com/y8v5q2j
    """
    return [l[i:i+n] for i in range(0, len(l), n)]

## {{{ http://code.activestate.com/recipes/499305/ (r3)
def locate(pattern, root=os.curdir):
    '''Locate all files matching supplied filename pattern in and below
    supplied root directory.'''
    for path, dirs, files in os.walk(os.path.abspath(root)):
        for filename in fnmatch.filter(files, pattern):
            yield os.path.join(path, filename)
## end of http://code.activestate.com/recipes/499305/ }}}

def find_dir_with_file(filename, root=os.curdir):
    """
    Find the first matching dir with file pattern starting in root passed in
    """
    locations = locate(filename, root)
    fullpath = ''
    for loc in locations:
        fullpath = loc
    return fullpath.replace(filename, '')
