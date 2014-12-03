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

from pulp.server.db.model.base import Model

# -- classes -----------------------------------------------------------------


class User(Model):
    """
    Represents a user of Pulp.

    @ivar login: user's login name, must be unique for each user
    @type login: str

    @ivar password: encrypted password for login credentials
    @type password: str

    @ivar name: user's full name
    @type name: str

    @ivar roles: list of roles user belongs to
    @type roles: list of str
    """

    collection_name = 'users'
    unique_indices = ('login',)
    search_indices = ('name', 'roles',)

    def __init__(self, login, password, name=None, roles=None):
        super(User, self).__init__()

        self.login = login
        self.password = password
        self.name = name or login
        self.roles = roles or []


class Role(Model):
    """
    Represents a role and a set of permissions associated with that role.
    Users that are added to this role will inherit all the permissions associated
    with the role.

    @ivar id: role's id, must be unique for each role
    @type id: str

    @ivar display_name: user-readable name of the role
    @type display_name: str

    @ivar description: free form text used to describe the role
    @type description: str

    @ivar permissions: dictionary of resource: tuple of allowed operations
    @type permissions: dict
    """

    collection_name = 'roles'
    unique_indices = ('id',)

    def __init__(self, id, display_name=None, description=None, permissions=None):
        super(Role, self).__init__()

        self.id = id
        self.display_name = display_name or id
        self.description = description
        self.permissions = permissions or {}


class Permission(Model):
    """
    Represents the user permissions associated with a pulp resource.

    @ivar resource: uri path of resource
    @type resource: str

    @ivar users: list of dictionaries of user logins and permissions
    @type users: list
    """

    collection_name = 'permissions'
    unique_indices = ('resource',)

    def __init__(self, resource, users=None):
        super(Permission, self).__init__()

        self.resource = resource
        self.users = users or []
