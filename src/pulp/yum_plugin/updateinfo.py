#
# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import logging
import yum
from yum.update_md import UpdateMetadata

log = logging.getLogger(__name__)
#
# yum 3.2.22 compat:  UpdateMetadata.add_notice() not
# supported in 3.2.22.
# 
if yum.__version__ < (3,2,28):
    def add_notice(self, un):
        if not un or not un["update_id"] or un['update_id'] in self._notices:
            return
        self._notices[un['update_id']] = un
        pkglist =  un['pkglist'] or []
        for pkg in pkglist:
            for filedata in pkg['packages']:
                self._cache['%s-%s-%s' % (filedata['name'],
                                          filedata['version'],
                                          filedata['release'])] = un
                no = self._no_cache.setdefault(filedata['name'], set())
                no.add(un)
    UpdateMetadata.add_notice = add_notice


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
    severity = ""
    if unotice.has_key('severity'):
        severity = unotice['severity']
    rights = ""
    if unotice.has_key('rights'):
        rights   = unotice['rights']
    summary = ""
    if unotice.has_key('summary'):
        summary = unotice['summary']
    solution = ""
    if unotice.has_key('solution'):
        solution = unotice['solution']
    erratum = Errata(id, title, description, version, release, type,
        status, updated, issued, pushcount, from_str, reboot_suggested,
        references, pkglist, severity, rights, summary, solution)
    return erratum

class Errata(dict):
    """
    Errata object to represent software updates
    maps to yum.update_md.UpdateNotice fields
    """

    def __init__(self, id, title, description, version, release, type, status=u"",
            updated=u"", issued=u"", pushcount=1, from_str=u"",
            reboot_suggested=False, references=[], pkglist=[], severity=u"",
            rights=u"", summary=u"", solution=u""):
        self.id = id
        self.title = title
        self.description = description
        self.version = version
        self.release = release
        self.type = type
        self.status = status
        self.updated = updated
        self.issued = issued
        if pushcount:
            self.pushcount = int(pushcount)
        else:
            self.pushcount = 1
        self.from_str = from_str
        self.reboot_suggested = reboot_suggested
        self.references = references
        self.pkglist = pkglist
        self.rights = rights
        self.severity = severity
        self.summary = summary
        self.solution = solution

    def __getattr__(self, attr):
        return self.get(attr, None)
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__
