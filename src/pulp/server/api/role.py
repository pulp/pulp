#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
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

import logging
import uuid

from pulp.server.api.base import BaseApi
from pulp.server.api.user import UserApi
from pulp.server.api.repo import RepoApi
from pulp.server.auditing import audit
from pulp.server.pexceptions import PulpException
from pulp.server import config
from pulp.server.db import model
from pulp.server.db.connection import get_object_db
from pulp.server.event.dispatcher import event
import pulp.server.auth.password_util as password_util
from pulp.server.db.model import RoleResourceType

log = logging.getLogger(__name__)
user_fields = model.User(None, None, None, None).keys()


class RoleApi(BaseApi):

    def __init__(self):
        BaseApi.__init__(self)
        self.userapi = UserApi()
        self.permapi = PermissionApi()
        self.repoapi = RepoApi()


    def _getcollection(self):
        return get_object_db('roles',
                             self._unique_indexes,
                             self._indexes)


    @audit(params=['name'])
    def create(self, name, description=None, action_types=None, resource_type=None):
        """
        Create a new Role object and return it
        """
        role = model.Role(name, description, action_types, resource_type)
        role = self.insert(role)
        return role


    def roles(self, spec=None, fields=None):
        """
        List all Roles.
        """
        roles = list(self.objectdb.find(spec=spec, fields=fields))
        return roles

    def role(self, name, fields=None):
        """
        Return a single Role object
        """
        return self.objectdb.find_one({'name': name}, fields)

    @audit(params=['name'])
    def delete(self, name):
        self.objectdb.remove({'name' : name}, safe=True)

    def add_instance(self, instance_id, role_name):
        role = self.role(role_name)
        instance = None
        resource_type = role['resource_type']
        if resource_type == RoleResourceType.REPO:
            repo = self.repoapi.repository(instance_id)
            self._add_instance(repo, role)
        else:
            raise PulpException("Only support access control on Repositories") 
        
        return role

        
    def _add_instance(self, instance, role):
        """
        Add an object to this Role
        TODO: Add object type checking to make sure we arent 
        adding objects to Roles managing the wrong type of thing
        """
        permission = self.permapi.create_with_role(instance, role)
        role['permissions'].append(permission)
        self.update(role)

         
    
    def add_user(self, role, user):
        """
        Add a single user to this role, granting them the permission to the object
        owned by this Role 
        """
        roles = user['roles']
        print "Roles: %s" % roles
        if (not roles.has_key(role['name'])):
            log.debug("Adding role!")
            roles[role['name']] = role
            self.userapi.update(user)
        users = role['users']
        if (users.count(user) == 0):
            users.append(user['login'])
            self.update(role)
        
    def check(self, user, object, resource_type, action_type):
        """
        Check if the passed in user has access to make the operation
        on the object you pass in.  This method is currently very inefficent 
        and will be improved as time goes on.
        """
        log.error("User in check(): %s"  % user)
        roles = user['roles'].values()
        for role in roles:
            log.info('Resource_type: %s' % resource_type)
            log.info('Role: %s' % role)
            log.info('role[resource_type]: %s' % role['resource_type'])
            # First check if Role is the right object type 
            object_match = False
            if role['resource_type'] == resource_type:
                action_types = role['action_types']
                log.info("action_types: %s" % action_types)
                if (action_types.count(action_type) > 0):
                    action_match = True
                permissions = role['permissions']
                log.info("Permissions: %s" % permissions)
                for perm in permissions:
                    log.info("Instance: %s" % perm['instance'])
                    log.info("object: %s" % object)
                    if (perm['instance']['id'] == object['id']):
                        object_match = True
                log.info("Action_match: %s , object_match: %s" % (action_match, object_match))
                return (action_match and object_match)
        return False
        
        
        
class PermissionApi(BaseApi):

    def __init__(self):
        BaseApi.__init__(self)


    def _getcollection(self):
        return get_object_db('permissions',
                             self._unique_indexes,
                             self._indexes)


    @audit(params=['role'])
    def create_with_role(self, instance, role):
        """
        Create a new Permission object and return it
        """
        permission = model.Permission(instance, role_id=role['id'])
        self.insert(permission)
        return permission

    def create_with_user(self, instance, user):
        """
        Create a new Permission object and return it
        """
        permission = model.Permission(instance, user_login=user['login'])
        self.insert(permission)
        return permission

    def permissions(self, spec=None, fields=None):
        """
        List all Permissions
        """
        perms = list(self.objectdb.find(spec=spec, fields=fields))
        return perms

    def permission(self, id, fields=None):
        """
        Return a single User object
        """
        return self.objectdb.find_one({'id': id}, fields)

    @audit(params=['name'])
    def delete(self, id):
        self.objectdb.remove({'id' : id}, safe=True)
        
        
        
        
        
        
        
