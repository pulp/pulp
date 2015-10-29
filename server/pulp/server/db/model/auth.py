# -*- coding: utf-8 -*-

from pulp.server.db.model.base import Model


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
