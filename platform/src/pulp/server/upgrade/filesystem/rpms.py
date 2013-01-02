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
DIR_RPMS = os.path.join(DIR_STORAGE_ROOT, 'rpm')
DIR_SRPMS = os.path.join(DIR_STORAGE_ROOT, 'srpm')
DIR_DRPM = os.path.join(DIR_STORAGE_ROOT, 'drpm')

V1_DIR_RPMS = '/var/lib/pulp/packages/'

def upgrade(v1_database, v2_database):
    report = UpgradeStepReport()

    rpms_report = _rpms(v1_database, v2_database)
    drpms_report = _drpms(v1_database, v2_database)

    report.success = (rpms_report and drpms_report)
    return report

def _rpms(v1_database, v2_database):
    rpm_coll = v2_database.units_rpm
    all_v1_rpms = v1_database.packages.find({'arch' : {'$ne' : 'src'}})
    for v1_rpm in all_v1_rpms:
        rpm_rel_path =  "%s/%s/%s/%s/%s/%s" % (v1_rpm['name'], v1_rpm['version'], v1_rpm['release'],
                                          v1_rpm['arch'], v1_rpm['checksum'].values()[0], v1_rpm['filename'])
        v1_pkgpath  = os.path.join(V1_DIR_RPMS, rpm_rel_path)
        if v1_rpm['arch'] == 'src':
            v2_pkgpath = os.path.join(DIR_SRPMS, rpm_rel_path)
        else:
            v2_pkgpath = os.path.join(DIR_RPMS, rpm_rel_path)

        if not os.path.exists(v1_pkgpath):
            # missing source path, skip migrate
            print "Package %s does not exist" % v1_pkgpath
            continue
        try:
            v2_pkg_dir = os.path.dirname(v2_pkgpath)
            os.makedirs(os.path.dirname(v2_pkgpath))
            shutil.copy(v1_pkgpath, v2_pkg_dir)
        except Exception, e:
            print "Error: %s" % e
            continue

def _drpms(v1_database, v2_database):

    pass
