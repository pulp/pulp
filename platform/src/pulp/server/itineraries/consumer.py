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
Itinerary creation for complex consumer operations.
"""

from pulp.common.tags import action_tag, resource_tag
from pulp.server import config as pulp_config
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.dispatch.call import CallRequest
from pulp.server.managers import factory as managers_factory


def consumer_content_install_itinerary(consumer_id, units, options):
    """
    Create an itinerary for consumer content installation.
    @param consumer_id: unique id of the consumer
    @type consumer_id: str
    @param units: units to install
    @type units: list or tuple
    @param options: options to pass to the install manager
    @type options: dict or None
    @return: list of call requests
    @rtype: list
    """
    manager = managers_factory.consumer_agent_manager()
    args = [consumer_id]
    kwargs = {'units': units,
              'options': options.get('options', {})}
    weight = pulp_config.config.getint('tasks', 'consumer_content_weight')
    tags = [resource_tag(dispatch_constants.RESOURCE_CONSUMER_TYPE, consumer_id),
            action_tag('unit_install')]
    call_request = CallRequest(manager.install_content, args, kwargs, weight=weight, tags=tags, archive=True)
    call_request.reads_resource(dispatch_constants.RESOURCE_CONSUMER_TYPE, consumer_id)
    return [call_request]


def consumer_content_update_itinerary(consumer_id, units, options):
    """
    Create an itinerary for consumer content update.
    @param consumer_id: unique id of the consumer
    @type consumer_id: str
    @param units: units to update
    @type units: list or tuple
    @param options: options to pass to the update manager
    @type options: dict or None
    @return: list of call requests
    @rtype: list
    """
    manager = managers_factory.consumer_agent_manager()
    args = [consumer_id]
    kwargs = {'units': units,
              'options': options.get('options', {})}
    weight = pulp_config.config.getint('tasks', 'consumer_content_weight')
    tags = [resource_tag(dispatch_constants.RESOURCE_CONSUMER_TYPE, consumer_id),
            action_tag('unit_update')]
    call_request = CallRequest(manager.update_content, args, kwargs, weight=weight, tags=tags, archive=True)
    call_request.reads_resource(dispatch_constants.RESOURCE_CONSUMER_TYPE, consumer_id)
    return [call_request]


def consumer_content_uninstall_itinerary(consumer_id, units, options):
    """
    Create an itinerary for consumer content uninstall.
    @param consumer_id: unique id of the consumer
    @type consumer_id: str
    @param units: units to uninstall
    @type units: list or tuple
    @param options: options to pass to the uninstall manager
    @type options: dict or None
    @return: list of call requests
    @rtype: list
    """
    manager = managers_factory.consumer_agent_manager()
    args = [consumer_id]
    kwargs = {'units': units,
              'options': options.get('options', {})}
    weight = pulp_config.config.getint('tasks', 'consumer_content_weight')
    tags = [resource_tag(dispatch_constants.RESOURCE_CONSUMER_TYPE, consumer_id),
            action_tag('unit_uninstall')]
    call_request = CallRequest(manager.uninstall_content, args, kwargs, weight=weight, tags=tags, archive=True)
    call_request.reads_resource(dispatch_constants.RESOURCE_CONSUMER_TYPE, consumer_id)
    return [call_request]

