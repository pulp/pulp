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

from pulp.server.db.model import Consumer

_log = logging.getLogger('pulp')


version = 15

def migrate():
    _log.info('migration to data model version %d started' % version)
    # update consumer.credentials
    collection = Consumer.get_collection()
    for consumer in collection.find():
        prevkey = 'credentials'
        newkey = 'certificate'
        if newkey not in consumer:
            value = consumer[prevkey]
            if isinstance(value, list):
                consumer[newkey] = ''.join(value)
            del consumer[prevkey]
            collection.save(consumer)
    _log.info('migration to data model version %d complete' % version)
