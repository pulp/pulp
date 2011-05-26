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

_log = logging.getLogger('pulp')

from pulp.server.db.model import Repo

version = 7

def migrate():
    _log.info('migration to data model version %d started' % version)

    new_keys = ['consumer_ca', 'consumer_cert', 'consumer_key']

    collection = Repo.get_collection()
    for repo in collection.find():

        # Add new keys for consumer cert bundle
        for key in new_keys:
            if key not in repo:
                repo[key] = None

        # Change existing cert bundle keys for feed bundle
        if 'cert' in repo:
            repo['feed_cert'] = repo['cert']
            repo.pop('cert')
        else:
            repo['feed_cert'] = None

        if 'key' in repo:
            repo['feed_key'] = repo['key']
            repo.pop('key')
        else:
            repo['feed_key'] = None

        if 'ca' in repo:
            repo['feed_ca'] = repo['ca']
            repo.pop('ca')
        else:
            repo['feed_ca'] = None

        collection.save(repo)

    _log.info('migration to data model version %d complete' % version)
