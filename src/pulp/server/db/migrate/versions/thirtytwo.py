
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
import pulp.server.api.repo as repo_api
from pulp.server.db.model import Repo

_LOG = logging.getLogger('pulp')

version = 32

CONFLICT_MESSAGE = '''
Repository [%s] with relative path [%s] conflicts with repository [%s] with
relative path [%s]. Relative paths may not be a parent or child directory of
another relative path. Please correct the listed repositories.
'''

def migrate():
    _LOG.info('migration to data model version %d started' % version)

    all_repos = list(Repo.get_collection().find())

    for i in range(0, len(all_repos)):
        repo_a = all_repos[i]

        for j in range(i + 1, len(all_repos)):
            repo_b = all_repos[j]

            if not repo_api.validate_relative_path(repo_a['relative_path'], repo_b['relative_path']):
                msg = CONFLICT_MESSAGE % (repo_a['id'], repo_a['relative_path'],
                                          repo_b['id'], repo_b['relative_path'])
                _LOG.warn(msg)
                print(msg)
                return False

    _LOG.info('migration to data model version %d complete' % version)

    return True
