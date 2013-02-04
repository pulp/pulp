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

"""
Calculates the content_unit_count field for all v2 repositories. This must
not be run until all of the repos and their content units have been migrated.
"""

from pulp.server.upgrade.model import UpgradeStepReport


def upgrade(v1_database, v2_database):
    report = UpgradeStepReport()

    # Idempotency: Don't bother; worst case we recalculate.
    repo_coll = v2_database.repos
    ass_coll = v2_database.repo_content_units

    v2_repos = repo_coll.find()
    for v2_repo in v2_repos:
        spec = {'repo_id' : v2_repo['id']}
        unit_count = ass_coll.find(spec).count()

        v2_repo['content_unit_count'] = unit_count

        repo_coll.save(v2_repo, safe=True)

    report.succeeded()
    return report
