from contextlib import suppress
from gettext import gettext as _
import logging

from celery import shared_task

from pulpcore.app import models
from pulpcore.tasking.services import storage
from pulpcore.tasking.tasks import UserFacingTask


log = logging.getLogger(__name__)


@shared_task(base=UserFacingTask)
def sync(importer_pk):
    """
    Call sync on the importer defined by a plugin.

    Check that the importer has a feed_url, which is necessary to sync. A working directory
    is prepared, the plugin's sync is called, and then working directory is removed.

    Args:
        importer_pk (str): The importer PK.

    Raises:
        ValueError: When feed_url is empty.
    """
    importer = models.Importer.objects.get(pk=importer_pk).cast()

    if not importer.feed_url:
        raise ValueError(_("An importer must have a 'feed_url' attribute to sync."))

    new_version = models.RepositoryVersion(repository=importer.repository)
    new_version.save()
    old_version = None
    with suppress(models.RepositoryVersion.DoesNotExist):
        old_version = importer.repository.versions.latest()

    with storage.working_dir_context() as working_dir:
        importer.working_dir = working_dir
        log.info(
            _('Starting sync: repository=%(repository)s importer=%(importer)s'),
            {
                'repository': importer.repository.name,
                'importer': importer.name
            })
        try:
            importer.sync(new_version, old_version)
        except Exception:
            new_version.delete()
            raise

    if new_version.added().count() == 0 and new_version.removed().count() == 0:
        log.debug('no changes; deleting repository version')
        new_version.delete()
