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
from pulp.server.api.repo import RepoApi
from pulp.server.api.consumer import ConsumerApi
from logging import getLogger

log = getLogger(__name__)


class ProductEvent(EventHandler):
    """
    The I{product} event handler.
    @ivar rapi: The product API object.
    @type rapi: L{productApi}
    """

    def __init__(self):
        self.rapi = RepoApi()
        self.capi = ConsumerApi()
        

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
        gpg_key_url = event['gpg_key_url']
        log.error("Repo event data %s %s %s" % (product_name, content_sets, cert_data))
        self.rapi.create_product_repo(content_sets, cert_data, groupid=product_name, 
                                      gpg_keys=gpg_key_url)

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
        log.error("Repo event create processing %s" % event)
        productid   = event['id']
        product_name = event['name']
        content_sets = event['content_sets']
        cert_data   = {'ca'   : event['ca_cert'],
                       'cert' : event['entitlement_cert'],
                       'key'  : event['cert_public_key'],
                      }
        gpg_key_url = event['gpg_key_url']
        log.error("Repo event data %s %s %s" % (product_name, content_sets, cert_data))
        self.rapi.update_product_repo(content_sets, cert_data, groupid=product_name, gpg_keys=gpg_key_url)

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
        log.error("Repo event delete processing %s" % event)
        productid   = event['id']
        product_name = event['name']
        log.error("Product event data %s" % (product_name))
        self.rapi.delete_product_repo(groupid=product_name)
    
    @inbound(action='bind')
    def bind(self, event):
        """
        The I{inbound} event handler for product.bind AMQP events.
        Called when an AMQP event is received notifying that
        a product binds to a consumer.  When received, the API is used
        to subscribe to the specified product repo in pulp.
        @param event: The event payload.
        @type event: dict.
        """
        log.error("Product Event bind processing %s" % event)
        productid = event['id']
        product_name = event['name']
        consumerid = event['consumer_id']
        release = event['consumer_os_release']
        arch    = event['consumer_os_arch']
        repos = self.rapi.repositories(spec={"groupid" : product_name, 
                                             "release" : release, 
                                             "arch" : arch})
        log.error("Repos found to bind %s" % repos)
        consumer = self.capi.consumer(consumerid)
        if not consumer:
            log.error("Consumer %s does not exist. Nothing to bind" % consumerid)
            return
        
        for repo in repos:
            self.capi.bind(consumer['id'], repo['id'])
    
    @inbound(action='unbind')
    def unbind(self, event):
        """
        The I{inbound} event handler for product.unbind AMQP events.
        Called when an AMQP event is received notifying that
        a product unbinds to a consumer.  When received, the API is used
        to unsubscribe to the specified product repo in pulp.
        @param event: The event payload.
        @type event: dict.
        """
        log.error("Product Event unbind processing %s" % event)
        productid = event['id']
        product_name = event['name']
        consumerid = event['consumer_id']
        consumer = self.capi.consumer(consumerid)
        if not consumer:
            log.error("Consumer %s does not exist. Nothing to bind" % consumerid)
            return
        log.error("Repos in consumer %s" % consumer['repoids'])
        for repoid in consumer['repoids']:
            repo = self.rapi.repository(str(repoid))
            log.error("Processing repo %s" % repo)
            if product_name in repo['groupid']:
                log.error("Unbind the consumer %s from repo %s" % (consumerid, repo['id']))
                self.capi.unbind(consumer['id'], repo['id'])
                

EventDispatcher.register('product', ProductEvent)
