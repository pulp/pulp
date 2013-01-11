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

import os
import shutil
from pulp.server.upgrade.model import UpgradeStepReport

DIR_STORAGE_ROOT = '/var/lib/pulp/content/'
DIR_DISTROS = os.path.join(DIR_STORAGE_ROOT, 'distributions')
V1_DIR_DISTROS = '/var/lib/pulp/distributions/'

def upgrade(v1_database, v2_database):
    report = UpgradeStepReport()

    distro_success = _distribution(v1_database, v2_database, report)
    report.success = distro_success
    return report

def _distribution(v1_database, v2_database, report):
    """
    Migrate distribution and associated from v1 to v2 location on filesystem. It assumes
    the distribution is already migrated in the Database. The distribution and its files
    from v1 are migarted to /var/lib/pulp/content/distribution/ in v2.
    """
    all_v2_distros = v2_database.units_distribution
    all_v1_distros = v1_database.distribution.find()
    for v1_distro in all_v1_distros:
        distro_id = v1_distro['id']
        v1_distro_path = V1_DIR_DISTROS + distro_id
        if not os.path.exists(v1_distro_path):
            # missing source path, skip migrate
            report.warning("distribution path %s does not exist" % v1_distro_path)
            continue
        v2_distro_path = os.path.join(DIR_DISTROS, distro_id)
        try:
            v2_distro_dir = os.path.dirname(v2_distro_path)
            if not os.path.isdir(v2_distro_dir):
                os.makedirs(v2_distro_dir)
            shutil.copytree(v1_distro_path, v2_distro_path)
        except Exception, e:
            report.error("Error: %s" % e)
            return False
    return True