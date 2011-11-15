
# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
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
from pulp.server.db.model import Distribution
from pulp.server.api.synchronizers import parse_treeinfo
import pulp.server.util as pulputil
_log = logging.getLogger('pulp')

version = 29

def _migrate_distribution():
    collection = Distribution.get_collection()
    for distro in collection.find({}):
        treecfg = None
        for tree_info_name in ['treeinfo', '.treeinfo']:
            treecfg = "%s/%s" % (distro['relativepath'], tree_info_name )
            if os.path.exists(treecfg):
                break
        treeinfo = parse_treeinfo(treecfg)
        if not treeinfo:
            distro['arch'] = None
            continue
        distro['arch'] = treeinfo['arch']
        collection.save(distro, safe=True)

def migrate():
    # There's a bit of the chicken and the egg problem here, since versioning
    # wasn't built into pulp from the beginning, we just have to bite the
    # bullet and call some initial state of the data model 'version 1'.
    # So this function is essentially a no-op.
    _log.info('migration to data model version %d started' % version)
    _migrate_distribution()
    _log.info('migration to data model version %d complete' % version)
