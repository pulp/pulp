# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

# Python
import logging

# 3rd Party
import web

# Pulp
import pulp.server.managers.factory as managers
from pulp.server.auth.authorization import READ, CREATE, UPDATE, DELETE
from pulp.server.webservices import execution
from pulp.server.exceptions import MissingResource
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.dispatch.call import CallRequest
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import auth_required

# -- constants ----------------------------------------------------------------

_LOG = logging.getLogger(__name__)

# -- controllers --------------------------------------------------------------

class Consumers(JSONController):

    @auth_required(READ)
    def GET(self):
        manager = managers.consumer_manager()
        return self.ok([])

    @auth_required(CREATE)
    def POST(self):

        # Pull all the consumer data
        consumer_data = self.params()
        id = consumer_data.get('id', None)
        display_name = consumer_data.get('display_name', None)
        description = consumer_data.get('description', None)
        notes = consumer_data.get('notes', None)

        # Creation
        manager = managers.consumer_manager()
        consumer = manager.register(id, display_name, description, notes)
        return self.ok(consumer)


class Consumer(JSONController):

    @auth_required(READ)
    def GET(self, id):
        return self.ok({})

    @auth_required(UPDATE)
    def PUT(self, id):

        # Pull all the consumer update data
        consumer_data = self.params()
        delta = consumer_data.get('delta', None)

        # Perform update
        manager = managers.consumer_manager()
        consumer = manager.update(id, delta)
        return self.ok(consumer)

    @auth_required(DELETE)
    def DELETE(self, id):

        # Perform deletion
        manager = managers.consumer_manager()
        manager.unregister(id)
        return self.ok()


class Bindings(JSONController):
    """
    Consumer I{bindings} represents the collection of
    objects used to associate a consumer and a repo-distributor
    association.  Users wanting to create this association will
    create an object in this collection.  Both bind and unbind
    is idempotent.
    """

    @auth_required(READ)
    def GET(self, consumer_id):
        """
        Fetch all bind objects referencing the
        specified I{consumer_id}.
        @param consumer_id: The specified consumer.
        @type consumer_id: str
        @return: A list of bind dict:
            {consumer_id:<str>,
             repo_id:<str>,
             distributor_id:<str>,
             distributor:<RepoDistributor>}
        @rtype: dict
        """
        manager = managers.consumer_bind_manager()
        bindings = manager.find_by_consumer(consumer_id)
        bindings = [Binding.serialized(b) for b in bindings]
        return self.ok(bindings)

    @auth_required(CREATE)
    def POST(self, consumer_id):
        """
        Create a bind association between the specified
        consumer by id included in the URL path and a repo-distributor
        specified in the POST body: {repo_id:<str>, distributor_id:<str>}.
        Designed to be itempotent so only MissingResource is expected to
        be raised by manager.
        @param consumer_id: The consumer to bind.
        @type consumer_id: str
        @return: The created bind model object:
            {consumer_id:<str>, repo_id:<str>, distributor_id:<str>}
        @rtype: dict
        """
        body = self.params()
        repo_id = body.get('repo_id')
        distributor_id = body.get('distributor_id')
        resources = {
            dispatch_constants.RESOURCE_CONSUMER_TYPE:
                {consumer_id:dispatch_constants.RESOURCE_READ_OPERATION},
            dispatch_constants.RESOURCE_REPOSITORY_TYPE:
                {repo_id:dispatch_constants.RESOURCE_READ_OPERATION},
            dispatch_constants.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE:
                {distributor_id:dispatch_constants.RESOURCE_READ_OPERATION},
        }
        args = [
            consumer_id,
            repo_id,
            distributor_id,
        ]
        manager = managers.consumer_bind_manager()
        call_request = CallRequest(
            manager.bind,
            args,
            resources=resources,
            weight=0)
        result = execution.execute_sync_ok(self, call_request)
        return result


class Binding(JSONController):
    """
    Represents a specific bind object.
    """

    @classmethod
    def serialized(cls, bind):
        manager = managers.repo_distributor_manager()
        distributor = manager.get_distributor(
            bind['repo_id'],
            bind['distributor_id'])
        expanded = dict(bind)
        expanded['distributor'] = distributor
        return expanded


    @auth_required(READ)
    def GET(self, consumer_id, repo_id, distributor_id):
        """
        Fetch a specific bind object which represents a specific association
        between a consumer and repo-distributor.
        @param consumer_id: A consumer ID.
        @type consumer_id: str
        @param repo_id: A repo ID.
        @type repo_id: str
        @param distributor_id: A distributor ID.
        @type distributor_id: str
        @return: A specific bind object:
            {consumer_id:<str>,
             repo_id:<str>,
             distributor_id:<str>,
             distributor:<RepoDistributor>}
        @rtype: dict
        """
        manager = managers.consumer_bind_manager()
        bind = manager.find(consumer_id, repo_id, distributor_id)
        return self.ok(self.serialized(bind))

    @auth_required(UPDATE)
    def PUT(self, consumer_id, repo_id, distributor_id):
        """
        Update a bind.
            **TBD
        @param consumer_id: A consumer ID.
        @type consumer_id: str
        @param repo_id: A repo ID.
        @type repo_id: str
        @param distributor_id: A distributor ID.
        @type distributor_id: str
        """
        return self.ok()

    @auth_required(DELETE)
    def DELETE(self, consumer_id, repo_id, distributor_id):
        """
        Delete a bind association between the specified
        consumer and repo-distributor.  Designed to be itempotent.
        @param consumer_id: A consumer ID.
        @type consumer_id: str
        @param repo_id: A repo ID.
        @type repo_id: str
        @param distributor_id: A distributor ID.
        @type distributor_id: str
        @return: The deleted bind model object:
            {consumer_id:<str>, repo_id:<str>, distributor_id:<str>}
            Or, None if bind does not exist.
        @rtype: dict
        """
        # update model
        manager = managers.consumer_bind_manager()
        bind = manager.unbind(consumer_id, repo_id, distributor_id)
        return self.ok(bind)


# -- web.py application -------------------------------------------------------


urls = (
    '/$', 'Consumers',
    '/([^/]+)/$', 'Consumer',
    '/([^/]+)/bindings/$', 'Bindings',
    '/([^/]+)/bindings/([^/]+)/([^/]+)/$', 'Binding',
)

application = web.application(urls, globals())
