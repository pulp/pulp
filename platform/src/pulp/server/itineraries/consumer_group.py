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
Itinerary creation for complex consumer group operations.
"""

from pulp.server.itineraries.consumer import (
    consumer_content_install_itinerary,
    consumer_content_update_itinerary,
    consumer_content_uninstall_itinerary)
from pulp.server.itineraries.bind import bind_itinerary, unbind_itinerary
from pulp.server.managers import factory as managers


def consumer_group_content_install_itinerary(consumer_group_id, units, options):
    """
    Create an itinerary for consumer group content installation.
    :param consumer_group_id: unique id of the consumer group
    :type consumer_group_id: str
    :param units: units to install
    :type units: list or tuple
    :param options: options to pass to the install manager
    :type options: dict or None
    :return: list of call requests
    :rtype: list
    """
    consumer_group = managers.consumer_group_query_manager().get_group(consumer_group_id)
    consumer_group_call_requests_list = []
    for consumer_id in consumer_group['consumer_ids']:
        consumer_call_requests = consumer_content_install_itinerary(consumer_id, units, options)
        consumer_group_call_requests_list.extend(consumer_call_requests)
 
    return consumer_group_call_requests_list


def consumer_group_content_update_itinerary(consumer_group_id, units, options):
    """
    Create an itinerary for consumer group content update.
    :param consumer_group_id: unique id of the consumer group
    :type consumer_group_id: str
    :param units: units to update
    :type units: list or tuple
    :param options: options to pass to the update manager
    :type options: dict or None
    :return: list of call requests
    :rtype: list
    """
    consumer_group = managers.consumer_group_query_manager().get_group(consumer_group_id)
    consumer_group_call_requests_list = []
    for consumer_id in consumer_group['consumer_ids']:
        consumer_call_requests = consumer_content_update_itinerary(consumer_id, units, options)
        consumer_group_call_requests_list.extend(consumer_call_requests)
 
    return consumer_group_call_requests_list


def consumer_group_content_uninstall_itinerary(consumer_group_id, units, options):
    """
    Create an itinerary for consumer group content uninstallation.
    :param consumer_group_id: unique id of the consumer group
    :type consumer_group_id: str
    :param units: units to uninstall
    :type units: list or tuple
    :param options: options to pass to the uninstall manager
    :type options: dict or None
    :return: list of call requests
    :rtype: list
    """
    consumer_group = managers.consumer_group_query_manager().get_group(consumer_group_id)
    consumer_group_call_requests_list = []
    for consumer_id in consumer_group['consumer_ids']:
        consumer_call_requests = consumer_content_uninstall_itinerary(consumer_id, units, options)
        consumer_group_call_requests_list.extend(consumer_call_requests)
 
    return consumer_group_call_requests_list


def consumer_group_bind_itinerary(
        group_id,
        repo_id,
        distributor_id,
        notify_agent,
        binding_config,
        agent_options):
    """
    Bind the members of the specified consumer group.
    :param group_id: A consumer group ID.
    :type group_id: str
    :param repo_id: A repository ID.
    :type repo_id: str
    :param distributor_id: A distributor ID.
    :type distributor_id: str
    :param agent_options: Bind options passed to the agent handler.
    :type agent_options: dict
    :param notify_agent: indicates if the agent should be sent a message about the new binding
    :type  notify_agent: bool
    :param binding_config: configuration options to use when generating the payload for this binding
    :type binding_config: dict
    :return: A list of call_requests.
    :rtype list
    """
    call_requests = []
    manager = managers.consumer_group_query_manager()
    group = manager.get_group(group_id)
    for consumer_id in group['consumer_ids']:
        itinerary = bind_itinerary(
            consumer_id=consumer_id,
            repo_id=repo_id,
            distributor_id=distributor_id,
            notify_agent=notify_agent,
            binding_config=binding_config,
            agent_options=agent_options)
        call_requests.extend(itinerary)
    return call_requests


def consumer_group_unbind_itinerary(group_id, repo_id, distributor_id, options):
    """
    Unbind the members of the specified consumer group.
    :param group_id: A consumer group ID.
    :type group_id: str
    :param repo_id: A repository ID.
    :type repo_id: str
    :param distributor_id: A distributor ID.
    :type distributor_id: str
    :param options: Bind options passed to the agent handler.
    :type options: dict
    :return: A list of call_requests.
    :rtype list
    """
    call_requests = []
    manager = managers.consumer_group_query_manager()
    group = manager.get_group(group_id)
    for consumer_id in group['consumer_ids']:
        itinerary = unbind_itinerary(consumer_id, repo_id, distributor_id, options)
        call_requests.extend(itinerary)
    return call_requests