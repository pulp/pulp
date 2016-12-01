from celery import task

from pulp.common.tags import action_tag
from pulp.server.managers.consumer.applicability import RepoProfileApplicabilityManager

from pulp.tasking.tasks import PulpTask, UserFacingTask


@task(base=PulpTask)
def queue_monthly_maintenance():
    """
    Create an itinerary for monthly task
    """
    tags = [action_tag('monthly')]
    monthly_maintenance.apply_async(tags=tags)


@task(base=UserFacingTask)
def monthly_maintenance():
    """
    Perform tasks that should happen on a monthly basis.
    """
    RepoProfileApplicabilityManager().remove_orphans()
