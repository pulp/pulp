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


import sys
import logging

from yum.update_md import UpdateMetadata

from pulp.db.model import Errata

log = logging.getLogger(__name__)


def get_update_notices(path_to_updateinfo):
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

def get_errata(path_to_updateinfo):
    """
    @param path_to_updateinfo: path to updateinfo metadata xml file

    Returns a list of pulp.model.Errata objects
    Parses updateinfo xml file and converts yum.update_md.UpdateNotice
    objects to pulp.model.Errata objects
    """
    errata = []
    uinfos = get_update_notices(path_to_updateinfo)
    for u in uinfos:
        e = _translate_updatenotice_to_erratum(u)
        errata.append(e)
    return errata

def _translate_updatenotice_to_erratum(unotice):
    id = unotice['update_id']
    title = unotice['title']
    description = unotice['description']
    version = unotice['version']
    release = unotice['release']
    type = unotice['type']
    status = unotice['status']
    updated = unotice['updated']
    issued = unotice['issued']
    pushcount = unotice['pushcount']
    from_str = unotice['from']
    reboot_suggested = unotice['reboot_suggested']
    references = unotice['references']
    pkglist = unotice['pkglist']
    erratum = Errata(id, title, description, version, release, type,
        status, updated, issued, pushcount, from_str, reboot_suggested,
        references, pkglist)
    return erratum

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print "Usage: %s <PATH_TO/updateinfo.xml>"
        sys.exit(1)
    updateinfo_path = sys.argv[1]
    notices = get_update_notices(updateinfo_path)
    if len(notices) < 1:
        print "Error parsing %s" % (updateinfo_path)
        print "Ensure you are specifying the path to updateinfo.xml"
        sys.exit(1)
    print "UpdateInfo has been parsed for %s notices." % (len(notices))
    example = notices[0]
    for key in example.keys():
        print "%s: %s" % (key, example[key])
    print "Available keys are: %s" % (example.keys())
