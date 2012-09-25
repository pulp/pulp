# -*- coding: utf-8 -*-

# Copyright © 2010-2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.


import logging
import os
from createrepo import yumbased

import rpmUtils

from pulp.server.managers.content.query import ContentQueryManager

_log = logging.getLogger('pulp')

version = 5


def _migrate_rpm_unit_repodata():
    """
    Looks up rpm unit collection in the db and computes the repodata if nto already available;
    If the package path is missing, the repodata if stored as an empty dict.
    """
    query_manager = ContentQueryManager()
    collection = query_manager.get_content_unit_collection(type_id="rpm")
    for rpm_unit in collection.find():
        modified = False
        if "repodata" not in rpm_unit:
            rpm_unit["repodata"] = get_package_xml(rpm_unit['_storage_path'])
            modified = True
        if modified:
            collection.save(rpm_unit, safe=True)


def get_package_xml(pkg_path):
    """
    Method to generate repo xmls - primary, filelists and other
    for a given rpm.

    @param pkg_path: rpm package path on the filesystem
    @type pkg_path: str

    @return rpm metadata dictionary or empty if rpm path doesnt exist
    @rtype {}
    """
    if not os.path.exists(pkg_path):
        _LOG.debug("Package path %s does not exist" % pkg_path)
        return {}
    ts = rpmUtils.transaction.initReadOnlyTransaction()
    po = yumbased.CreateRepoPackage(ts, pkg_path)
    # RHEL6 createrepo throws a ValueError if _cachedir is not set
    po._cachedir = None
    metadata = {'primary' : po.xml_dump_primary_metadata(),
                'filelists': po.xml_dump_filelists_metadata(),
                'other'   : po.xml_dump_other_metadata(),
                }
    return metadata

def migrate():
    _log.info('migration to data model version %d started' % version)
    _migrate_rpm_unit_repodata()
    _log.info('migration to data model version %d complete' % version)

migrate()