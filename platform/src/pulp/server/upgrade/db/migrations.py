# -*- coding: utf-8 -*-
# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""
Initializes the migration versions to 0 so that the migrations will run
when pulp-manage-db is invoked.
"""

from pulp.server.upgrade.model import UpgradeStepReport

# List of packages to add migration tracker entries for
MIGRATION_PACKAGES = (
    'pulp.server.db.migrations',
    'pulp_puppet.plugins.migrations',
    'pulp_rpm.migrations',
)


def upgrade(v1_database, v2_database):
    report = UpgradeStepReport()

    tracker_coll = v2_database.migration_trackers

    # Idempotency: By name, make sure it's not present
    existing_name_list = tracker_coll.find({}, {'name' : 1})
    existing_names = [n['name'] for n in existing_name_list]
    migrate_names = [n for n in MIGRATION_PACKAGES if n not in existing_names]

    for pkg in migrate_names:
        tracker = {
            'name' : pkg,
            'version' : 0,
        }
        tracker_coll.insert(tracker, safe=True)

    report.succeeded()
    return report
