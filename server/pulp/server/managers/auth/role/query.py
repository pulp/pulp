"""
Contains roles query classes
"""
from pulp.server.db.model.auth import Role


class RoleQueryManager(object):
    """
    Manager used to process queries on roles. Roles returned from
    these calls are role SON objects from the database.
    """
    def find_all(self):
        """
        Returns serialized versions of all role in the database.

        @return: list of serialized roles
        @rtype:  list of dict
        """
        all_roles = list(Role.get_collection().find())
        return all_roles

    def find_by_id(self, role_id):
        """
        Returns a serialized version of the given role if it exists.
        If a role cannot be found with the given id, None is returned.

        @return: serialized data describing the role
        @rtype:  dict or None
        """
        role = Role.get_collection().find_one({'id': role_id})
        return role

    def get_other_roles(self, role, role_ids):
        """
        Get a list of role instances corresponding to the role ids, excluding the
        given role instance

        @type role: L{pulp.server.model.db.Role} instance
        @param role: role to exclude

        @type role_ids: list or tuple of str's

        @rtype: list of L{pulp.server.model.db.Role} instances
        @return: list of roles
        """
        return [self.find_by_id(n) for n in role_ids if n != role['id']]
