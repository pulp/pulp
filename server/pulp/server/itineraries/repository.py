# Copyright (c) 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import logging

from pulp.server.dispatch.call import CallRequest
from pulp.common.tags import action_tag, resource_tag
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.managers import factory as managers
from pulp.server.itineraries.bind import unbind_itinerary, bind_itinerary


_LOG = logging.getLogger(__name__)


def repo_delete_itinerary(repo_id):
    """
    Get the itinerary for deleting a repository.
      1. Delete the repository on the sever.
      2. Unbind any bound consumers.
    @param repo_id: A repository ID.
    @type repo_id: str
    @return: A list of call_requests known as an itinerary.
    @rtype list
    """

    call_requests = []

    # delete repository

    manager = managers.repo_manager()
    tags = [
        resource_tag(dispatch_constants.RESOURCE_REPOSITORY_TYPE, repo_id),
        action_tag('delete')
    ]

    delete_request = CallRequest( # rbarlow_converted
        manager.delete_repo,
        [repo_id],
        tags=tags,
        archive=True)
    delete_request.deletes_resource(dispatch_constants.RESOURCE_REPOSITORY_TYPE, repo_id)
    call_requests.append(delete_request)

    # append unbind itineraries foreach bound consumer

    options = {}
    manager = managers.consumer_bind_manager()
    for bind in manager.find_by_repo(repo_id):
        unbind_requests = unbind_itinerary(
            bind['consumer_id'],
            bind['repo_id'],
            bind['distributor_id'],
            options)
        if unbind_requests:
            unbind_requests[0].depends_on(delete_request.id)
            call_requests.extend(unbind_requests)

    return call_requests


def distributor_delete_itinerary(repo_id, distributor_id):
    """
    Get the itinerary for deleting a repository distributor.
      1. Delete the distributor on the sever.
      2. Unbind any bound consumers.
    @param repo_id: A repository ID.
    @type repo_id: str
    @return: A list of call_requests known as an itinerary.
    @rtype list
    """

    call_requests = []

    # delete distributor

    manager = managers.repo_distributor_manager()

    tags = [
        resource_tag(dispatch_constants.RESOURCE_REPOSITORY_TYPE, repo_id),
        resource_tag(dispatch_constants.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE, distributor_id),
        action_tag('remove_distributor')
    ]

    delete_request = CallRequest( # rbarlow_converted
        manager.remove_distributor,
        [repo_id, distributor_id],
        tags=tags,
        archive=True)

    delete_request.updates_resource(dispatch_constants.RESOURCE_REPOSITORY_TYPE, repo_id)
    delete_request.deletes_resource(dispatch_constants.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE, distributor_id)

    call_requests.append(delete_request)

    # append unbind itineraries foreach bound consumer

    options = {}
    manager = managers.consumer_bind_manager()
    for bind in manager.find_by_distributor(repo_id, distributor_id):
        unbind_requests = unbind_itinerary(
            bind['consumer_id'],
            bind['repo_id'],
            bind['distributor_id'],
            options)
        if unbind_requests:
            unbind_requests[0].depends_on(delete_request.id)
            call_requests.extend(unbind_requests)

    return call_requests


def distributor_update_itinerary(repo_id, distributor_id, config, delta=None):
    """
    Get the itinerary for updating a repository distributor.
      1. Update the distributor on the server.
      2. (re)bind any bound consumers.

    :param repo_id:         A repository ID.
    :type  repo_id:         str
    :param distributor_id:  A unique distributor id
    :type  distributor_id:  str
    :param config:          A configuration dictionary for a distributor instance. The contents of this
                            dict depends on the type of distributor.
    :type  config:          dict
    :param delta:           A dictionary used to change other saved configuration values for a
                            distributor instance. This currently only supports the 'auto_publish'
                            keyword, which should have a value of type bool
    :type  delta:           dict

    :return: A list of call_requests known as an itinerary.
    :rtype: list
    """

    call_requests = []

    # update the distributor

    manager = managers.repo_distributor_manager()

    tags = [
        resource_tag(dispatch_constants.RESOURCE_REPOSITORY_TYPE, repo_id),
        resource_tag(dispatch_constants.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE, distributor_id),
        action_tag('update_distributor')
    ]

    # Retrieve configuration options from the delta
    auto_publish = None
    if delta is not None:
        auto_publish = delta.get('auto_publish')

    update_request = CallRequest(manager.update_distributor_config, [repo_id, distributor_id], # rbarlow_converted
                                 {'distributor_config': config, 'auto_publish': auto_publish}, tags=tags,
                                 archive=True, kwarg_blacklist=['distributor_config', 'auto_publish'])

    update_request.updates_resource(dispatch_constants.RESOURCE_REPOSITORY_TYPE, repo_id)
    update_request.updates_resource(dispatch_constants.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE, distributor_id)

    call_requests.append(update_request)

    # append unbind itineraries foreach bound consumer

    options = {}
    manager = managers.consumer_bind_manager()
    for bind in manager.find_by_distributor(repo_id, distributor_id):
        bind_requests = bind_itinerary(
            bind['consumer_id'],
            bind['repo_id'],
            bind['distributor_id'],
            bind['notify_agent'],
            bind['binding_config'],
            options)
        if bind_requests:
            bind_requests[0].depends_on(update_request.id)
            call_requests.extend(bind_requests)

    return call_requests
