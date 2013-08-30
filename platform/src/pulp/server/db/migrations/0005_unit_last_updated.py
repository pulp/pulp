# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from pulp.server.db import connection
from pulp.plugins.types.database import TYPE_COLLECTION_PREFIX


LAST_UPDATED = '_last_updated'
QUERY = {LAST_UPDATED: {'$exists': False}}
NEVER = 0.0


def migrate(*args, **kwargs):
    """
    Ensure all content units have the _last_updated attribute.
    """
    database = connection.get_database()
    for name in database.collection_names():
        if not name.startswith(TYPE_COLLECTION_PREFIX):
            continue
        collection = connection.get_collection(name)
        for unit in collection.find(QUERY):
            unit[LAST_UPDATED] = NEVER
            collection.save(unit, safe=True)
