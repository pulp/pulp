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
import sys
from pulp.server.db.model import Repo
_log = logging.getLogger('pulp')

version = 25

DUPLICATE_WARNING_MSG = """WARNING: Your database has multiple repos with the same relative path.
This is a deprecated functionality and will not be supported in upcoming versions of pulp.
Please remove the following set(s) of repoids from your pulp server %s\n\n"""

def _warning_repo_relativepath():
    collection = Repo.get_collection()
    relpath_repo_map = {}
    for repo in collection.find():
        if not repo['relative_path']:
            continue
        rpath = repo['relative_path'].strip()
        if not relpath_repo_map.has_key(rpath):
            relpath_repo_map[rpath] = []
        relpath_repo_map[rpath].append(str(repo['id']))
    dup_repos = []
    for relpath, repoids in relpath_repo_map.items():
        if len(repoids) > 1:
            dup_repos.append(tuple(repoids))
    if not dup_repos:
        # no duplicates found, db is clean
        return
    sys.stderr.write(DUPLICATE_WARNING_MSG % dup_repos)


def migrate():
    # this is only a db content validation rather migration; no change to db model itself
    _log.info('validation on previous data model version started')
    _warning_repo_relativepath()
    _log.info('validation complete; data model at version %d' % version)