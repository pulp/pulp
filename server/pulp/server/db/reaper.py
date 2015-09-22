from gettext import gettext as _
import logging

from celery import task

from pulp.common.tags import action_tag
from pulp.server import config as pulp_config
from pulp.server.async.tasks import Task
from pulp.server.db import models
from pulp.server.db.model import celery_result, consumer, repo_group, repository


# Add collections to reap here. The keys in this datastructure are the Model classes that represent
# each collection, and the values are the config keyname from our server.conf in the [data_reaping]
# section that corresponds to the collection. The config is consulted by the reap_expired_documents
# Task to determine how old documents should be (in days) before they are removed.
_COLLECTION_TIMEDELTAS = {
    models.TaskStatus: 'task_status_history',
    consumer.ConsumerHistoryEvent: 'consumer_history',
    repository.RepoSyncResult: 'repo_sync_history',
    repository.RepoPublishResult: 'repo_publish_history',
    repo_group.RepoGroupPublishResult: 'repo_group_publish_history',
    celery_result.CeleryResult: 'task_result_history',
}


_logger = logging.getLogger(__name__)


@task
def queue_reap_expired_documents():
    """
    Create an itinerary for reaper task
    """
    tags = [action_tag('reaper')]
    reap_expired_documents.apply_async(tags=tags)


@task(base=Task)
def reap_expired_documents():
    """
    For each collection in _COLLECTION_TIMEDELTAS, call the class method reap_old_documents().

    This method gets the number of days from the pulp_config, and calls reap_old_documents with the
    number of days as the argument.
    """
    _logger.info(_('The reaper task is cleaning out old documents from the database.'))
    for model_class, config_name in _COLLECTION_TIMEDELTAS.items():
        # Get the config for how old documents should be before they are reaped.
        config_days = pulp_config.config.getfloat('data_reaping', config_name)
        model_class.reap_old_documents(config_days)
    _logger.info(_('The reaper task has completed.'))
