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
from pulp.server.db.model.persistence import TaskHistory, TaskSnapshot
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
        valid_states = ('waiting', 'running', 'complete', 'incomplete')
        filters = self.filters(valid_filters)
        states = [s.lower() for s in filters.pop('state', [])]
        tasks = set()
        if not states:
            tasks.add(async.all_async())
        if 'waiting' in states:
            tasks.add(async.waiting_async())
        if 'running' in states:
            tasks.add(async.running_async())
        if 'complete' in states:
            tasks.add(async.complete_async())
        if 'incomplete' in states:
            tasks.add(async.incomplete_async())
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
        return self.ok(self._task_to_dict(tasks[0]))

    @JSONController.error_handler
    @JSONController.auth_required(super_user_only=True)
    def DELETE(self, id):
        """
        [[wiki]]
        """
        tasks = async.find_async(id=id)
        if not tasks:
            return self.not_found(_('Task not found: %s') % id)
        async.cancel_async(tasks[0])
        return self.accepted(_('Task set to be canceled: %s') % id)
