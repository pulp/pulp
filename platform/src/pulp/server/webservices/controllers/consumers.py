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
from web.webapi import BadRequest

# Pulp
from pulp.common.tags import action_tag, resource_tag
from pulp.server import config as pulp_config
import pulp.server.managers.factory as managers
from pulp.server.auth.authorization import READ, CREATE, UPDATE, DELETE
from pulp.server.db.model.criteria import Criteria
from pulp.server.webservices import execution
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.dispatch.call import CallRequest
from pulp.server.webservices.controllers.search import SearchController
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import auth_required
from pulp.server.webservices import serialization
from pulp.server.exceptions import MissingValue

# -- constants ----------------------------------------------------------------

_LOG = logging.getLogger(__name__)

def process_consumers(consumers, merge_bindings=False):
    """
    Apply standard processing to consumers before returning them to a client.
    This includes adding the '_href' link attribute, and optionally merging in
    related bindings.

    @param consumers:   list of consumers pulled from the database
    @type  consumer:    list

    @param merge_bindings:  iff True, add an attribute 'bindings' to each
                            consumer, the value of which will be a list of
                            related binding objects.
    @type  merge_bindings:  bool

    @return:    same list that was passed in, just for convenience. list members
                are modified in-place
    @rtype:     list
    """
    ids = [consumer['id'] for consumer in consumers]
    if merge_bindings:
        bindings = managers.consumer_bind_manager().find_by_consumer_list(ids)

    for consumer in consumers:
        consumer.update(serialization.link.current_link_obj())
        if merge_bindings:
            consumer['bindings'] = bindings[consumer['id']]
    return consumers


# -- controllers --------------------------------------------------------------

class ConsumersCollection(JSONController):
    
    # Scope: Collection
    # GET:   Retrieves all consumers registered to the Pulp Server
    # POST:  Register a consumer

    @auth_required(READ)
    def GET(self):

        query_manager = managers.consumer_query_manager()
        consumers = query_manager.find_all()

        process_consumers(consumers, self.params().get('bindings', False))

        return self.ok(consumers)

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
        resources = {dispatch_constants.RESOURCE_CONSUMER_TYPE: {id: dispatch_constants.RESOURCE_CREATE_OPERATION}}
        args = [id, display_name, description, notes]
        weight = pulp_config.config.getint('tasks', 'create_weight')
        tags = [resource_tag(dispatch_constants.RESOURCE_CONSUMER_TYPE, id),
                action_tag('create')]
        call_request = CallRequest(manager.register,
                                   args,
                                   resources=resources,
                                   weight=weight,
                                   tags=tags)
        return execution.execute_sync_created(self, call_request, id)


class ConsumerSearch(SearchController):
    def __init__(self):
        super(ConsumerSearch, self).__init__(
            managers.consumer_query_manager().find_by_criteria)

    def GET(self):
        consumers = self._get_query_results_from_get()
        process_consumers(consumers, self.params().get('bindings', False))
        return self.ok(consumers)

    def POST(self):
        consumers = self._get_query_results_from_post()
        process_consumers(consumers, self.params().get('bindings', False))
        return self.ok(consumers)


class ConsumerResource(JSONController):

    # Scope:   Resource
    # GET:     Get Consumer details
    # DELETE:  Unregister a consumer
    # PUT:     Consumer update

    @auth_required(READ)
    def GET(self, id):

        manager = managers.consumer_manager()
        consumer = manager.get_consumer(id)

        consumer = process_consumers(
            [consumer], self.params().get('bindings', False))[0]

        return self.ok(consumer)

    @auth_required(DELETE)
    def DELETE(self, id):

        manager = managers.consumer_manager()
        
        resources = {dispatch_constants.RESOURCE_CONSUMER_TYPE: {id: dispatch_constants.RESOURCE_DELETE_OPERATION}}
        tags = [resource_tag(dispatch_constants.RESOURCE_CONSUMER_TYPE, id),
                action_tag('delete')]
        call_request = CallRequest(manager.unregister,
                                   [id],
                                   resources=resources,
                                   tags=tags)
        return self.ok(execution.execute(call_request))

    @auth_required(UPDATE)
    def PUT(self, id):

        # Pull all the consumer update data
        consumer_data = self.params()
        delta = consumer_data.get('delta', None)

        # Perform update        
        manager = managers.consumer_manager()
        resources = {dispatch_constants.RESOURCE_CONSUMER_TYPE: {id: dispatch_constants.RESOURCE_UPDATE_OPERATION}}
        tags = [resource_tag(dispatch_constants.RESOURCE_CONSUMER_TYPE, id),
                action_tag('update')]
        call_request = CallRequest(manager.update,
                                   [id, delta],
                                   resources=resources,
                                   tags=tags)
        consumer = execution.execute(call_request)
        consumer.update(serialization.link.current_link_obj())
        return self.ok(consumer)


class Bindings(JSONController):
    """
    Consumer I{bindings} represents the collection of
    objects used to associate a consumer and a repo-distributor
    association.  Users wanting to create this association will
    create an object in this collection.  Both bind and unbind
    is idempotent.
    """

    #@auth_required(READ)
    def GET(self, consumer_id, repo_id=None):
        """
        Fetch all bind objects referencing the
        specified I{consumer_id}.
        @param consumer_id: The specified consumer.
        @type consumer_id: str
        @return: A list of bind dict:
            {consumer_id:<str>,
             repo_id:<str>,
             distributor_id:<str>,
             href:<str>,
             type_id:<str>,
             details:<dict>}
        @rtype: dict
        """
        manager = managers.consumer_bind_manager()
        bindings = manager.find_by_consumer(consumer_id, repo_id)
        bindings = [serialization.binding.serialize(b) for b in bindings]
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
        link = serialization.link.child_link_obj(
            consumer_id,
            repo_id,
            distributor_id)
        result = execution.execute_sync_created(self, call_request, link)
        return result


class Binding(JSONController):
    """
    Represents a specific bind resource.
    """

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
             href:<str>,
             type_id:<str>,
             details:<dict>}
        @rtype: dict
        """
        manager = managers.consumer_bind_manager()
        bind = manager.get_bind(consumer_id, repo_id, distributor_id)
        serialized_bind = serialization.binding.serialize(bind)
        return self.ok(serialized_bind)

    @auth_required(DELETE)
    def DELETE(self, consumer_id, repo_id, distributor_id):
        """
        Delete a bind association between the specified
        consumer and repo-distributor.  Designed to be idempotent.
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
        manager = managers.consumer_bind_manager()
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
        tags = [
            resource_tag(dispatch_constants.RESOURCE_CONSUMER_TYPE, consumer_id),
            resource_tag(dispatch_constants.RESOURCE_REPOSITORY_TYPE, repo_id),
            resource_tag(dispatch_constants.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE, distributor_id),
            action_tag('unbind')
        ]
        call_request = CallRequest(manager.unbind,
                                   args=args,
                                   resources=resources,
                                   tags=tags)
        return self.ok(execution.execute(call_request))


class Content(JSONController):
    """
    Represents a specific bind object.
    """

    @auth_required(CREATE)
    def POST(self, id, action):
        """
        Content actions.
        """
        method = getattr(self, action, None)
        if method:
            return method(id)
        else:
            raise BadRequest()

    def install(self, id):
        """
        Install content (units) on a consumer.
        Expected body: {units:[], options:<dict>}
        where unit is: {type_id:<str>, unit_key={}} and the
        options is a dict of install options.
        @param id: A consumer ID.
        @type id: str
        @return: TBD
        @rtype: dict
        """
        body = self.params()
        units = body.get('units')
        options = body.get('options')
        resources = {
            dispatch_constants.RESOURCE_CONSUMER_TYPE:
                {id:dispatch_constants.RESOURCE_READ_OPERATION},
        }
        args = [
            id,
            units,
            options,
        ]
        manager = managers.consumer_agent_manager()
        call_request = CallRequest(
            manager.install_content,
            args,
            resources=resources,
            weight=0,
            asynchronous=True,
            archive=True,)
        result = execution.execute_async(self, call_request)
        return result

    def update(self, id):
        """
        Update content (units) on a consumer.
        Expected body: {units:[], options:<dict>}
        where unit is: {type_id:<str>, unit_key={}} and the
        options is a dict of update options.
        @param id: A consumer ID.
        @type id: str
        @return: TBD
        @rtype: dict
        """
        body = self.params()
        units = body.get('units')
        options = body.get('options')
        resources = {
            dispatch_constants.RESOURCE_CONSUMER_TYPE:
                {id:dispatch_constants.RESOURCE_READ_OPERATION},
        }
        args = [
            id,
            units,
            options,
        ]
        manager = managers.consumer_agent_manager()
        call_request = CallRequest(
            manager.update_content,
            args,
            resources=resources,
            weight=0,
            asynchronous=True,
            archive=True,)
        result = execution.execute_async(self, call_request)
        return result

    def uninstall(self, id):
        """
        Uninstall content (units) on a consumer.
        Expected body: {units:[], options:<dict>}
        where unit is: {type_id:<str>, unit_key={}} and the
        options is a dict of uninstall options.
        @param id: A consumer ID.
        @type id: str
        @return: TBD
        @rtype: dict
        """
        body = self.params()
        units = body.get('units')
        options = body.get('options')
        resources = {
            dispatch_constants.RESOURCE_CONSUMER_TYPE:
                {id:dispatch_constants.RESOURCE_READ_OPERATION},
        }
        args = [
            id,
            units,
            options,
        ]
        manager = managers.consumer_agent_manager()
        call_request = CallRequest(
            manager.uninstall_content,
            args,
            resources=resources,
            weight=0,
            asynchronous=True,
            archive=True,)
        result = execution.execute_async(self, call_request)
        return result

class ConsumerHistory(JSONController):

    @auth_required(READ)
    def GET(self, id):
        """
        @type id: str
        @param id: consumer id
        """
        valid_filters = ['event_type', 'limit', 'sort', 'start_date', 'end_date']
        filters = self.filters(valid_filters)
        event_type = filters.get('event_type', None)
        limit = filters.get('limit', None)
        sort = filters.get('sort', None)
        start_date = filters.get('start_date', None)
        end_date = filters.get('end_date', None)

        if sort is None:
            sort = 'descending'
        else:
            sort = sort[0]

        if limit:
            limit = int(limit[0])

        if start_date:
            start_date = start_date[0]

        if end_date:
            end_date = end_date[0]
            
        if event_type:
            event_type = event_type[0]

        results = managers.consumer_history_manager().query(consumer_id=id, event_type=event_type, limit=limit,
                                    sort=sort, start_date=start_date, end_date=end_date)
        return self.ok(results)


class Profiles(JSONController):
    """
    Consumer I{profiles} represents the collection of
    objects used to associate consumers and installed content
    unit profiles.
    """

    @auth_required(READ)
    def GET(self, consumer_id):
        """
        Get all profiles associated with a consumer.
        @param consumer_id: The consumer ID.
        @type consumer_id: str
        @return: A list of profiles:
          profile is: {consumer_id:<str>, content_type:<str>, profile:<dict>}
        @return: list
        """
        manager = managers.consumer_profile_manager()
        profiles = manager.get_profiles(consumer_id)
        profiles = [serialization.profile.serialize(p) for p in profiles]
        return self.ok(profiles)

    @auth_required(CREATE)
    def POST(self, consumer_id):
        """
        Associate a profile with a consumer by content type ID.
        @param consumer_id: A consumer ID.
        @type consumer_id: str
        @return: The created model object:
            {consumer_id:<str>, content_type:<str>, profile:<dict>}
        @rtype: dict
        """
        body = self.params()
        content_type = body.get('content_type')
        profile = body.get('profile')
        resources = {
            dispatch_constants.RESOURCE_CONSUMER_TYPE:
                {consumer_id:dispatch_constants.RESOURCE_READ_OPERATION},
        }
        args = [
            consumer_id,
            content_type,
            profile,
        ]
        manager = managers.consumer_profile_manager()
        call_request = CallRequest(
            manager.create,
            args,
            resources=resources,
            weight=0)
        link = serialization.link.child_link_obj(consumer_id, content_type)
        result = execution.execute_sync_created(self, call_request, link)
        return result


class Profile(JSONController):
    """
    Consumer I{profiles} represents the collection of
    objects used to associate consumers and installed content
    unit profiles.
    """

    @auth_required(READ)
    def GET(self, consumer_id, content_type):
        """
        @param consumer_id: The consumer ID.
        @type consumer_id: str
        """
        manager = managers.consumer_profile_manager()
        profile = manager.get_profile(consumer_id, content_type)
        serialized = serialization.profile.serialize(profile)
        return self.ok(serialized)

    @auth_required(UPDATE)
    def PUT(self, consumer_id, content_type):
        """
        Update the association of a profile with a consumer by content type ID.
        @param consumer_id: A consumer ID.
        @type consumer_id: str
        @param content_type: A content unit type ID.
        @type content_type: str
        @return: The updated model object:
            {consumer_id:<str>, content_type:<str>, profile:<dict>}
        @rtype: dict
        """
        body = self.params()
        profile = body.get('profile')
        resources = {
            dispatch_constants.RESOURCE_CONSUMER_TYPE:
                {consumer_id:dispatch_constants.RESOURCE_READ_OPERATION},
        }
        args = [
            consumer_id,
            content_type,
            profile,
        ]
        manager = managers.consumer_profile_manager()
        call_request = CallRequest(
            manager.update,
            args,
            resources=resources,
            weight=0)
        link = serialization.link.child_link_obj(consumer_id, content_type)
        result = execution.execute_sync_created(self, call_request, link)
        return result

    @auth_required(DELETE)
    def DELETE(self, consumer_id, content_type):
        """
        Delete an association between the specified
        consumer and profile.  Designed to be idempotent.
        @param consumer_id: A consumer ID.
        @type consumer_id: str
        @param content_type: The content type ID.
        @type content_type: str
        @return: The deleted model object:
            {consumer_id:<str>, content_type:<str>, profile:<dict>}
            Or, None if bind does not exist.
        @rtype: dict
        """
        manager = managers.consumer_profile_manager()
        resources = {
            dispatch_constants.RESOURCE_CONSUMER_TYPE:
                {consumer_id:dispatch_constants.RESOURCE_READ_OPERATION},
        }
        args = [
            consumer_id,
            content_type,
        ]
        tags = [
            resource_tag(dispatch_constants.RESOURCE_CONSUMER_TYPE, consumer_id),
        ]
        call_request = CallRequest(manager.delete,
                                   args=args,
                                   resources=resources,
                                   tags=tags)
        return self.ok(execution.execute(call_request))


class ContentApplicability(JSONController):
    """
    Determine content applicability.
    """

    #@auth_required(READ)
    def POST(self):
        """
        Determine content applicability.
        body {criteria:<dict>, units:[{type_id:<str>,unit_key:<str>}]}
        @return: A dict of applicability reports keyed by consumer ID.
            Each report is:
                {unit:<{type_id:<str>,unit_key:<str>}>,
                 applicable:<bool>,
                 summary:<str>,
                 details:<?>}
        @return: dict
        """
        body = self.params()
        try:
            criteria = body['criteria']
            units = body['units']
        except KeyError, e:
            raise MissingValue(str(e))
        criteria = Criteria.from_client_input(criteria)
        manager = managers.consumer_applicability_manager()
        report = manager.units_applicable(criteria, units)
        for k,v in report.items():
            report[k] = [self.__rdict(r) for r in v]
        return self.ok(report)

    def __rdict(self, report):
        """
        Serialized report dict.
        @param report: A applicability report object.
        @type report: ApplicabilityReport
        @return: A dictionary representation of the report.
        @rtype: dict
        """
        return dict(
            unit=report.unit,
            applicable=report.applicable,
            summary=report.summary,
            details=report.details)


# -- web.py application -------------------------------------------------------


urls = (
    '/$', 'ConsumersCollection',
    '/search/$', 'ConsumerSearch', # resource search
    '/([^/]+)/$', 'ConsumerResource',
    '/([^/]+)/bindings/$', 'Bindings',
    '/([^/]+)/bindings/([^/]+)/$', 'Bindings',
    '/([^/]+)/bindings/([^/]+)/([^/]+)/$', 'Binding',
    '/([^/]+)/profiles/$', 'Profiles',
    '/([^/]+)/profiles/([^/]+)/$', 'Profile',
    '/([^/]+)/actions/content/(install|update|uninstall)/$', 'Content',
    '/actions/content/applicability/$', 'ContentApplicability',
    '/([^/]+)/history/$', 'ConsumerHistory',  
)

application = web.application(urls, globals())
