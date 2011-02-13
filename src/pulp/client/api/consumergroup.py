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


class ConsumerGroupAPI(PulpAPI):
    """
    Connection class to access consumer group related calls
    """
    def create(self, id, description, consumerids=[]):
        consumergroup_data = {"id": id,
                              "description": description,
                              "consumerids": consumerids}
        path = "/consumergroups/"
        return self.server.PUT(path, consumergroup_data)

    def update(self, consumergroup):
        path = "/consumergroups/%s/" % consumergroup['id']
        return self.server.PUT(path, consumergroup)

    def delete(self, id):
        path = "/consumergroups/%s/" % id
        return self.server.DELETE(path)

    def clean(self):
        path = "/consumergroups/"
        return self.server.DELETE(path)

    def consumergroups(self):
        path = "/consumergroups/"
        return self.server.GET(path)

    def consumergroup(self, id):
        path = "/consumergroups/%s/" % str(id)
        return self.server.GET(path)

    def add_consumer(self, id, consumerid):
        path = "/consumergroups/%s/add_consumer/" % id
        return self.server.POST(path, consumerid)

    def delete_consumer(self, id, consumerid):
        path = "/consumergroups/%s/delete_consumer/" % id
        return self.server.POST(path, consumerid)

    def bind(self, id, repoid):
        path = "/consumergroups/%s/bind/" % id
        return self.server.POST(path, repoid)

    def unbind(self, id, repoid):
        path = "/consumergroups/%s/unbind/" % id
        return self.server.POST(path, repoid)

    def add_key_value_pair(self, id, key, value, force):
        key_value_dict = {'key' : key, 'value' : value, 'force'  : force}
        path = "/consumergroups/%s/add_key_value_pair/" % id
        return self.server.POST(path, key_value_dict)

    def delete_key_value_pair(self, id, key):
        path = "/consumergroups/%s/delete_key_value_pair/" % id
        return self.server.POST(path, key)

    def update_key_value_pair(self, id, key, value):
        key_value_dict = {'key' : key, 'value' : value}
        path = "/consumergroups/%s/update_key_value_pair/" % id
        return self.server.POST(path, key_value_dict)

    def installpackages(self, id, packagenames, when=None):
        path = "/consumergroups/%s/installpackages/" % id
        body = dict(packagenames=packagenames, scheduled_time=when)
        return self.server.POST(path, body)

    def installerrata(self, id, errataids, types=[], assumeyes=False, when=None):
        erratainfo = {'consumerid': id,
                      'errataids': errataids,
                      'types':   types,
                      'assumeyes': assumeyes,
                      'scheduled_time': when}
        path = "/consumergroups/%s/installerrata/" % id
        return self.server.POST(path, erratainfo)

