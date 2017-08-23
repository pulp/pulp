from datetime import datetime
from gettext import gettext as _
from logging import getLogger

from celery import shared_task
from django.db import transaction
from django.http import QueryDict

from pulpcore.app import models
from pulpcore.app.apps import get_plugin_config
from pulpcore.tasking.services import storage
from pulpcore.tasking.tasks import UserFacingTask


log = getLogger(__name__)


@shared_task(base=UserFacingTask)
def update(publisher_id, app_label, serializer_name, data=None, partial=False):
    """
    Update an instance of a :class:`~pulpcore.app.models.Publisher`

    Args:
        publisher_id (str): id of the publisher instance
        app_label (str): the Django app label of the plugin that provides the publisher
        serializer_name (str): name of the serializer class for this publisher
        data (dict): Data to update on the publisher. keys are field names, values are new values.
        partial (bool): When true, update only the specified fields. When false, omitted fields
            are set to None.
    Raises:
        :class:`rest_framework.exceptions.ValidationError`: When serializer instance can't be saved
            due to validation error. This theoretically should never occur since validation is
            performed before the task is dispatched.
    """
    instance = models.Publisher.objects.get(id=publisher_id).cast()
    data_querydict = QueryDict("", mutable=True)
    data_querydict.update(data)
    # The publisher serializer class is different for each plugin
    serializer_class = get_plugin_config(app_label).named_serializers[serializer_name]
    serializer = serializer_class(instance, data=data_querydict, partial=partial)
    serializer.is_valid(raise_exception=True)
    serializer.save()


@shared_task(base=UserFacingTask)
def delete(repo_name, publisher_name):
    """
    Delete a :class:`~pulpcore.app.models.Publisher`

    :param repo_name:       the name of a repository
    :type  repo_name:       str
    :param publisher_name:  the name of a publisher
    :type  publisher_name:  str
    """
    models.Publisher.objects.filter(name=publisher_name, repository__name=repo_name).delete()


@shared_task(base=UserFacingTask)
def publish(repo_name, publisher_name):
    """
    Call publish on the publisher defined by a plugin.

    A working directory is prepared, the plugin's publish is called, and then working directory is
    removed.

    Args:
        repo_name (str): unique name to specify the repository.
        publisher_name (str): name to specify the Publisher.
    """
    publisher = models.Publisher.objects.get(
        name=publisher_name,
        repository__name=repo_name).cast()
    log.warn(
        _('Publishing: repository=%(r)s, publisher=%(p)s'),
        {
            'r': repo_name,
            'p': publisher_name
        })
    with transaction.atomic():
        publication = models.Publication(publisher=publisher)
        publisher.publication = publication
        publication.save()
        with storage.working_dir_context() as working_dir:
                publisher.working_dir = working_dir
                publisher.publish()
                publisher.last_published = datetime.utcnow()
                publisher.save()
                distributions = models.Distribution.objects.filter(
                    publisher=publisher,
                    auto_updated=True)
                distributions.update(publication=publication)
    log.warn(
        _('Publication: %(p)s created'),
        {
            'p': publication.pk
        })

    # TODO: Replace WARN w/ INFO or DEBUG.
