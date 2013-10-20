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
import itertools
import logging
import pickle

from celery import Task as CeleryTask
from celery.app import control
from celery.result import AsyncResult

from pulp.server.db.model.dispatch import CeleryTaskResult
from pulp.server.async.celery_instance import celery

controller = control.Control(app=celery)
inspector= control.Inspect(app=celery)

logger = logging.getLogger(__name__)

class Task(CeleryTask):
    """
    This is a custom Pulp subclass of the Celery Task object. It allows us to inject some custom
    behavior into each Pulp task, including management of resource locking.
    """
    def apply_async_with_reservation(self, resource_id, *args, **kwargs):
        """
        This method allows the caller to schedule the Task to run asynchronously just like Celery's
        apply_async, while also making the named resource. No two tasks that claim the same
        resource reservation can execute concurrently.

        :param resource_id: A string that identifies some named resource, guaranteeing that only one
                            task reserving this same string can happen at a time.
        :type  resource_id: basestring
        :return:            An AsyncResult instance as returned by Celery's apply_async
        :rtype:             celery.result.AsyncResult
        """
        async_result = self.apply_async(*args, **kwargs)
        return async_result


def cancel(task_id):
    """
    Cancel the task that is represented by the given task_id.

    :param task_id: The ID of the task you wish to cancel
    :type  task_id: basestring
    """
    controller.revoke(task_id, terminate=True)

def get_task_details(task_id):
    task_result_collection = CeleryTaskResult.get_collection()
    task_result = task_result_collection.find_one({'_id': task_id})
    serialize_task_result(task_result)
    logger.info("$$$$$$ %s" % task_result)
    logger.info("$$$ %s: %s:  %s" % (task_result['result'],
                                     task_result['traceback'],
                                     task_result['children']))   
    return task_result

def serialize_task_result(task_result):
    task_result['traceback'] = pickle.loads(str(task_result['traceback']))
    task_result['result'] = pickle.loads(str(task_result['result']))
    task_result['children'] = pickle.loads(str(task_result['children']))

def get_active():
    return get_all_task_values(inspector.active())

def get_reserved():
    return get_all_task_values(inspector.reserved())

def get_revoked():
    return get_all_task_values(inspector.revoked())

def get_scheduled():
    return get_all_task_values(inspector.scheduled())

def get_all_task_values(worker_tasks_dict):
    current_tasks = []
    for current_task in worker_tasks_dict.values():
        current_tasks.extend(current_task)
    return current_tasks

def get_current_tasks():
    return itertools.chain(get_active(),
                           get_reserved(),
                           get_revoked(),
                           get_scheduled())
