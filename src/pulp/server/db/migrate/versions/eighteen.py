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

from pulp.server.db.model import Consumer, Repo

_log = logging.getLogger('pulp')


version = 18

def migrate():
    _log.info('migration to data model version %d started' % version)
    _migrate_consumers()
    _migrate_repos()
    _log.info('migration to data model version %d complete' % version)
    
def _migrate_consumers():
    #
    # consolidate credentials key and certificate
    # and rename to: certificate.
    #
    collection = Consumer.get_collection()
    for consumer in collection.find():
        PREV = 'credentials'
        NEW = 'certificate'
        if NEW not in consumer:
            value = consumer[PREV]
            if isinstance(value, list):
                consumer[NEW] = ''.join(value)
            del consumer[PREV]
            collection.save(consumer)

def _migrate_repos():
    #
    # update repo: consolidate key & certificate and
    # remove key attributes.
    #
    collection = Repo.get_collection()
    for repo in collection.find():
        for type in ('feed', 'consumer'):
            KEY = '%s_key' % type
            if KEY not in repo:
                continue
            CERT = '%s_cert' % type
            key = repo.get(KEY)
            crt = repo.get(CERT)
            if key and crt:
                repo[CERT] = ''.join((key, crt))
            del repo[KEY]
