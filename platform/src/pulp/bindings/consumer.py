# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from pulp.bindings.base import PulpAPI


class ConsumerAPI(PulpAPI):
    """
    Connection class to access consumer specific calls
    """
    def __init__(self, pulp_connection):
        super(ConsumerAPI, self).__init__(pulp_connection)
        self.base_path = "/v2/consumers/"

    def consumers(self):
        path = self.base_path
        return self.server.GET(path)

    def register(self, id, display_name, description, notes):
        path = self.base_path
        repodata = {"id": id,
                    "display_name": display_name,
                    "description": description,
                    "notes": notes,}
        return self.server.POST(path, repodata)

    def consumer(self, id):
        path = self.base_path + ("%s/" % id)
        return self.server.GET(path)

    def unregister(self, id):
        path = self.base_path + "%s/" % id
        return self.server.DELETE(path)

    def update(self, id, delta):
        path = self.base_path + "%s/" % id
        body = {'delta' : delta}
        return self.server.PUT(path, body)


class ConsumerContentAPI(PulpAPI):
    """
    Connection class to access consumer content install/uninstall/update calls
    """
    def __init__(self, pulp_connection):
        super(ConsumerContentAPI, self).__init__(pulp_connection)
        self.base_path = "/v2/consumers/%s/actions/content/"

    def install(self, id, units, options={}):
        path = self.base_path % id + "install/"
        data = {"units": units,
                "options": options,}
        return self.server.POST(path, data)

    def update(self, id, units, options={}):
        path = self.base_path % id + "update/"
        data = {"units": units,
                "options": options,}
        return self.server.POST(path, data)

    def uninstall(self, id, units, options={}):
        path = self.base_path % id + "uninstall/"
        data = {"units": units,
                "options": options,}
        return self.server.POST(path, data)



class BindingsAPI(PulpAPI):

    BASE_PATH = '/v2/consumers/%s/bindings/'

    def find_by_id(self, id, repoid=None):
        """
        Find bindings by consumer ID.
        @param id: A consumer ID.
        @type id: str
        @param repoid: An (optional) repository ID.
        @type repoid: str
        @return: A list of bindings.
        @rtype: list
        """
        path = self.BASE_PATH % id
        if repoid:
            path += '%s/' % repoid
        return self.server.GET(path)
    
    def bind(self, id, repo_id, distributor_id):
        path = self.BASE_PATH % id
        data = {'repo_id' : repo_id, 'distributor_id' : distributor_id}
        return self.server.POST(path, data)
    
    def unbind(self, id, repo_id, distributor_id):
        path = self.BASE_PATH % id + "%s/" % repo_id + "%s/" % distributor_id
        return self.server.DELETE(path)


class ProfilesAPI(PulpAPI):

    BASE_PATH = '/v2/consumers/%s/profiles/'

    def send(self, id, content_type, profile):
        path = self.BASE_PATH % id
        data = { 'content_type':content_type, 'profile':profile }
        return self.server.POST(path, data)


class ConsumerHistoryAPI(PulpAPI):
    """
    Connection class to access consumer history retrieval calls
    """
    def __init__(self, pulp_connection):
        super(ConsumerHistoryAPI, self).__init__(pulp_connection)
        self.base_path = "/v2/consumers/%s/history/"

    def history(self, consumer_id, event_type=None, limit=None, sort=None, start_date=None, end_date=None):
        path = self.base_path % consumer_id
        queries = {}
        if event_type:
            queries['event_type'] = event_type
        if limit:
            queries['limit'] = limit
        if sort:
            queries['sort'] = sort
        if start_date:
            queries['start_date'] = start_date
        if end_date:
            queries['end_date'] = end_date
        return self.server.GET(path, queries)
