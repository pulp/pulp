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
from pulp.common import dateutils


class CDSAPI(PulpAPI):
    '''
    Connection class to the CDS APIs.
    '''
    def cds(self, hostname):
        path = '/cds/%s/' % hostname
        return self.server.GET(path)[1]

    def register(self, hostname, name=None, description=None, sync_schedule=None, cluster_id=None):
        data = {'hostname': hostname,
                'name': name,
                'description': description,
                'sync_schedule' : sync_schedule,
                'cluster_id' : cluster_id}
        path = '/cds/'
        return self.server.POST(path, data)[1]

    def unregister(self, hostname, force):
        path = '/cds/%s/' % hostname

        data = {}
        if force:
            data['force'] = True

        return self.server.DELETE(path, data)[1]

    def update(self, hostname, delta):
        path = '/cds/%s/' % hostname
        return self.server.PUT(path, delta)[1]

    def list(self):
        path = '/cds/'
        return self.server.GET(path)[1]

    def history(self, hostname,
                event_type=None,
                limit=None,
                sort=None,
                start_date=None,
                end_date=None):

        data = {}
        if event_type:
            data['event_type'] = event_type
        if limit:
            data['limit'] = limit
        if sort:
            data['sort'] = sort
        if start_date:
            # ghetto input validation
            dateutils.parse_iso8601_date(start_date)
            data['start_date'] = start_date
        if end_date:
            # again, ghetto input validation
            dateutils.parse_iso8601_date(end_date)
            data['end_date'] = end_date

        path = '/cds/%s/history/' % hostname
        return self.server.POST(path, data)[1]

    def associate(self, hostname, repo_id):
        data = {'repo_id' : repo_id}
        path = '/cds/%s/associate/' % hostname
        return self.server.POST(path, data)[1]

    def unassociate(self, hostname, repo_id):
        data = {'repo_id' : repo_id}
        path = '/cds/%s/unassociate/' % hostname
        return self.server.POST(path, data)[1]

    def sync(self, hostname):
        data = {}
        path = '/cds/%s/sync/' % hostname
        return self.server.POST(path, data)[1]

    def sync_list(self, hostname):
        path = '/cds/%s/sync/' % hostname
        return self.server.GET(path)[1]

    def sync_history(self, repoid):
        path = "/cds/%s/history/sync/" % repoid
        return self.server.GET(path)[1]
