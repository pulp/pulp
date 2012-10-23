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
    all_v1_roles = list(v1_roles_coll.find())
    all_v2_roles = []

    for v1_role in all_v1_roles:
        v2_role = {
            'display_name' : v1_role['name'],
            'description' : None,
            'permissions' : v1_role['permissions'],
        }
        all_v2_roles.append(v2_role)

    v2_roles_coll = v2_database.roles
    v2_roles_coll.insert(all_v2_roles)

    # Final report
    report = UpgradeStepReport()
    report.succeeded()
    return report
