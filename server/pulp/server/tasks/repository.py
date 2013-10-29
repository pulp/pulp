# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import celery

from pulp.common.tags import resource_tag, action_tag
from pulp.server.constants import REPO_RESOURCE_PREFIX
from pulp.server.dispatch.constants import RESOURCE_REPOSITORY_TYPE
from pulp.server.managers.repo import publish


@celery.task
def delete(repo_id):
    pass


@celery.task
def distributor_delete(repo_id, distributor_id):
    pass


@celery.task
def distributor_update(repo_id, distributor_id, config, delta):
    pass


@celery.task
def publish(repo_id, distributor_id, overrides=None):
    """
    Create an itinerary for repo publish.
    :param repo_id: id of the repo to publish
    :type repo_id: str
    :param distributor_id: id of the distributor to use for the repo publish
    :type distributor_id: str
    :param overrides: dictionary of options to pass to the publish manager
    :type overrides: dict or None
    :return: list of call requests
    :rtype: list
    """
    resource_id = REPO_RESOURCE_PREFIX + repo_id
    kwargs = {
        'repo_id': repo_id,
        'distributor_id': distributor_id,
        'publish_config_override': overrides
    }

    tags = [resource_tag(RESOURCE_REPOSITORY_TYPE, repo_id),
            action_tag('publish')]

    return publish.publish.apply_async_with_reservation(
        resource_id, tags=tags, kwargs=kwargs)

@celery.task
def sync_with_auto_publish(repo_id, overrides=None):
    pass
