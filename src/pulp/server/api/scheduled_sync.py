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


from pulp.server import async
from pulp.server.api.repo_sync import RepoSyncTask
from pulp.server.db.model.resource import Repo, RepoSyncSchedule
from pulp.server.tasking.scheduler import IntervalScheduler

# existing api ----------------------------------------------------------------

def update_schedule(repo, new_schedule):
    pass


def delete_schedule(repo):
    pass

# startup initialization ------------------------------------------------------

def init_scheduled_syncs():
    pass
