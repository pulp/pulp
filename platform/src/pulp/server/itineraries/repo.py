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

"""
Itinerary creation for complex repository operations.
"""

from pulp.common.tags import action_tag, resource_tag
from pulp.server import config as pulp_config
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.dispatch.call import CallRequest
from pulp.server.managers import factory as manager_factory


def sync_with_auto_publish_itinerary(repo_id, overrides=None):
    """
    Create a call request list for the synchronization of a repository and the
    publishing of any distributors that are configured for auto publish.
    @param repo_id: id of the repository to create a sync call request list for
    @type repo_id: str
    @param overrides: dictionary of configuration overrides for this sync
    @type overrides: dict or None
    @return: list of call request instances
    @rtype: list
    """

    repo_sync_manager = manager_factory.repo_sync_manager()

    sync_weight = pulp_config.config.getint('tasks', 'sync_weight')
    sync_tags = [resource_tag(dispatch_constants.RESOURCE_REPOSITORY_TYPE, repo_id),
                 action_tag('sync')]

    sync_call_request = CallRequest(repo_sync_manager.sync,
                                    [repo_id],
                                    {'sync_config_override': overrides},
                                    weight=sync_weight,
                                    tags=sync_tags,
                                    archive=True)
    sync_call_request.updates_resource(dispatch_constants.RESOURCE_REPOSITORY_TYPE, repo_id)
    sync_call_request.add_life_cycle_callback(dispatch_constants.CALL_ENQUEUE_LIFE_CYCLE_CALLBACK,
                                              repo_sync_manager.prep_sync)
    sync_call_request.add_life_cycle_callback(dispatch_constants.CALL_COMPLETE_LIFE_CYCLE_CALLBACK,
                                              repo_sync_manager.post_sync)

    call_requests = [sync_call_request]

    repo_publish_manager = manager_factory.repo_publish_manager()
    auto_publish_tags = [resource_tag(dispatch_constants.RESOURCE_REPOSITORY_TYPE, repo_id),
                         action_tag('auto_publish'), action_tag('publish')]
    auto_distributors = repo_publish_manager.auto_distributors(repo_id)

    for distributor in auto_distributors:
        distributor_id = distributor['id']
        publish_call_request = CallRequest(repo_publish_manager.publish,
                                           [repo_id, distributor_id],
                                           tags=auto_publish_tags,
                                           archive=True)
        publish_call_request.updates_resource(dispatch_constants.RESOURCE_REPOSITORY_TYPE, repo_id)
        publish_call_request.add_life_cycle_callback(dispatch_constants.CALL_ENQUEUE_LIFE_CYCLE_CALLBACK,
                                                     repo_publish_manager.prep_publish)
        publish_call_request.add_life_cycle_callback(dispatch_constants.CALL_COMPLETE_LIFE_CYCLE_CALLBACK,
                                                     repo_publish_manager.post_publish)
        publish_call_request.depends_on(sync_call_request.id, [dispatch_constants.CALL_FINISHED_STATE])

        call_requests.append(publish_call_request)

    return call_requests


def publish_itinerary(repo_id, distributor_id, overrides=None):
    """
    Create an itinerary for repo publish.
    @param repo_id: id of the repo to publish
    @type repo_id: str
    @param distributor_id: id of the distributor to use for the repo publish
    @type distributor_id: str
    @param overrides: dictionary of options to pass to the publish manager
    @type overrides: dict or None
    @return: list of call requests
    @rtype: list
    """

    repo_publish_manager = manager_factory.repo_publish_manager()
    weight = pulp_config.config.getint('tasks', 'publish_weight')
    tags = [resource_tag(dispatch_constants.RESOURCE_REPOSITORY_TYPE, repo_id),
            action_tag('publish')]

    call_request = CallRequest(repo_publish_manager.publish,
                               [repo_id, distributor_id],
                               {'publish_config_override': overrides},
                               weight=weight,
                               tags=tags,
                               archive=True)

    call_request.updates_resource(dispatch_constants.RESOURCE_REPOSITORY_TYPE, repo_id)
    call_request.add_life_cycle_callback(dispatch_constants.CALL_ENQUEUE_LIFE_CYCLE_CALLBACK,
                                         repo_publish_manager.prep_publish)
    call_request.add_life_cycle_callback(dispatch_constants.CALL_COMPLETE_LIFE_CYCLE_CALLBACK,
                                         repo_publish_manager.post_publish)

    return [call_request]
