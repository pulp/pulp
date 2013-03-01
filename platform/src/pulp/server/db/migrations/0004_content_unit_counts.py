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

from pulp.server.db.model.repository import Repo
from pulp.server.managers.repo.cud import RepoManager


def migrate(*args, **kwargs):
    """
    Regenerates the 'content_unit_counts' attribute of each repository, and
    removes the obsolete attribute 'content_unit_count'. The normal use case
    will be that the 'content_unit_counts' attribute does not yet exist, but
    this migration is idempotent just in case.
    """
    RepoManager().rebuild_content_unit_counts()
    repo_collection = Repo.get_collection()
    repo_collection.update({}, {'$unset': {'content_unit_count': 1}}, safe=True)
