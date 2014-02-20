# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License
# (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied, including the
# implied warranties of MERCHANTABILITY, NON-INFRINGEMENT, or FITNESS FOR A
# PARTICULAR PURPOSE.
# You should have received a copy of GPLv2 along with this software; if not,
# see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

import logging
from datetime import datetime, timedelta
from gettext import gettext as _

from celery import task

from pulp.common import dateutils
from pulp.server import config as pulp_config
from pulp.server.async.tasks import Task
from pulp.server.compat import ObjectId
from pulp.server.db.model import consumer, dispatch, repo_group, repository


# Add collections to reap here. The keys in this datastructure are the Model classes that represent
# each collection, and the values are the config keyname from our server.conf in the [data_reaping]
# section that corresponds to the collection. The config is consulted by the reap_expired_documents
# Task to determine how old documents should be (in days) before they are removed.
_COLLECTION_TIMEDELTAS = {
    dispatch.ArchivedCall: 'archived_calls',
    consumer.ConsumerHistoryEvent: 'consumer_history',
    repository.RepoSyncResult: 'repo_sync_history',
    repository.RepoPublishResult: 'repo_publish_history',
    repo_group.RepoGroupPublishResult: 'repo_group_publish_history',
}


_logger = logging.getLogger(__name__)


@task(base=Task)
def reap_expired_documents():
    """
    For each collection in _COLLECTION_TIMEDELTAS, remove documents that are older than the
    specified timedelta.
    """
    _logger.info(_('The reaper task is cleaning out old documents from the database.'))
    for model, config_name in _COLLECTION_TIMEDELTAS.items():
        collection = model.get_collection()
        # Get the config for how old documents should be before they are reaped.
        config_days = pulp_config.config.getfloat('data_reaping', config_name)
        age = timedelta(days=config_days)
        # Generate an ObjectId that we can use to know which objects to remove
        expired_object_id = _create_expired_object_id(age)
        # Remove all objects older than the timestamp encoded into the generated ObjectId
        collection.remove({'_id': {'$lte': expired_object_id}})
    _logger.info(_('The reaper task has completed.'))


def _create_expired_object_id(age):
    """
    By default, MongoDB uses a primary key that has the date that each document was created encoded
    into it. This method generates a pulp.server.compat.ObjectId that corresponds to the timstamp of
    now minues age, where age is a timedelta. For example, if age is 60 seconds, this will
    return an ObjectId that has the UTC time that it was 60 seconds ago encoded into it. This is
    useful in this module, as we want to automatically delete documents that are older than a
    particular age, and so we can issue a remove query to MongoDB for objects with _id attributes
    that are less than the ObjectId returned by this method.

    :param age: A timedelta representing the relative time in the past that you wish an ObjectId
                to be generated against.
    :type  age: datetime.timedelta
    :return:    An ObjectId containing the encoded time (now - age).
    :rtype:     pulp.server.compat.ObjectId
    """
    now = datetime.now(dateutils.utc_tz())
    expired_datetime = now - age
    expired_object_id = ObjectId.from_datetime(expired_datetime)
    return expired_object_id
