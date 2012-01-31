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
 * id, str, unique id (usually a uuid) for the task
 * job_id, str, associate job id
 * class_name, str, name of the class, if the task's method is an instance method
 * method_name, str, name of the pulp library method that was called
 * state, str, one of several valid states of the tasks lifetime: waiting, running, finished, error, timed_out, canceled, reset, suspended
 * start_time, str or nil, time the task started running in iso8601 format, nil if the task has not yet started
 * finish_time,  or nil, time the task finished running in iso8601 format, nil if the task has not yet finished
 * result, object or nil, the result of the pulp library method upon return, usually nil
 * exception, str or nil, a string representation of an error in the pulp librry call, if any
 * traceback, str or nil, a string print out of the trace back for the exception, if any
 * progress, object or nil, object representing the pulp library call's progress, nill if no information is available
 * scheduled_time, str or nil, time the task is scheduled to run in iso8601 format, applicable only for scheduled tasks
 * snapshot_id, str, id of task's snapshot, if it has one
TaskSnapshot object fields:
 * id, str, unique task id
 * class_name, str, name of the class, if the task's method is an instance method
 * method_name, str, name of the pulp library method that was called
 * state, str, one of several valid states of the tasks lifetime: waiting, running, finished, error, timed_out, canceled, reset, suspended
 * failure_threshold, int, number of failures allowed this task before it is no longer scheduled
 * cancel_attempts, int, the number of times cancel was called on this task
 * callable, str, pickled task method
 * args, str, pickled arguments for the task method
 * kwargs, str, picked keyword arguments for the task method
 * progress, object or nil, object representing the pulp library call's progress, nill if no information is available
 * timeout, str, pickled timedelta representing the time limit for the task's run
 * schedule_threshold, str, pickled timedelta representing a max difference between the scheduled_time and start_time before an error is logged
 * _progress_callback, str, pickled method allowing progress information to be recorded by the task
 * start_time, str, pickled datetime showing the start time of the task
 * finish_time, str, pickled datetime showing the finish time of the task
 * result, str, pickled result of the task call
 * exception, str, pickled error, if one occurred
 * traceback, str, pickled traceback, if one occured
"""

import web
from gettext import gettext as _

import pymongo

from pulp.server import async
from pulp.server.api import task_history
from pulp.server.db.model.persistence import TaskSnapshot, TaskHistory
from pulp.server.auth.authorization import READ, UPDATE
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import (
    auth_required, error_handler)

# tasks controller -------------------------------------------------------------

class Tasks(JSONController):

    @error_handler
    @auth_required(READ)
    def GET(self):
        """
        [[wiki]]
        title: Get All Tasks
        description: Get a list of all tasks currently in the tasking system
        method: GET
        path: /tasks/
        permission: READ
        success response: 200 OK
        failure response: None
        return: list of task objects
        filters:
         * id, str, task id
         * state, str, tasking system task state: waiting, running, complete, incomplete, current, archived (current is the same as waiting, running, complete, and incomplete, also the same as omitting the state filter; archived looks into the the task history, will not return archived tasks without this filter)
        """
        def _archived(ids):
            collection = TaskHistory.get_collection()
            query_doc = {}
            if ids:
                query_doc['id'] = {'$in': ids}
            cursor = collection.find(query_doc)
            cursor.sort('finish_time', pymongo.DESCENDING)
            archived_tasks = [dict(t) for t in cursor]
            return archived_tasks

        def _serialize(t):
            d = self._task_to_dict(t)
            d['snapshot_id'] = t.snapshot_id
            return d

        valid_filters = ('id', 'state',)
        valid_states = ('waiting', 'running', 'complete', 'incomplete', 'current', 'archived')
        filters = self.filters(valid_filters)
        ids = filters.pop('id', [])
        states = [s.lower() for s in filters.pop('state', [])]
        for s in states:
            if s in valid_states:
                continue
            return self.bad_request(_('Unknown state: %s') % s)
        tasks = set()
        if not states or 'current' in states:
            tasks.update(async.all_async())
        if 'waiting' in states:
            tasks.update(async.waiting_async())
        if 'running' in states:
            tasks.update(async.running_async())
        if 'complete' in states:
            tasks.update(async.complete_async())
        if 'incomplete' in states:
            tasks.update(async.incomplete_async())
        if ids:
            tasks = [t for t in tasks if t.id in ids]
        serialized_tasks = [_serialize(t) for t in tasks]
        if 'archived' in states:
            archived_tasks = _archived(ids)
            serialized_tasks.extend(archived_tasks)
        return self.ok(serialized_tasks)

# task controller --------------------------------------------------------------

class Task(JSONController):

    @error_handler
    @auth_required(READ)
    def GET(self, id):
        """
        [[wiki]]
        title: Get A Task
        description: Get a Task object for a specific task
        method: GET
        path: /tasks/<id>/
        permission: READ
        success response: 200 OK
        failure response: 404 Not Found if no such task
        return: Task object
        """
        tasks = self.active(id)
        if not tasks:
            tasks = self.history(id)
        if not tasks:
            return self.not_found(_('Task not found: %s') % id)
        return self.ok(tasks[0])

    def active(self, id):
        tasks = []
        for task in async.find_async(id=id):
            task_dict = self._task_to_dict(task)
            task_dict['snapshot_id'] = task.snapshot_id
            tasks.append(task_dict)
        return tasks

    def history(self, id):
        tasks = []
        for task in task_history.task(id):
            task['scheduler'] = None
            task['snapshot_id'] = None
            tasks.append(task)
        return tasks


    @error_handler
    @auth_required(super_user_only=True)
    def DELETE(self, id):
        """
        [[wiki]]
        title: Remove A Task
        description: Remove a task from the tasking sub-system. This does not interrupt the task if it is running
        method: DELETE
        path: /tasks/<id>/
        permission: Super User Only
        success response: 202 Accepted
        failure response: 404 Not Found if no such task
        return: Task object
        """
        tasks = async.find_async(id=id)
        if not tasks:
            return self.not_found(_('Task not found: %s') % id)
        task = tasks[0]
        async.remove_async(task)
        return self.accepted(self._task_to_dict(task))

# task cancelation controller --------------------------------------------------

class CancelTask(JSONController):

    @error_handler
    @auth_required(UPDATE)
    def POST(self, id):
        """
        [[wiki]]
        title: Cancel A Task
        description: Cancel a waiting or running task.
        method: POST
        path: /tasks/<id>/cancel/
        permission: UPDATE
        success response: 202 Accepted
        failure response: 404 Not Found
        return: Task object
        """
        tasks = async.find_async(id=id)
        if not tasks:
            return self.not_found(_('Task not found: %s') % id)
        task = tasks[0]
        async.cancel_async(task)
        return self.accepted(self._task_to_dict(task))

# snapshots controller ---------------------------------------------------------

class Snapshots(JSONController):

    @error_handler
    @auth_required(super_user_only=True)
    def GET(self):
        """
        [[wiki]]
        title: Get All Task Snapshots
        description: Get a list of all task snapshots currently in the system
        method: GET
        path: /tasks/snapshots/
        permission: Super User Only
        success response: 200 OK
        failure response: None
        return: a list of !TaskSnapshot objects
        """
        collection = TaskSnapshot.get_collection()
        snapshots = list(collection.find())
        return self.ok(snapshots)

# snapshot controller ----------------------------------------------------------

class Snapshot(JSONController):

    @error_handler
    @auth_required(super_user_only=True)
    def GET(self, id):
        """
        [[wiki]]
        title: Get A Task Snapshot
        description: Get a !TaskSnapshot object for the give task
        method: GET
        path: /tasks/<id>/snapshot/
        permission: Super User Only
        success response: 200 OK
        failure response: 404 Not Found if no snapshot exists for the given task
        return: !TaskSnapshot object
        """
        collection = TaskSnapshot.get_collection()
        snapshot = collection.find_one({'id': id})
        if snapshot is None:
            return self.not_found(_('Snapshot for task not found: %s') % id)
        return self.ok(snapshot)

    @error_handler
    @auth_required(super_user_only=True)
    def DELETE(self, id):
        """
        [[wiki]]
        title: Delete A Task Snapshot
        description: Delete the snapshot for a given task
        method: DELETE
        path: /tasks/<id>/snapshot/
        permission: Super User Only
        success response: 200 OK
        failure response: 404 Not Found if no snapshot exists for the given task
        return: !TaskSnapshot object
        """
        collection = TaskSnapshot.get_collection()
        snapshot = collection.find_one({'id': id})
        if snapshot is None:
            return self.not_found(_('Snapshot for task not found: %s') % id)
        collection.remove({'id': id}, safe=True)
        return self.ok(snapshot)

# web.py application -----------------------------------------------------------

_urls = (
    '/$', Tasks,
    '/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/$', Task,
    '/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/cancel/$', CancelTask,
    '/snapshots/$', Snapshots,
    '/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/snapshot/$', Snapshot,
)

application = web.application(_urls, globals())
