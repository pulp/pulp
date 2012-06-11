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

import os
import sys
import logging
import yum
from yum.update_md import UpdateMetadata, UpdateNotice
from pulp.server.db.model import Errata
from pulp.server.api.errata import ErrataApi
from pulp.server.compat import chain
import pulp.server.util

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
    um.add(pulp.server.util.encode_unicode(path_to_updateinfo))
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

def generate_updateinfo(repo):
    """
    Method to generate updateinfo xml for a given repo, write to file and
    update repomd.xml with new updateinfo
    @param repo:  repo object with errata to generate updateinfo.xml
    @type repo:  repository object
    """
    if repo['preserve_metadata']:
        # metadata is set to be preserved, dont generate updatinfo
        return
    if not repo['errata']:
        #no errata to process, return
        return
    errataids = list(chain.from_iterable(repo['errata'].values()))
    repo_dir = "%s/%s/" % (pulp.server.util.top_repos_location(), repo['relative_path'])
    updateinfo_path = updateinfo(errataids, repo_dir)
    if updateinfo_path:
        log.debug("Modifying repo for updateinfo")
        pulp.server.util.modify_repo(os.path.join(repo_dir, "repodata"),
                updateinfo_path)

def updateinfo(errataids, save_location):
    um = UpdateMetadata()
    eapi = ErrataApi()
    for eid in errataids:
        un = UpdateNotice()
        e = eapi.erratum(eid)

        _md = {
            'from'             : e['from_str'],
            'type'             : e['type'],
            'title'            : e['title'],
            'release'          : e['release'],
            'status'           : e['status'],
            'version'          : e['version'],
            'pushcount'        : e['pushcount'],
            'update_id'        : e['id'],
            'issued'           : e['issued'],
            'updated'          : e['updated'],
            'description'      : e['description'],
            'references'       : e['references'],
            'pkglist'          : e['pkglist'],
            'reboot_suggested' : e['reboot_suggested'],
            'severity'         : e['severity'],
            'rights'           : e['rights'],
            'summary'          : e['summary'],
            'solution'         : e['solution'],
        }
        un._md = _md
        um.add_notice(un)

    if not um._notices:
        # nothing to do return
        return
    updateinfo_path = None
    try:
        updateinfo_path = "%s/%s" % (save_location, "updateinfo.xml")
        updateinfo_xml = um.xml(fileobj=open(updateinfo_path, 'wt'))
        log.info("updateinfo.xml generated and written to file %s" % updateinfo_path)
    except:
        log.error("Error writing updateinfo.xml to path %s" % updateinfo_path)
    return updateinfo_path

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
