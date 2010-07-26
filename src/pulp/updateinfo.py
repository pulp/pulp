#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
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


# Python
import sys
import logging

# 3rd Party
from yum.update_md import UpdateMetadata

import pulp

log = logging.getLogger(__name__)

def getUpdateInfo(path_to_updateinfo):
    """
    path_to_updateinfo:  path to updateinfo.xml

    Returns a list of dictionaries
    Dictionary is based on keys from yum.update_md.UpdateNotice
    """
    um = UpdateMetadata()
    um.add(path_to_updateinfo)
    notices = []
    for info in um.get_notices():
        notices.append(info.get_metadata())
    return notices


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print "Usage: %s <PATH_TO/updateinfo.xml>"
        sys.exit(1)
    updateinfo_path = sys.argv[1]
    notices = getUpdateInfo(updateinfo_path)
    if len(notices) < 1:
        print "Error parsing %s" % (updateinfo_path)
        print "Ensure you are specifying the path to updateinfo.xml"
        sys.exit(1)
    print "UpdateInfo has been parsed for %s notices." % (len(notices))
    example = notices[0]
    print "Available keys are: %s" % (example.keys())
    for key in example.keys():
        print "%s: %s" % (key, example[key])
