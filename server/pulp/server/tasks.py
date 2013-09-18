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
from celery import Celery, task, Task as CeleryTask

from pulp.server.config import config
from pulp.server import initialization
from pulp.server.managers.consumer.applicability import ApplicabilityRegenerationManager


broker_url = config.get('tasks', 'broker_url')
celery = Celery('tasks', broker=broker_url)
initialization.initialize()


# This will be our custom task that adds the ability to reserve resources. For now, it is simply
# the Celery task.
class Task(CeleryTask):
    def apply_async_with_reservation(self, resource_id, *args, **kwargs):
        self.apply_async(*args, **kwargs)


@task(base=Task)
def regenerate_applicability_for_consumers(*args, **kwargs):
    return ApplicabilityRegenerationManager.regenerate_applicability_for_consumers(*args, **kwargs)
