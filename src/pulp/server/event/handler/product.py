#! /usr/bin/env python
#
# Copyright (c) 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
#

"""
Contains product event handler classes.
"""

from pulp.server.event.dispatcher import *
from pulp.server.api.repo import RepoApi
from pulp.messaging.producer import EventProducer
from logging import getLogger

log = getLogger(__name__)


@handler(entity='product')
class ProductEvent(EventHandler):
    """
    The I{product} event handler.
    @ivar rapi: The product API object.
    @type rapi: L{productApi}
    """

    def __init__(self):
        self.rapi = RepoApi()
        

    @outbound(action='created')
    def create(self, *args, **kwargs):
        """
        Raise events when a product is created.
        Called when productApi.create() is called.
        @param args: The arguments passed to productApi.create()
        @type args: list
        @param kwargs: The keyword arguments passed to productApi.create()
        @type kwargs: list
        """
        pass

    @outbound(action='updated')
    def update(self, *args, **kwargs):
        """
        Raise events when a product is updated.
        Called when productApi.update() is called.
        @param args: The arguments passed to productApi.update()
        @type args: list
        @param kwargs: The keyword arguments passed to productApi.update()
        @type kwargs: list
        """
        pass

    @outbound(action='deleted')
    def delete(self, *args, **kwargs):
        """
        Raise events when a product is deleted.
        Called when productApi.delete() is called.
        @param args: The arguments passed to productApi.delete()
        @type args: list
        @param kwargs: The keyword arguments passed to productApi.delete()
        @type kwargs: list
        """
        pass

    @inbound(action='created')
    def created(self, event):
        """
        The I{inbound} event handler for product.created AMQP events.
        Called when an AMQP event is received notifying that
        a product has been created.  When received, the API is used
        to create the specified product in pulp.
        @param event: The event payload.
        @type event: dict.
        """
        log.error("Repo event create processing %s" % event)
        productid   = event['id']
        product_name = event['name']
        content_sets = event['content_sets']
        cert_data   = {'ca'   : event['ca_cert'],
                       'cert' : event['entitlement_cert'],
                       'key'  : event['cert_public_key'],
                       }
        log.error("Repo event data %s %s %s" % (product_name, content_sets, cert_data))
        self.rapi.create_product_repo(content_sets, cert_data, groupid=product_name)

    @inbound(action='updated')
    def updated(self, event):
        """
        The I{inbound} event handler for product.updated AMQP events.
        Called when an AMQP event is received notifying that
        a product has been created.  When received, the API is used
        to update the specified product in pulp.
        @param event: The event payload.
        @type event: dict.
        """
        pass

    @inbound(action='deleted')
    def deleted(self, event):
        """
        The I{inbound} event handler for product.deleted AMQP events.
        Called when an AMQP event is received notifying that
        a product has been deleted.  When received, the API is used
        to delete the specified product in pulp.
        @param event: The event payload.
        @type event: dict.
        """
        pass
