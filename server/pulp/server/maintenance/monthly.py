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
from celery import task

from pulp.common.tags import action_tag
from pulp.server.async.tasks import Task
from pulp.server.db import connection
from pulp.server.managers.consumer.applicability import RepoProfileApplicabilityManager


# This module is generally called from the pulp-monthly script, so let's set up the DB connection
connection.initialize()

@task
def queue_monthly_maintenance():
    """
    Create an itinerary for monthly task
    """
    tags = [action_tag('monthly')]
    monthly_maintenance.apply_async(tags=tags)

@task(base=Task)
def monthly_maintenance():
    """
    Perform tasks that should happen on a monthly basis.
    """
    RepoProfileApplicabilityManager().remove_orphans()
