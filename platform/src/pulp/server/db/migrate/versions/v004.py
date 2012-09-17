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

from pulp.server.db.model.auth import Role

_log = logging.getLogger('pulp')

special_roles = ['super-users', 'consumer-users']

version = 4


def _migrate_role_id_display_name():
    collection = Role.get_collection()
    for role in collection.find():
        modified = False
        if 'display_name' not in role:
            if role['name'] in special_roles:
                collection.remove({'name':role['name']}, safe=True)
            else:
                role['id'] = role['display_name'] = role['name'] 
                del role['name']
                modified = True
        if modified:
            collection.save(role, safe=True)
            

def _migrate_role_description():
    collection = Role.get_collection()
    for role in collection.find():
        if 'description' not in role:
            role['description'] = None
        collection.save(role, safe=True)

def migrate():
    _log.info('migration to data model version %d started' % version)
    _migrate_role_id_display_name()
    _migrate_role_description()
    _log.info('migration to data model version %d complete' % version)

