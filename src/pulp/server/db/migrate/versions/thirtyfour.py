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


# This is an example migration module.
# Each migration module must implement the following members:
# 1. version - integer representing the version the module migrates to
# 2. migrate() - function with no arguments that performs the migration

import logging

from pulp.server.db.model.resource import ConsumerHistoryEvent


_log = logging.getLogger('pulp')

version = 34


def _migrate_consumer_history():
    collection = ConsumerHistoryEvent.get_collection()
    collection.update({'type_name': 'consumer_created'}, 
        {'$set': {'type_name': 'consumer_registered'}}, 
        safe=True, multi=True)
    collection.update({'type_name': 'consumer_deleted'}, 
        {'$set': {'type_name': 'consumer_unregistered'}}, 
        safe=True, multi=True)


def migrate():
    _log.info('migration to data model version %d started' % version)
    _migrate_consumer_history()
    _log.info('migration to data model version %d complete' % version)
