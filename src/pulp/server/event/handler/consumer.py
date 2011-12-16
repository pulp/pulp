#
# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

"""
Contains product event handler classes.
"""

from pulp.server.event.dispatcher import *
from pulp.server.api.consumer import ConsumerApi
from pulp.server.agent import PulpAgent
from logging import getLogger

log = getLogger(__name__)


class ConsumerEvent(EventHandler):
    """
    The I{consumer} event handler.
    @ivar rapi: The consumer API object.
    @type rapi: L{consumerApi}
    """

    def __init__(self):
        self.capi = ConsumerApi()
        

    @outbound(action='created')
    def create(self, *args, **kwargs):
        """
        Raise events when a consumer is created.
        Called when consumerApi.create() is called.
        @param args: The arguments passed to consumerApi.create()
        @type args: list
        @param kwargs: The keyword arguments passed to consumerApi.create()
        @type kwargs: list
        """
        pass

    @outbound(action='updated')
    def update(self, *args, **kwargs):
        """
        Raise events when a consumer is updated.
        Called when consumerApi.update() is called.
        @param args: The arguments passed to consumerApi.update()
        @type args: list
        @param kwargs: The keyword arguments passed to consumerApi.update()
        @type kwargs: list
        """
        pass

    @outbound(action='deleted')
    def delete(self, *args, **kwargs):
        """
        Raise events when a consumer is deleted.
        Called when consumerApi.delete() is called.
        @param args: The arguments passed to consumerApi.delete()
        @type args: list
        @param kwargs: The keyword arguments passed to consumerApi.delete()
        @type kwargs: list
        """
        pass

    @inbound(action='created')
    def created(self, event):
        """
        The I{inbound} event handler for consumer.created AMQP events.
        Called when an AMQP event is received notifying that
        a consumer has been created.  When received, the API is used
        to create the specified consumer in pulp.
        @param event: The event payload.
        @type event: dict.
        """
        log.error("Consumer event create processing %s" % event)
        consumerid   = event['id']
        if not event.has_key('description'):
            description = consumerid
        else:
            description = event['description']
        log.error("Consumer event data %s" % consumerid)
        consumer = self.capi.create(consumerid, description)
        #invoke agent here to get consumer package profile
        agent = PulpAgent(consumer, async=True)
        update = agent.ProfileUpdateAction()
        update.perform()

    @inbound(action='updated')
    def updated(self, event):
        """
        The I{inbound} event handler for consumer.updated AMQP events.
        Called when an AMQP event is received notifying that
        a consumer has been created.  When received, the API is used
        to update the specified consumer in pulp.
        @param event: The event payload.
        @type event: dict.
        """
        log.error("Consumer event create processing %s" % event)
        pass

    @inbound(action='deleted')
    def deleted(self, event):
        """
        The I{inbound} event handler for consumer.deleted AMQP events.
        Called when an AMQP event is received notifying that
        a consumer has been deleted.  When received, the API is used
        to delete the specified consumer in pulp.
        @param event: The event payload.
        @type event: dict.
        """
        log.error("Consumer event delete processing %s" % event)
        consumerid   = event['id']
        self.capi.delete(consumerid)


EventDispatcher.register('consumer', ConsumerEvent)
