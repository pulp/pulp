from datetime import datetime
from gettext import gettext as _
from logging import getLogger

from celery import shared_task
from django.db import transaction

from pulpcore.app import models
from pulpcore.tasking.services import storage
from pulpcore.tasking.tasks import UserFacingTask


log = getLogger(__name__)


@shared_task(base=UserFacingTask)
def publish(publisher_pk):
    """
    Call publish on the publisher defined by a plugin.

    A working directory is prepared, the plugin's publish is called, and then
    working directory is removed.

    Args:
        publisher_pk (str): The publisher PK.
    """
    publisher = models.Publisher.objects.get(pk=publisher_pk).cast()

    log.info(
        _('Publishing: repository=%(repository)s, publisher=%(publisher)s'),
        {
            'repository': publisher.repository.name,
            'publisher': publisher.name
        })

    with transaction.atomic():
        publication = models.Publication(publisher=publisher)
        publisher.publication = publication
        publication.save()
        created = models.CreatedResource(content_object=publication)
        created.save()
        with storage.working_dir_context() as working_dir:
                publisher.working_dir = working_dir
                publisher.publish()
                publisher.last_published = datetime.utcnow()
                publisher.save()
                distributions = models.Distribution.objects.filter(publisher=publisher)
                distributions.update(publication=publication)

    log.info(
        _('Publication: %(publication)s created'),
        {
            'publication': publication.pk
        })
