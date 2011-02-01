# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

import logging

from pulp.server.api.repo import RepoApi
from pulp.server.api.user import UserApi
from pulp.server.api.consumer import ConsumerApi


_log = logging.getLogger('pulp')

# migration module conventions ------------------------------------------------

version = 2

def _migrate_repo_model():
    api = RepoApi()
    for repo in api._getcollection().find():
        modified = False
        if 'package_count' not in repo:
            repo['package_count'] = len(repo['packages'])
            modified = True
        if 'distributionid' not in repo:
            repo['distributionid'] = []
            modified = True
        if not isinstance(repo['packages'], list):
            repo['packages'] = [pkg_id for pkg_id in repo['packages']]
            modified = True
        if modified:
            api.update(repo)

def _migrate_user_model():
    api = UserApi()
    for user in api._getcollection().find():
        if 'roles' not in user or \
           not isinstance(user['roles'], list):
            user['roles'] = []
            api.update(user)

def _migrate_consumer_model():
    api = ConsumerApi()
    for consumer in api._getcollection().find():
        key = 'credentials'
        if key not in consumer:
            consumer[key] = None
            api.update(consumer)

def migrate():
    _log.info('migration to data model version 2 started')
    _migrate_repo_model()
    _migrate_user_model()
    _migrate_consumer_model()
    _log.info('migration to data model version 2 complete')
