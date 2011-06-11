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

"""
[[wiki]]
title: Tasking RESTful Interface
description: RESTful interface providing an administrative and debugging api for
             pulp's tasking system.
Task object fields:
 *
TaskSnapshot object fields:
 *
"""

import web
from gettext import gettext as _

from pulp.server import async
from pulp.server.db.model.persistence import TaskSnapshot
from pulp.server.webservices.controllers.base import JSONController, AsyncController

# tasks controller -------------------------------------------------------------

class Tasks(AsyncController):

    @JSONController.error_handler
    @JSONController.auth_required(super_user_only=True)
    def GET(self):
        """
        [[wiki]]
        """
        def _serialize(t):
            d = self._task_to_dict(t)
            d['snapshot_id'] = t.snapshot_id
            return d

        valid_filters = ('state',)
        valid_states = ('waiting', 'running', 'complete', 'incomplete', 'all')
        filters = self.filters(valid_filters)
        states = [s.lower() for s in filters.pop('state', [])]
        for s in states:
            if s in valid_states:
                continue
            return self.bad_request(_('Unknown state: %s') % s)
        tasks = set()
        if not states or 'all' in states:
            tasks.update(async.all_async())
        if 'waiting' in states:
            tasks.update(async.waiting_async())
        if 'running' in states:
            tasks.update(async.running_async())
        if 'complete' in states:
            tasks.update(async.complete_async())
        if 'incomplete' in states:
            tasks.update(async.incomplete_async())
        return self.ok([_serialize(t) for t in tasks])

# task controller --------------------------------------------------------------

class Task(AsyncController):

    @JSONController.error_handler
    @JSONController.auth_required(super_user_only=True)
    def GET(self, id):
        """
        [[wiki]]
        """
        tasks = async.find_async(id=id)
        if not tasks:
            return self.not_found(_('Task not found: %s') % id)
        task_dict = self._task_to_dict(tasks[0])
        task_dict['snapshot_id'] = task.snapshot_id
        return self.ok(task_dict)

    @JSONController.error_handler
    @JSONController.auth_required(super_user_only=True)
    def DELETE(self, id):
        """
        [[wiki]]
        """
        tasks = async.find_async(id=id)
        if not tasks:
            return self.not_found(_('Task not found: %s') % id)
        async.remove_async(tasks[0])
        return self.accepted(_('Task set to be removed: %s') % id)

# snapshots controller ---------------------------------------------------------

class Snapshots(JSONController):

    @JSONController.error_handler
    @JSONController.auth_required(super_user_only=True)
    def GET(self):
        collection = TaskSnapshot.get_collection()
        snapshots = list(collection.find())
        return self.ok(snapshots)

# snapshot controller ----------------------------------------------------------

class Snapshot(JSONController):

    @JSONController.error_handler
    @JSONController.auth_required(super_user_only=True)
    def GET(self, id):
        collection = TaskSnapshot.get_collection()
        snapshot = collection.find_one({'id': id})
        if snapshot is None:
            return self.not_found(_('Snapshot for task not found: %s') % id)
        return self.ok(snapshot)

    @JSONController.error_handler
    @JSONController.auth_required(super_user_only=True)
    def DELETE(self, id):
        collection = TaskSnapshot.get_collection()
        snapshot = collection.find_one({'id': id})
        if snapshot is None:
            return self.not_found(_('Snapshot for task not found: %s') % id)
        collection.remove({'id': id}, safe=True)
        return self.ok(snapshot)

# web.py application -----------------------------------------------------------

_urls = (
    '/$', Tasks,
    '/(?[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/$', Task,
    '/snapshots/$', Snapshots,
    '/(?[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/snapshot/$', Snapshot,
)

application = web.application(_urls, globals())
