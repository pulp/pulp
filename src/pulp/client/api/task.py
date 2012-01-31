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

from pulp.client.api.base import PulpAPI
from pulp.client.api.server import ServerRequestError


def task_end(task):
    if task is None:
        return True
    return task['state'] in ('finished', 'error', 'canceled', 'timed_out')

def task_succeeded(task):
    return task['state'] in ('finished',)


class TaskAPI(PulpAPI):

    def list(self, states=()):
        path = '/tasks/'
        return self.server.GET(path, [('state', s) for s in states])[1]

    def info(self, task_id):
        path = '/tasks/%s/' % task_id
        try:
            return self.server.GET(path)[1]
        except ServerRequestError, e:
            print e.args[1]
        return None

    def remove(self, task_id):
        path = '/tasks/%s/' % task_id
        try:
            return self.server.DELETE(path)[1]
        except ServerRequestError, e:
            print e.args[1]
        return None

    def cancel(self, task_id):
        path = '/tasks/%s/cancel/' % task_id
        try:
            return self.server.POST(path)[1]
        except ServerRequestError, e:
            print e.args[1]
        return None

    def list_snapshots(self):
        path = '/tasks/snapshots/'
        try:
            return self.server.GET(path)[1]
        except ServerRequestError, e:
            print e.args[1]
        return None

    def info_snapshot(self, task_id):
        path = '/tasks/%s/snapshot/' % task_id
        try:
            return self.server.GET(path)[1]
        except ServerRequestError, e:
            print e.args[1]
        return None

    def delete_snapshot(self, task_id):
        path = '/tasks/%s/snapshot/' % task_id
        try:
            return self.server.DELETE(path)[1]
        except ServerRequestError, e:
            print e.args[1]
        return None
