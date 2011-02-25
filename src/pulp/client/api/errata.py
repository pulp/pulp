# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
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

from pulp.client.api.base import PulpAPI


class ErrataAPI(PulpAPI):
    """
    Connection class to access errata related calls
    """
    def clean(self):
        pass

    def create(self, id, title, description, version, release, type,
               status="", updated="", issued="", pushcount="", update_id="",
               from_str="", reboot_suggested="", references=[], pkglist=[]):

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
                  'pkglist': pkglist}
        path = "/errata/"
        return self.server.POST(path, params)[1]

    def update(self, erratum):
        path = "/errata/%s/" % erratum['id']
        return self.server.PUT(path, erratum)[1]

    def delete(self, erratumid):
        path = "/errata/%s/" % erratumid
        return self.server.DELETE(path)[1]

    def erratum(self, id):
        path = "/errata/%s/" % id
        return self.server.GET(path)[1]

    def errata(self, id=None, title=None, description=None, version=None,
               release=None, type=None, status=None, updated=None, issued=None,
               pushcount=None, from_str=None, reboot_suggested=None):
        pass

    def find_repos(self, id):
        path = "/errata/%s/get_repos/" % id
        return self.server.POST(path)[1]
