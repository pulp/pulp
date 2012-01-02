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


class ConsumerGroupAPI(PulpAPI):
    """
    Connection class to access consumer group related calls
    """
    def create(self, id, description, consumerids=[]):
        consumergroup_data = {"id": id,
                              "description": description,
                              "consumerids": consumerids}
        path = "/consumergroups/"
        return self.server.POST(path, consumergroup_data)[1]

    def update(self, id, delta):
        path = "/consumergroups/%s/" % id
        return self.server.PUT(path, delta)[1]

    def delete(self, id):
        path = "/consumergroups/%s/" % id
        return self.server.DELETE(path)[1]

    def clean(self):
        path = "/consumergroups/"
        return self.server.DELETE(path)[1]

    def consumergroups(self):
        path = "/consumergroups/"
        return self.server.GET(path)[1]

    def consumergroup(self, id):
        path = "/consumergroups/%s/" % str(id)
        return self.server.GET(path)[1]

    def add_consumer(self, id, consumerid):
        path = "/consumergroups/%s/add_consumer/" % id
        return self.server.POST(path, consumerid)[1]

    def delete_consumer(self, id, consumerid):
        path = "/consumergroups/%s/delete_consumer/" % id
        return self.server.POST(path, consumerid)[1]

    def bind(self, id, repoid):
        path = "/consumergroups/%s/bind/" % id
        return self.server.POST(path, repoid)[1]

    def unbind(self, id, repoid):
        path = "/consumergroups/%s/unbind/" % id
        return self.server.POST(path, repoid)[1]

    def add_key_value_pair(self, id, key, value, force):
        key_value_dict = {'key' : key, 'value' : value, 'force'  : force}
        path = "/consumergroups/%s/add_key_value_pair/" % id
        return self.server.POST(path, key_value_dict)[1]

    def delete_key_value_pair(self, id, key):
        path = "/consumergroups/%s/delete_key_value_pair/" % id
        return self.server.POST(path, key)[1]

    def update_key_value_pair(self, id, key, value):
        key_value_dict = {'key' : key, 'value' : value}
        path = "/consumergroups/%s/update_key_value_pair/" % id
        return self.server.POST(path, key_value_dict)[1]

    def installpackages(self, id, packagenames, when=None):
        path = "/consumergroups/%s/installpackages/" % id
        body = dict(packagenames=packagenames, scheduled_time=when)
        return self.server.POST(path, body)[1]

    def updatepackages(self, id, packagenames, when=None):
        path = "/consumergroups/%s/updatepackages/" % id
        body = dict(packagenames=packagenames, scheduled_time=when)
        return self.server.POST(path, body)[1]

    def uninstallpackages(self, id, packagenames, when=None):
        path = "/consumergroups/%s/uninstallpackages/" % id
        body = dict(packagenames=packagenames, scheduled_time=when)
        return self.server.POST(path, body)[1]

    def installpackagegroups(self, id, grpids, when=None):
        path = "/consumergroups/%s/installpackagegroups/" % id
        body = dict(grpids=grpids, scheduled_time=when)
        return self.server.POST(path, body)[1]

    def uninstallpackagegroups(self, id, grpids, when=None):
        path = "/consumergroups/%s/uninstallpackagegroups/" % id
        body = dict(grpids=grpids, scheduled_time=when)
        return self.server.POST(path, body)[1]

    def installerrata(self, id, errataids, types=[], importkeys=False, when=None):
        erratainfo = {'errataids': errataids,
                      'types':   types,
                      'importkeys': importkeys,
                      'scheduled_time': when}
        path = "/consumergroups/%s/installerrata/" % id
        return self.server.POST(path, erratainfo)[1]

