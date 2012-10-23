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

    # Collection: users
    #   No changes

    # Collection: permissions
    #   No changes

    # Collection: roles
    v1_roles_coll = v1_database.roles
    v2_roles_coll = v2_database.roles

    all_v1_roles = list(v1_roles_coll.find())
    v2_roles_to_add = []

    for v1_role in all_v1_roles:

        # Idempotency: If there's already a role with the given name, don't
        # re-add it.

        existing = v2_roles_coll.find_one({'display_name' : v1_role['name']})
        if existing is not None:
            continue

        v2_role = {
            'display_name' : v1_role['name'],
            'description' : None,
            'permissions' : v1_role['permissions'],
        }
        v2_roles_to_add.append(v2_role)

    if len(v2_roles_to_add) > 0:
        v2_roles_coll.insert(v2_roles_to_add)

    # Final report
    report = UpgradeStepReport()
    report.succeeded()
    return report
