# -*- coding: utf-8 -*-

# Copyright © 2010 Red Hat, Inc.
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

from pulp.server.db.model.base import Base


class Permission(Base):

    def __init__(self, resource):
        super(Permission, self).__init__()
        self.resource = resource
        self.users = {}


class Role(Base):

    def __init__(self, name):
        self._id = self.name = name
        self.permissions = {}


class User(Base):
    def __init__(self, login, id, password, name):
        self._id = id
        self.id = id
        self.login = login
        self.password = password
        self.name = name
        self.roles = []

    def __unicode__(self):
        return unicode(self.name)
