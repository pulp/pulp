# -*- coding: utf-8 -*-

# Copyright © 2010-2011 Red Hat, Inc.
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
from gettext import gettext as _
import os

from pulp.server.db.model import Package
import pulp.server.util

_log = logging.getLogger('pulp')


def _migrate_packages():
    collection = Package.get_collection()
    for pkg in collection.find({}):
        modified = False
        pkg_path = pulp.server.util.get_shared_package_path(pkg['name'], pkg['version'], pkg['release'], \
                                                            pkg['arch'], pkg['filename'], pkg['checksum'].values()[0])
        if os.path.exists(pkg_path):
            header = pulp.server.util.get_rpm_information(pkg_path)
        else:
            header = dict(size=None, buildhost=None, license=None, group=None)
        _log.info("Processing pkg header:: %s" % header)
        if 'size' not in pkg:
            pkg['size'] = header['size']
            modified = True
        if 'buildhost' not in pkg:
            pkg['buildhost'] = header['buildhost']
            modified = True
        if 'license' not in pkg:
            pkg['license'] = header['license']
            modified = True
        if 'group' not in pkg:
            pkg['group'] = header['group']
            modified = True
        _log.info(_('updating details for package %s') % pkg['id'])
        if modified:
            collection.save(pkg, safe=True)


version = 11

def migrate():
    # There's a bit of the chicken and the egg problem here, since versioning
    # wasn't built into pulp from the beginning, we just have to bite the
    # bullet and call some initial state of the data model 'version 1'.
    # So this function is essentially a no-op.
    _log.info('migration to data model version %d started' % version)
    _migrate_packages()
    _log.info('migration to data model version %d complete' % version)
