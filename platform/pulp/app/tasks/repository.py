from celery import shared_task

from pulp.app import models
from pulp.tasking.tasks import UserFacingTask


@shared_task(base=UserFacingTask)
def delete(repo_name):
    """
    Delete a :class:`~pulp.app.models.Repository`

    :param repo_name:       the name of a repository
    :type  repo_name:       str
    """

    models.Repository.objects.filter(name=repo_name).delete()
