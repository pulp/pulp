#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
#
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

#
# Contains agent (gofer) mocks used for testing.
# Most only do argument checking.  Add additional functionality
# as needed.
#


from gofer.messaging import mock

def install():
    mock.install()
    mock.reset()
    mock.register(
        Consumer=Consumer,
        Repo=Repo,
        Packages=Packages,
        PackageGroups=PackageGroups,
        cdsplugin=cdsplugin,)

def reset():
    mock.reset()

def all():
    return mock.all()


class Consumer(object):

    def deleted(self):
        pass


class Repo(object):

    def bind(self, repoid, data):
        pass

    def unbind(self, repoid):
        pass

    def update(self, repoid, data):
        pass


class Packages(object):

    def install(self, packageinfo, reboot=False, yes=False):
        pass


class PackageGroups(object):

    def install(self, packagegroupids):
        pass


class cdsplugin(object):

    SECRET = 'SECRET'

    def initialize(self):
        return self.SECRET

    def release(self):
        pass

    def sync(self, url, repos):
        pass

    def set_repo_auth(self, repoid, path, bundle):
        pass

    def set_global_repo_auth(self, bundle):
        pass
