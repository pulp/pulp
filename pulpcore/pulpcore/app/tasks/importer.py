from gettext import gettext as _
import logging

from celery import shared_task
from django.http import QueryDict

from pulpcore.app import models
from pulpcore.app.apps import get_plugin_config
from pulpcore.tasking.services import storage
from pulpcore.tasking.tasks import UserFacingTask


log = logging.getLogger(__name__)


@shared_task(base=UserFacingTask)
def update(importer_id, app_label, serializer_name, data=None, partial=False):
    """
    Update an :class:`~pulp.app.models.Importer`

    Args:
        importer_id (str): the id of the importer
        app_label (str): the Django app label of the plugin that provides the importer
        serializer_name (str): name of the serializer class for the importer
        data (dict): dictionary whose keys represent the fields of the importer that need to be
            updated with the corresponding values.
        partial (bool): When true, only the fields specified in the data dictionary are updated.
            When false, any fields missing from the data dictionary are assumed to be None and
            their values are updated as such.

    Raises:
        :class:`rest_framework.exceptions.ValidationError`: When serializer instance can't be saved
            due to validation error. This theoretically should never occur since validation is
            performed before the task is dispatched.
    """
    instance = models.Importer.objects.get(id=importer_id).cast()
    data_querydict = QueryDict('', mutable=True)
    data_querydict.update(data)
    serializer_class = get_plugin_config(app_label).named_serializers[serializer_name]
    serializer = serializer_class(instance, data=data_querydict, partial=partial)
    serializer.is_valid(raise_exception=True)
    serializer.save()


@shared_task(base=UserFacingTask)
def delete(repo_name, importer_name):
    """
    Delete an :class:`~pulpcore.app.models.Importer`

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
        raise ValueError(_("An importer must have a 'feed_url' attribute to sync."))

    with storage.working_dir_context() as working_dir:
        importer.working_dir = working_dir
        log.info(_('Starting sync: repository=%(repo)s importer=%(imp)s'),
                 {'repo': repo_name, 'imp': importer_name})
        importer.sync()
