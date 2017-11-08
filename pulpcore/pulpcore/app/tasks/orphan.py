from celery import shared_task

from pulpcore.app import models
from pulpcore.tasking.tasks import UserFacingTask


@shared_task(base=UserFacingTask)
def delete_all():
    """
    Delete all orphan content.
    This task removes content from the filesystem as well.
    """
    models.Content.objects.filter(repositories=None).delete()
