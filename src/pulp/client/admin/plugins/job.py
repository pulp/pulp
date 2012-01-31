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

import os
from gettext import gettext as _

from pulp.client.admin.plugin import AdminPlugin
from pulp.client.api.job import JobAPI
from pulp.client.api.task import task_end
from pulp.client.lib.utils import system_exit
from pulp.client.pluginlib.command import Action, Command


JOB = """
Job:      %s
Finished: %s%%
Tasks     (%d):"""

CANCEL = """
Job: %s
Completed: %d
%s
Cancelled: %d
%s"""

TASK = """
\tTask:      %s
\tState:     %s
\tScheduled: %s
"""

TASK_LONG = """
\tTask:      %s
\tState:     %s
\tScheduled: %s
\tStarted:   %s
\tFinished:  %s
\tResult:    %s
\tException: %s
"""

# job actions -----------------------------------------------------------------

class JobAction(Action):

    def setup_parser(self):
        self.parser.add_option('--id', dest='id', help=_('job id'))


class ListAction(JobAction):

    def setup_parser(self):
        self.parser.add_option('--id', dest='id', help=_('job id'))

    def job(self, job):
        s = []
        id = job['id']
        tasks = job['tasks']
        s.append(JOB % (id, self.pct(tasks), len(tasks)))
        for t in tasks:
            s.append(self.task(t))
        return ''.join(s)

    def pct(self, tasks):
        total = len(tasks)
        if total < 1:
            return 0
        ended = 0
        for t in tasks:
            if task_end(t):
                ended += 1
        f = (ended/float(total))
        return int(f*100)


class List(ListAction):

    name = "list"
    description = _('list jobs currently in the tasking system')

    def run(self):
        japi = JobAPI()
        jobs = japi.list()
        if not jobs:
            system_exit(os.EX_OK, _('No jobs found'))
        for j in jobs:
            print self.job(j)
            
    def job(self, job):
        s = []
        id = job['id']
        tasks = job['tasks']
        s.append(JOB % (id, self.pct(tasks), len(tasks)))
        for t in tasks:
            s.append(self.task(t))
        return ''.join(s)
            
    def task(self, task):
        return TASK % \
            (task['id'],
             task['state'].upper(),
             task['scheduled_time'],)


class Info(ListAction):

    name = "info"
    description = _('show information for a job')

    def run(self):
        japi = JobAPI()
        id = self.get_required_option('id')
        job = japi.info(id)
        if not job:
            system_exit(os.EX_OK)
        print self.job(job)
        
    def task(self, task):
        return TASK_LONG % \
            (task['id'],
             task['state'].upper(),
             task['scheduled_time'],
             task['start_time'],
             task['finish_time'],
             task['result'],
             task['exception'],)


class Cancel(JobAction):
    
    name = "cancel"
    description = _('cancel a job')

    def run(self):
        japi = JobAPI()
        id = self.get_required_option('id')
        cancel = japi.cancel(id)
        if not cancel:
            system_exit(os.EX_OK)
        id = cancel['id']
        completed = []
        for t in cancel['completed']:
            completed.append(self.task(t))
        cancelled = []
        for t in cancel['cancelled']:
            cancelled.append(self.task(t))
        print CANCEL % (
            id,
            len(completed),
            ''.join(completed),
            len(cancelled),
            ''.join(cancelled))
        
    def task(self, task):
        return TASK % \
            (task['id'],
             task['state'].upper(),
             task['scheduled_time'],)
    

# job command -----------------------------------------------------------------

class Job(Command):

    name = "job"
    description = _('pulp server job administration and debugging')
    actions = [ List,
                Info,
                Cancel ]

# job plugin -----------------------------------------------------------------

class JobPlugin(AdminPlugin):

    name = "job"
    commands = [ Job ]
    CONFIG_FILE = "job.conf"
