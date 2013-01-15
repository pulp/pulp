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
import yum
from pulp.server.upgrade.model import UpgradeStepReport
from pulp.server.upgrade.utils import PrestoParser

DIR_STORAGE_ROOT = '/var/lib/pulp/content/'
DIR_RPMS = os.path.join(DIR_STORAGE_ROOT, 'rpm')
DIR_SRPMS = os.path.join(DIR_STORAGE_ROOT, 'srpm')
DIR_DRPM = os.path.join(DIR_STORAGE_ROOT, 'drpm')
V1_DIR_RPMS = '/var/lib/pulp/packages/'

def upgrade(v1_database, v2_database):
    report = UpgradeStepReport()

    rpms_success = _rpms(v1_database, v2_database, report)
    drpms_success = _drpms(v1_database, v2_database, report)

    report.success = (rpms_success and drpms_success)
    return report

def _rpms(v1_database, v2_database, report):
    """
    Migrate RPM/SRPM units on filesystem from v1 to v2 database. This assumes that the
    database migration is already complete at this point. The rpm units are migrated
    from v1 location to v2 content location /var/lib/pulp/content/{rpm,srpm}.
    """
    rpm_coll = v2_database.units_rpm
    all_v1_rpms = v1_database.packages.find()
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
            report.warning("Package %s does not exist" % v1_pkgpath)
            continue
        try:
            v2_pkg_dir = os.path.dirname(v2_pkgpath)
            os.makedirs(os.path.dirname(v2_pkgpath))
            shutil.move(v1_pkgpath, v2_pkg_dir)
        except Exception, e:
            report.error("Error: %s" % e)
            return False
    return True

def _drpms(v1_database, v2_database, report):
    """
    Migrate DRPMS from v1 to v2 location on filesystem. DRPMs are not inventoried in the DB in v1.
    This method looks up each repo in v1 for repodata and pretodelta in particular. If availble,
    It parses the presto, extracts the drpm info and finds the drpms in repo dir in v1 and migrates
    then to /var/lib/pulp/content/drpm/ in v1.
    """
    drpm_v2_coll = v2_database.units_drpm
    v1_coll = v1_database.repos
    repos = v1_coll.find()
    for repo in repos:
        deltarpms = PrestoParser.get_deltas(repo)
        for nevra, dpkg in deltarpms.items():
            for drpm in dpkg.deltas.values():
                v2_path = os.path.join(DIR_DRPM, drpm.filename)
                v1_path = repo['repomd_xml_path'].split("repodata/repomd.xml")[0] + drpm.filename
                if not os.path.exists(v1_path):
                    # missing source path, skip migrate
                    report.warning("Package %s does not exist" % v1_path)
                    continue
                try:
                    v2_pkg_dir = os.path.dirname(v2_path)
                    if not os.path.isdir(v2_pkg_dir):
                        os.makedirs(v2_pkg_dir)
                    shutil.move(v1_path, v2_pkg_dir)
                except Exception, e:
                    report.error("Error: %s" % e)
                    return False
    return True
