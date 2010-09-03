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
Contains REPO event handler classes.
"""

from pulp.server.event.dispatcher import *
from pulp.server.api.repo import RepoApi
from pulp.messaging.producer import EventProducer
from logging import getLogger

log = getLogger(__name__)


@handler(entity='repo')
class RepoEvent(EventHandler):
    """
    The I{repo} event handler.
    @ivar rapi: The repo API object.
    @type rapi: L{RepoApi}
    """

    def __init__(self):
        self.rapi = RepoApi()
        self.producer = EventProducer()

    @outbound(action='created')
    def create(self, *args, **kwargs):
        """
        Raise events when a repo is created.
        Called when RepoApi.create() is called.
        @param args: The arguments passed to RepoApi.create()
        @type args: list
        @param kwargs: The keyword arguments passed to RepoApi.create()
        @type kwargs: list
        """
        event = dict(
            id=args[1],
            name=args[2],)
        self.producer.send('repo.created', event)

    @outbound(action='updated')
    def update(self, *args, **kwargs):
        """
        Raise events when a repo is updated.
        Called when RepoApi.update() is called.
        @param args: The arguments passed to RepoApi.update()
        @type args: list
        @param kwargs: The keyword arguments passed to RepoApi.update()
        @type kwargs: list
        """
        pass

    @outbound(action='deleted')
    def delete(self, *args, **kwargs):
        """
        Raise events when a repo is deleted.
        Called when RepoApi.delete() is called.
        @param args: The arguments passed to RepoApi.delete()
        @type args: list
        @param kwargs: The keyword arguments passed to RepoApi.delete()
        @type kwargs: list
        """
        pass

    @inbound(action='created')
    def created(self, event):
        """
        The I{inbound} event handler for repo.created AMQP events.
        Called when an AMQP event is received notifying that
        a repo has been created.  When received, the API is used
        to create the specified repo in pulp.
        @param event: The event payload.
        @type event: dict.
        """
        id   = event['id']
        name = event['name']
        arch = event.get('arch', 'noarch')
        self.rapi.create(id, name, arch)

    @inbound(action='updated')
    def updated(self, event):
        """
        The I{inbound} event handler for repo.updated AMQP events.
        Called when an AMQP event is received notifying that
        a repo has been created.  When received, the API is used
        to update the specified repo in pulp.
        @param event: The event payload.
        @type event: dict.
        """
        pass

    @inbound(action='deleted')
    def deleted(self, event):
        """
        The I{inbound} event handler for repo.deleted AMQP events.
        Called when an AMQP event is received notifying that
        a repo has been deleted.  When received, the API is used
        to delete the specified repo in pulp.
        @param event: The event payload.
        @type event: dict.
        """
        pass

