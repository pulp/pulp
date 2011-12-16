# -*- coding: utf-8 -*-  
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
Contains REPO event handler classes.
"""

import os
from pulp.server.event.dispatcher import *
from pulp.server.event.producer import EventProducer
from pulp.server.api.repo import RepoApi
from pulp.server.config import config
from pulp.server import util
from logging import getLogger

log = getLogger(__name__)


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
        @param repo: The created repo domain object.
        @type repo: Repo
        """
        repo = args[1]
        path = os.path.join(util.top_repos_location(), repo.relative_path)
        event = dict(id=repo.id, name=repo.name, path=path)
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
        id = args[1]
        delta = args[2]
        event = dict(id=id, delta=delta,)
        self.producer.send('repo.updated', event)

    @outbound(action='updated.content')
    def contentupdated(self, *args, **kwargs):
        """
        Raise events when a repo's content is updated.
        @param args: The arguments passed to RepoApi.xx()
        @type args: list
        @param kwargs: The keyword arguments passed to RepoApi.xx()
        @type kwargs: list
        """
        id = args[1]
        fields = ('relative_path',)
        repo = self.rapi.repository(id, fields)
        path = os.path.join(self.rapi.published_path, repo[fields[0]])
        event = dict(id=id, path=path,)
        self.producer.send('repo.updated.content', event)

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
        if len(args) > 1:
            id = args[1]
        else:
            id = kwargs.get('id')
        event = dict(id=id)
        self.producer.send('repo.deleted', event)


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


EventDispatcher.register('repo', RepoEvent)
