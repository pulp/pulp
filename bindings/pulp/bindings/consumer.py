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
from pulp.bindings.search import SearchAPI

# Default for update APIs to differentiate between None and not updating the value
UNSPECIFIED = object()


class ConsumerAPI(PulpAPI):
    """
    Connection class to access consumer specific calls
    """
    def __init__(self, pulp_connection):
        super(ConsumerAPI, self).__init__(pulp_connection)
        self.base_path = "/v2/consumers/"

    def consumers(self, **options):
        """
        options:
          details (bool) - include all details
          bindings (bool) - include bindings
        """
        path = self.base_path
        return self.server.GET(path, options)

    def register(self, id, name=None, description=None, notes=None, rsa_pub=None):
        path = self.base_path
        body = {
            "id": id,
            "display_name": name,
            "description": description,
            "notes": notes,
            "rsa_pub": rsa_pub
        }
        return self.server.POST(path, body)

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


class ConsumerSearchAPI(SearchAPI):
    PATH = "/v2/consumers/search/"


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


class ConsumerContentSchedulesAPI(PulpAPI):
    """
    Connection class to access consumer calls related to scheduled content install/uninstall/update
    Each function inside the class accepts an additional 'action' parameter. This is to specify a particular
    schedule action. Possible values are 'install', 'update' and 'uninstall'.
    """
    def __init__(self, pulp_connection):
        """
        @type:   pulp_connection: pulp.bindings.server.PulpConnection
        """
        super(ConsumerContentSchedulesAPI, self).__init__(pulp_connection)
        self.base_path = "/v2/consumers/%s/schedules/content/"

    def list_schedules(self, action, consumer_id):
        url = self.base_path % consumer_id + action + '/'
        return self.server.GET(url)

    def get_schedule(self, action, consumer_id, schedule_id):
        url = self.base_path % consumer_id + action + '/%s/' % schedule_id
        return self.server.GET(url)

    def add_schedule(self, action, consumer_id, schedule, units, failure_threshold=UNSPECIFIED,
                     enabled=UNSPECIFIED, options=UNSPECIFIED):
        url = self.base_path % consumer_id + action + '/'
        body = {
            'schedule' : schedule,
            'units': units,
            'failure_threshold' : failure_threshold,
            'enabled' : enabled,
            'options': options,
            }
        # Strip out anything that wasn't specified by the caller
        body = dict([(k, v) for k, v in body.items() if v is not UNSPECIFIED])
        return self.server.POST(url, body)

    def delete_schedule(self, action, consumer_id, schedule_id):
        url = self.base_path % consumer_id + action + '/%s/' % schedule_id
        return self.server.DELETE(url)

    def update_schedule(self, action, consumer_id, schedule_id, schedule=UNSPECIFIED, units=UNSPECIFIED,
                        failure_threshold=UNSPECIFIED, remaining_runs=UNSPECIFIED, enabled=UNSPECIFIED,
                        options=UNSPECIFIED):
        url = self.base_path % consumer_id + action + '/%s/' % schedule_id
        body = {
            'schedule' : schedule,
            'units': units,
            'failure_threshold' : failure_threshold,
            'remaining_runs' : remaining_runs,
            'enabled' : enabled,
            'options': options,
            }
        # Strip out anything that wasn't specified by the caller
        body = dict([(k, v) for k, v in body.items() if v is not UNSPECIFIED])
        self.server.PUT(url, body)


class BindingsAPI(PulpAPI):

    BASE_PATH = '/v2/consumers/%s/bindings/'

    def find_by_id(self, consumer_id, repo_id=None):
        path = self.BASE_PATH % consumer_id
        if repo_id:
            path += '%s/' % repo_id
        return self.server.GET(path)

    def bind(self, consumer_id, repo_id, distributor_id, notify_agent=True, binding_config=None):
        path = self.BASE_PATH % consumer_id
        data = {
            'repo_id' :repo_id,
            'distributor_id' :distributor_id,
            'notify_agent': notify_agent,
            'binding_config': binding_config or {}
        }
        return self.server.POST(path, data)

    def unbind(self, consumer_id, repo_id, distributor_id, force=False):
        path = self.BASE_PATH % consumer_id + "%s/" % repo_id + "%s/" % distributor_id
        body = dict(force=force)
        return self.server.DELETE(path, body)


class BindingSearchAPI(SearchAPI):
    PATH = "/v2/consumers/binding/search/"


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


