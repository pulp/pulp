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
DIR_ISOS = os.path.join(DIR_STORAGE_ROOT, 'isos')
V1_DIR_ISO = '/var/lib/pulp/files/'

def upgrade(v1_database, v2_database):
    report = UpgradeStepReport()

    isos_success = _isos(v1_database, v2_database, report)
    report.success = isos_success
    return report

def _isos(v1_database, v2_database, report):
    """
    Migrate isos from v1 to v2 location on filesystem. It assumes
    the iso is already migrated in the Database. The isos from v1
    are migrated to /var/lib/pulp/content/isos/ in v2.
    """
    all_v1_files = v1_database.file.find()
    for v1_file in list(all_v1_files):
        isos_rel_path =  "%s/%s/%s/%s" % (v1_file['filename'][:3], v1_file['filename'], v1_file['checksum'].values()[0], v1_file['filename'])
        v1_pkgpath  = os.path.join(V1_DIR_ISO, isos_rel_path)
        v2_pkgpath = os.path.join(DIR_ISOS, isos_rel_path)
        if not os.path.exists(v1_pkgpath):
            # missing source path, skip migrate
            report.warning("ISO file %s does not exist" % v1_pkgpath)
            continue
        try:
            v2_pkg_dir = os.path.dirname(v2_pkgpath)
            os.makedirs(os.path.dirname(v2_pkgpath))
            shutil.move(v1_pkgpath, v2_pkg_dir)
        except (IOError, OSError), e:
            report.error(str(e))
            continue
        except Exception, e:
            report.error("Error: %s" % str(e))
            continue
    if len(report.errors):
        return False
    return True
