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
from celery import Task as CeleryTask
from celery.app import control

from pulp.server.async.celery_instance import celery


controller = control.Control(app=celery)


class Task(CeleryTask):
    """
    This is a custom Pulp subclass of the Celery Task object. It allows us to inject some custom
    behavior into each Pulp task, including management of resource locking.
    """
    def apply_async(self, *args, **kwargs):
        """
        A wrapper around the Celery apply_async method. It allows us to accept a few more
        parameters than Celery does for our own purposes, listed below.

        :param tags:        A list of tags (strings) to place onto the task, used for searching for
                            tasks by tag
        :type  tags:        list
        :return:            An AsyncResult instance as returned by Celery's apply_async
        :rtype:             celery.result.AsyncResult
        """
        tags = kwargs.pop('tags', [])

        return super(Task, self).apply_async(*args, **kwargs)

    def apply_async_with_reservation(self, resource_id, *args, **kwargs):
        """
        This method allows the caller to schedule the Task to run asynchronously just like Celery's
        apply_async, while also making the named resource. No two tasks that claim the same
        resource reservation can execute concurrently.

        For a list of parameters accepted by the *args and **kwargs parameters, please see the
        docblock for the apply_async() method.

        :param resource_id: A string that identifies some named resource, guaranteeing that only one
                            task reserving this same string can happen at a time.
        :type  resource_id: basestring
        :param tags:        A list of tags (strings) to place onto the task, used for searching for
                            tasks by tag
        :type  tags:        list
        :return:            An AsyncResult instance as returned by Celery's apply_async
        :rtype:             celery.result.AsyncResult
        """
        return self.apply_async(*args, **kwargs)


def cancel(task_id):
    """
    Cancel the task that is represented by the given task_id.

    :param task_id: The ID of the task you wish to cancel
    :type  task_id: basestring
    """
    controller.revoke(task_id, terminate=True)
