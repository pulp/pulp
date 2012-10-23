# -*- coding: utf-8 -*-
# Copyright (c) 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from pulp.server.upgrade.model import UpgradeStepReport


def upgrade(v1_database, v2_database):

    _roles(v1_database, v2_database)
    _permissions(v1_database, v2_database)
    _users(v1_database, v2_database)

    report = UpgradeStepReport()
    report.succeeded()
    return report


def _roles(v1_database, v2_database):
    v1_roles_coll = v1_database.roles
    v2_roles_coll = v2_database.roles

    all_v1_roles = list(v1_roles_coll.find())
    v2_roles_to_add = []

    for v1_role in all_v1_roles:

        # Idempotency: If there's already a v2 role whose id is the name in v1,
        # don't re-add it.

        existing = v2_roles_coll.find_one({'id' : v1_role['name']})
        if existing is not None:
            continue

        v2_role = {
            'id' : v1_role['name'],
            'display_name' : v1_role['name'],
            'description' : None,
            'permissions' : v1_role['permissions'],
        }
        v2_roles_to_add.append(v2_role)

    if v2_roles_to_add:
        v2_roles_coll.insert(v2_roles_to_add)


def _permissions(v1_database, v2_database):
    v1_coll = v1_database.permissions
    v2_coll = v2_database.permissions

    # Idempotency: There's no unique ID other than _id, so we're explicitly
    # maintaining them in the upgrade for this check.
    v2_ids = [x['_id'] for x in list(v2_coll.find({}, {'_id' : 1}))]
    missing_v1_permissions = list(v1_coll.find({'_id' : {'$nin' : v2_ids}}))

    v2_permissions_to_add = []
    for v1_permission in missing_v1_permissions:
        v2_permission = {
            '_id' : v1_permission['_id'], # for uniqueness check by this script
            'resource' : v1_permission['resource'],
            'users' : v1_permission['users'],
        }
        v2_permissions_to_add.append(v2_permission)

    if v2_permissions_to_add:
        v2_coll.insert(v2_permissions_to_add)


def _users(v1_database, v2_database):
    v1_coll = v1_database.users
    v2_coll = v2_database.users

    # Idempotency: Check already upgraded users by login
    v2_logins = [x['login'] for x in list(v2_coll.find({}, {'login' : 1}))]
    missing_v1_users = list(v1_coll.find({'login' : {'$nin' : v2_logins}}))

    v2_users_to_add = []
    for v1_user in missing_v1_users:
        v2_user = {
            'login' : v1_user['login'],
            'password' : v1_user['password'],
            'name' : v1_user['name'] or v1_user['login'],
            'roles' : v1_user['roles'],
        }
        v2_users_to_add.append(v2_user)

    if v2_users_to_add:
        v2_coll.insert(v2_users_to_add)

