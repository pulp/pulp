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


consumer_deferred_fields = ('package_profile', 'repoids')


class ConsumerAPI(PulpAPI):
    """
    Connection class to access repo specific calls
    """
    def create(self, id, description, key_value_pairs={}):
        consumerdata = {"id": id,
                        "description": description,
                        "key_value_pairs": key_value_pairs}
        path = "/consumers/"
        return self.server.PUT(path, consumerdata)[1]

    def update(self, consumer):
        path = "/consumers/%s/" % consumer['id']
        return self.server.PUT(path, consumer)[1]

    def bulkcreate(self, consumers):
        path = "/consumers/bulk/"
        return self.server.POST(path, consumers)[1]

    def delete(self, id):
        path = "/consumers/%s/" % id
        return self.server.DELETE(path)[1]

    def clean(self):
        path = "/consumers/"
        return self.server.DELETE(path)[1]

    def consumer(self, id):
        path = "/consumers/%s/" % str(id)
        consumer = self.server.GET(path)[1]
        for field in consumer_deferred_fields:
            consumer[field] = self.server.GET('%s%s/' % (path, field))[1]
        return consumer

    def packages(self, id):
        path = "/consumers/%s/packages/" % str(id)
        return self.server.GET(path)[1]

    def certificate(self, id):
        path = "/consumers/%s/certificate/" % str(id)
        cert_dict = self.server.GET(path)
        return cert_dict

    def consumers(self):
        path = "/consumers/"
        consumers = self.server.GET(path)[1]
        for c in consumers:
            consumer_link = "/consumers/%s/" % str(c["id"])
            c['repoids'] = self.server.GET('%s%s/' % (consumer_link, 'repoids'))[1]
        return consumers

    def consumers_with_package_name(self, name):
        path = '/consumers/?package_name=%s' % name
        return self.server.GET(path)[1]

    def bind(self, id, repoid):
        path = "/consumers/%s/bind/" % id
        return self.server.POST(path, repoid)[1]

    def unbind(self, id, repoid):
        path = "/consumers/%s/unbind/" % id
        return self.server.POST(path, repoid)[1]

    def add_key_value_pair(self, id, key, value):
        key_value_dict = {'key' : key, 'value' : value}
        path = "/consumers/%s/add_key_value_pair/" % id
        return self.server.POST(path, key_value_dict)[1]

    def delete_key_value_pair(self, id, key):
        path = "/consumers/%s/delete_key_value_pair/" % id
        return self.server.POST(path, key)[1]

    def update_key_value_pair(self, id, key, value):
        key_value_dict = {'key' : key, 'value' : value}
        path = "/consumers/%s/update_key_value_pair/" % id
        return self.server.POST(path, key_value_dict)[1]

    def get_keyvalues(self, id):
        path = "/consumers/%s/keyvalues/" % str(id)
        return self.server.GET(path)[1]

    def profile(self, id, profile):
        path = "/consumers/%s/profile/" % id
        return self.server.POST(path, profile)[1]

    def installpackages(self, id, packagenames, when=None):
        path = "/consumers/%s/installpackages/" % id
        body = dict(packagenames=packagenames, scheduled_time=when)
        return self.server.POST(path, body)[1]

    def installpackagegroups(self, id, packageids, when=None):
        path = "/consumers/%s/installpackagegroups/" % id
        body = dict(packageids=packageids, scheduled_time=when)
        return self.server.POST(path, body)[1]

    def installpackagegroupcategories(self, id, repoid, categoryids, when=None):
        path = "/consumers/%s/installpackagegroupcategories/" % id
        body = dict(categoryids=categoryids, repoid=repoid, scheduled_time=when)
        return self.server.POST(path, body)[1]

    def errata(self, id, types=None):
        path = "/consumers/%s/listerrata/" % id
        body = dict(types=types)
        return self.server.POST(path, body)[1]

    def package_updates(self, id):
        path = "/consumers/%s/package_updates/" % id
        return self.server.GET(path)[1]

    def errata_package_updates(self, id):
        path = "/consumers/%s/errata_package_updates/" % id
        return self.server.GET(path)[1]

    def installerrata(self, id, errataids, assumeyes=False, types=(), when=None):
        erratainfo = {'consumerid': id,
                      'errataids': errataids,
                      'types':   types,
                      'assumeyes': assumeyes,
                      'scheduled_time': when}
        path = "/consumers/%s/installerrata/" % id
        return self.server.POST(path, erratainfo)[1]

    def history(self, id, query_params):
        path = "/consumers/%s/history/" % id
        return self.server.POST(path, query_params)[1]
