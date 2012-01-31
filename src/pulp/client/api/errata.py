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

from pulp.client.api.base import PulpAPI


class ErrataAPI(PulpAPI):
    """
    Connection class to access errata related calls
    """
    def clean(self):
        pass

    def create(self, id, title, description, version, release, type,
               status="", updated="", issued="", pushcount="", update_id="",
               from_str="", reboot_suggested="", references=[], pkglist=[],
               severity="", rights="", summary="", solution=""):

        params = {'id': id,
                  'title': title,
                  'description': description,
                  'version': version,
                  'release': release,
                  'type': type,
                  'status': status,
                  'updated': updated,
                  'issued': issued,
                  'pushcount': pushcount,
                  'from_str': from_str,
                  'reboot_suggested': reboot_suggested,
                  'references': references,
                  'pkglist': pkglist,
                  'severity' : severity,
                  'rights'   : rights,
                  'summary'  : summary,
                  'solution' : solution,}
        path = "/errata/"
        return self.server.POST(path, params)[1]

    def update(self, id, delta):
        path = "/errata/%s/" % id
        return self.server.PUT(path, delta)[1]

    def delete(self, erratumid):
        path = "/errata/%s/" % erratumid
        return self.server.DELETE(path)[1]

    def erratum(self, id):
        path = "/errata/%s/" % id
        return self.server.GET(path)[1]

    def errata(self, types=None, id=None, title=None, repo_defined=True, bzid=None, cve=None):
        path = "/errata/"
        queries = []
        if types:
            queries.append(('type', types))
        if id:
            queries.append(('id', id))
        if title:
            queries.append(('title', title))
        if not repo_defined:
            queries.append(('repo_defined', repo_defined))
        if bzid:
            queries.append(('bzid', bzid))
        if cve:
            queries.append(('cve', cve))
        return self.server.GET(path, queries)[1]

    def find_repos(self, id):
        path = "/errata/%s/get_repos/" % id
        return self.server.POST(path)[1]
