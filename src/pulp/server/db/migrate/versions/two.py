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

import logging

from pulp.server.api.consumer import ConsumerApi
from pulp.server.api.repo import RepoApi
from pulp.server.api.role import RoleAPI
from pulp.server.api.user import UserApi
from pulp.server.auth.authorization import (consumer_users_role,
    add_user_to_role, grant_automatic_permissions_to_consumer_user)


_log = logging.getLogger('pulp')

# migration module conventions ------------------------------------------------

version = 2


def _migrate_builtin_roles():
    api = RoleAPI()
    for role in api._getcollection().find():
        # just delete the roles, the proper ones will get create when pulp starts
        if role['name'] in ('SuperUsers', 'ConsumerUsers'):
            api.delete(role)


def _migrate_consumer_model():
    api = ConsumerApi()
    user_api = UserApi()
    for consumer in api._getcollection().find():
        key = 'credentials'
        if key not in consumer:
            consumer[key] = None
            api.update(consumer)
        # look for the corresponding consumer user and create it if missing
        user = user_api.user(consumer['id'])
        if not user:
            user = user_api.create(consumer['id'])
            add_user_to_role(consumer_users_role, user['login'])
            grant_automatic_permissions_to_consumer_user(user['login'])


def _migrate_repo_model():
    api = RepoApi()
    for repo in api._getcollection().find():
        modified = False
        if 'package_count' not in repo:
            repo['package_count'] = len(repo['packages'])
            modified = True
        if 'distributionid' not in repo:
            repo['distributionid'] = []
            modified = True
        if not isinstance(repo['packages'], list):
            repo['packages'] = [pkg_id for pkg_id in repo['packages']]
            modified = True
        if modified:
            api.update(repo)


def _migrate_user_model():
    api = UserApi()
    for user in api._getcollection().find():
        modified = False
        if 'roles' not in user or not isinstance(user['roles'], list):
            user['roles'] = []
            modified = True
        elif 'SuperUsers' in user['roles']:
            user['roles'].remove('SuperUsers')
            user['roles'].append('super-users')
            modified = True
        elif 'ConsumerUsers' in user['roles']:
            user['roles'].remove('ConsumerUsers')
            user['roles'].append('consumer-users')
            modified = True
        if modified:
            api.update(user)


def migrate():
    _log.info('migration to data model version 2 started')
    _migrate_builtin_roles()
    _migrate_consumer_model()
    _migrate_repo_model()
    _migrate_user_model()
    _log.info('migration to data model version 2 complete')
