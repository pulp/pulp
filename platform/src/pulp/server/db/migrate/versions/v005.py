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

from pulp.server.db.model.auth import Permission

_log = logging.getLogger('pulp')

version = 5

def _migrate_permissions():
    collection = Permission.get_collection()
    for permission in collection.find():
        if not isinstance (permission['resource'], basestring):
            collection.remove({'resource':permission['resource']}, safe=True)


def migrate():
    _log.info('migration to data model version %d started' % version)
    _migrate_permissions()
    _log.info('migration to data model version %d complete' % version)

