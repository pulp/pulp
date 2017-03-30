from celery import shared_task

from pulp.app import models
from pulp.tasking.services import storage
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


@shared_task(base=UserFacingTask)
def sync(importer_name):
    """
    Call sync on the specified importer.

    Args:
        importer_name (basestring): unique name to specify the Importer
    """
    importer = models.Importer.objects.get(name=importer_name).cast()
    importer.working_dir = storage.get_working_directory()
    importer.sync()
