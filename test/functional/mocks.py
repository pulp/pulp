#!/usr/bin/python
#
# Copyright (c) 2011 Red Hat, Inc.
#
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

#
# Contains agent (gofer) mocks used for testing.
# Most only do argument checking.  Add additional functionality
# as needed.
#


from gofer.rmi import mock

def install():
    mock.install()
    mock.reset()
    mock.register(
        Consumer=Consumer,
        Packages=Packages,
        PackageGroups=PackageGroups,
        cdsplugin=cdsplugin,)

def reset():
    mock.reset()

def all():
    return mock.all()


class Consumer(object):

    def unregistered(self):
        pass

    def bind(self, repoid, data):
        pass

    def unbind(self, repoid):
        pass

    def update(self, repoid, data):
        pass


class Packages(object):

    def install(self, names, reboot=False):
        pass

    def update(self, names=(), reboot=False):
        pass

    def uninstall(self, names):
        return names

    def __call__(self, *args, **kwargs):
        pass


class PackageGroups(object):

    def install(self, names):
        pass

    def uninstall(self, names):
        return names

    def __call__(self, *args, **kwargs):
        pass


class cdsplugin(object):

    SECRET = 'SECRET'

    def initialize(self):
        return self.SECRET

    def release(self):
        pass

    def sync(self, payload):
        self.payload = payload

    def update_cluster_membership(self, cluster_name, member_hostnames):
        self.cluster_name = cluster_name
        self.member_hostnames = member_hostnames
