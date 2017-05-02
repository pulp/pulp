from celery import shared_task

from pulp.app import models
from pulp.tasking.tasks import UserFacingTask


@shared_task(base=UserFacingTask)
def delete(repo_name, importer_name):
    """
    Delete an :class:`~pulp.app.models.Importer`

    :param repo_name:       the name of a repository
    :type  repo_name:       str
    :param importer_name:   the name of an importer
    :type  importer_name:   str
    """
    models.Importer.objects.filter(name=importer_name, repository__name=repo_name).delete()
