from celery import shared_task

from pulp.app import models
from pulp.tasking.tasks import UserFacingTask


@shared_task(base=UserFacingTask)
def delete(repo_name, publisher_name):
    """
    Delete a :class:`~pulp.app.models.Publisher`

    :param repo_name:       the name of a repository
    :type  repo_name:       str
    :param publisher_name:  the name of a publisher
    :type  publisher_name:  str
    """
    models.Publisher.objects.filter(name=publisher_name, repository__name=repo_name).delete()
