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
