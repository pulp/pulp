from gettext import gettext as _
import os

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
def sync(repo_name, importer_name):
    """
    Call sync on the importer defined by a plugin.

    Check that the importer has a feed_url, which is necessary to sync. A working directory
    is prepared, the plugin's sync is called, and then working directory is removed.

    Args:
        repo_name (basestring): unique name to specify the repository.
        importer_name (basestring): name to specify the Importer.

    Raises:
        ValueError: When feed_url is empty.
    """
    importer = models.Importer.objects.get(name=importer_name, repository__name=repo_name).cast()
    if not importer.feed_url:
        raise ValueError_("An importer must have a 'feed_url' attribute to sync.")

    with storage.working_dir_context() as working_dir:
        importer.working_dir = working_dir
        importer.sync()
