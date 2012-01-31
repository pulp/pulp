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
from pulp.client.api.task import task_end, task_succeeded


def job_end(job):
    for task in job['tasks']:
        if not task_end(task):
            return False
    return True

def job_succeeded(job):
    for task in job['tasks']:
        if not task_succeeded(task):
            return False
    return True


class JobAPI(PulpAPI):

    def list(self):
        path = '/jobs/'
        return self.server.GET(path)[1]

    def info(self, job_id):
        path = '/jobs/%s/' % job_id
        try:
            return self.server.GET(path)[1]
        except ServerRequestError, e:
            print e.args[1]
        return None
    
    def cancel(self, job_id):
        path = '/jobs/%s/cancel/' % job_id
        try:
            return self.server.POST(path)[1]
        except ServerRequestError, e:
            print e.args[1]
        return None
