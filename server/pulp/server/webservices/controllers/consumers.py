"""
This module contains the consumer related web controllers.
"""
from web.webapi import BadRequest
import web

from pulp.common import tags
from pulp.server.async.tasks import TaskResult
from pulp.server.auth.authorization import READ, CREATE, UPDATE, DELETE
from pulp.server.db.model.criteria import Criteria
from pulp.server.exceptions import InvalidValue, MissingValue, OperationPostponed, \
    UnsupportedValue, MissingResource
from pulp.server.managers.consumer.applicability import (regenerate_applicability_for_consumers,
                                                         retrieve_consumer_applicability)
from pulp.server.managers.schedule.consumer import UNIT_INSTALL_ACTION, UNIT_UNINSTALL_ACTION, \
    UNIT_UPDATE_ACTION
from pulp.server.tasks import consumer
from pulp.server.webservices import serialization
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import auth_required
from pulp.server.webservices.controllers.search import SearchController
import pulp.server.managers.factory as managers


def expand_consumers(options, consumers):
    """
    Expand a list of users based on flags specified in the
    post body or query parameters.  The _href is always added by the
    serialization function used.
    Supported options:
      details - synonym for: (bindings=True,)
      bindings - include bindings
    @param options: The (expanding) options.
    @type options: dict
    @param consumers: A list of consumers
    @type consumers: list
    @return: A list of expanded consumers.
    @rtype: list
    """
    if options.get('details', False):
        options['bindings'] = True
    # add bindings
    if options.get('bindings', False):
        ids = [c['id'] for c in consumers]
        manager = managers.consumer_bind_manager()
        criteria = Criteria({'consumer_id': {'$in': ids}})
        bindings = manager.find_by_criteria(criteria)
        collated = {}
        for b in bindings:
            lst = collated.setdefault(b['consumer_id'], [])
            lst.append(b)
        for _consumer in consumers:
            _consumer['bindings'] = \
                [serialization.binding.serialize(b, False)
                    for b in collated.get(_consumer['id'], [])]
    return consumers


class Consumers(JSONController):

    @auth_required(READ)
    def GET(self):
        params = web.input()
        manager = managers.consumer_query_manager()
        consumers = expand_consumers(params, manager.find_all())
        for c in consumers:
            href = serialization.link.child_link_obj(c['id'])
            c.update(href)
        return self.ok(consumers)

    @auth_required(CREATE)
    def POST(self):
        body = self.params()
        consumer_id = body.get('id')
        display_name = body.get('display_name')
        description = body.get('description')
        notes = body.get('notes')
        rsa_pub = body.get('rsa_pub')

        manager = managers.consumer_manager()

        created, certificate = manager.register(
            consumer_id,
            display_name=display_name,
            description=description,
            notes=notes,
            rsa_pub=rsa_pub)

        link = serialization.link.child_link_obj(consumer_id)
        created.update({'_href': link})

        document = {
            'consumer': created,
            'certificate': certificate
        }

        return self.created(link['_href'], document)


class Consumer(JSONController):

    @auth_required(READ)
    def GET(self, id):
        params = web.input()
        manager = managers.consumer_manager()
        consumer = manager.get_consumer(id)
        consumer = expand_consumers(params, [consumer])[0]
        href = serialization.link.current_link_obj()
        consumer.update(href)
        return self.ok(consumer)

    @auth_required(DELETE)
    def DELETE(self, id):
        manager = managers.consumer_manager()
        return self.ok(manager.unregister(id))

    @auth_required(UPDATE)
    def PUT(self, id):
        body = self.params()
        delta = body.get('delta')
        manager = managers.consumer_manager()
        consumer = manager.update(id, delta)
        href = serialization.link.current_link_obj()
        consumer.update(href)
        return self.ok(consumer)


class ConsumerSearch(SearchController):

    def __init__(self):
        super(ConsumerSearch, self).__init__(
            managers.consumer_query_manager().find_by_criteria)

    def GET(self):
        params = web.input()
        ignored = ('details', 'bindings')
        found = self._get_query_results_from_get(ignored)
        consumers = expand_consumers(params, found)
        for c in consumers:
            href = serialization.link.search_safe_link_obj(c['id'])
            c.update(href)
        return self.ok(consumers)

    def POST(self):
        body = self.params()
        found = self._get_query_results_from_post()
        consumers = expand_consumers(body, found)
        for c in consumers:
            href = serialization.link.search_safe_link_obj(c['id'])
            c.update(href)
        return self.ok(consumers)


class Bindings(JSONController):
    """
    Consumer bindings represents the collection of
    objects used to associate a consumer and a repo-distributor
    association.  Users wanting to create this association will
    create an object in this collection.  Both bind and unbind
    is idempotent.
    """

    @auth_required(READ)
    def GET(self, consumer_id, repo_id=None):
        """
        Fetch all bind objects referencing the specified consumer_id. Optionally,
        specify a repo_id to fetch all bind objects for the consumer_id to the repo_id

        :param consumer_id: The specified consumer.
        :type  consumer_id: str
        :param repo_id:     The repository to retrieve bindings for (optional)
        :type  repo_id:     str

        :return: A list of dictionaries that represent pulp.server.db.model.consumer.Bind objects
        :rtype:  list
        """
        # Check to make sure the resources exist
        missing_resources = {}
        if repo_id is not None:
            repo = managers.repo_query_manager().find_by_id(repo_id)
            if repo is None:
                missing_resources['repo_id'] = repo_id
        # If get_consumer raises MissingResource we might miss reporting a bad repo_id
        try:
            managers.consumer_manager().get_consumer(consumer_id)
        except MissingResource:
            missing_resources['consumer_id'] = consumer_id

        if len(missing_resources) > 0:
            raise MissingResource(**missing_resources)

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
        Designed to be idempotent so only MissingResource is expected to
        be raised by manager.
        @param consumer_id: The consumer to bind.
        @type consumer_id: str
        @return: A call_report
        @rtype: TaskResult
        """
        # get other options and validate them
        body = self.params()
        repo_id = body.get('repo_id')
        distributor_id = body.get('distributor_id')
        binding_config = body.get('binding_config', {})
        options = body.get('options', {})
        notify_agent = body.get('notify_agent', True)

        if not isinstance(binding_config, dict):
            raise BadRequest()

        call_report = consumer.bind(
            consumer_id, repo_id, distributor_id, notify_agent, binding_config, options)

        if call_report.spawned_tasks:
            raise OperationPostponed(call_report)
        else:
            return self.ok(call_report.serialize())


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
        @return: A call_report
        @rtype: TaskResult
        """
        body = self.params()
        forced = body.get('force', False)
        options = body.get('options', {})
        if forced:
            call_report = consumer.force_unbind(consumer_id, repo_id, distributor_id, options)
        else:
            call_report = consumer.unbind(consumer_id, repo_id, distributor_id, options)

        if call_report.spawned_tasks:
            raise OperationPostponed(call_report)
        else:
            return self.ok(call_report.serialize())


class BindingSearch(SearchController):
    """
    Bind search.
    """
    def __init__(self):
        SearchController.__init__(self, managers.consumer_bind_manager().find_by_criteria)


class Content(JSONController):
    """
    Represents a specific bind object.
    """

    @auth_required(CREATE)
    def POST(self, consumer_id, action):
        """
        Content actions.
        """
        method = getattr(self, action, None)
        if method:
            return method(consumer_id)
        else:
            raise BadRequest()

    def install(self, consumer_id):
        """
        Install content (units) on a consumer.
        Expected body: {units:[], options:<dict>}
        where unit is: {type_id:<str>, unit_key={}} and the
        options is a dict of install options.
        :param consumer_id: A consumer ID.
        :type consumer_id: str
        """
        body = self.params()
        missing_params = []
        units = body.get('units')
        if units is None:
            missing_params.append('units')
        options = body.get('options')
        if options is None:
            missing_params.append('options')

        if len(missing_params) > 0:
            raise MissingValue(missing_params)

        agent_manager = managers.consumer_agent_manager()
        task = agent_manager.install_content(consumer_id, units, options)
        raise OperationPostponed(TaskResult.from_task_status_dict(task))

    def update(self, consumer_id):
        """
        Update content (units) on a consumer.
        Expected body: {units:[], options:<dict>}
        where unit is: {type_id:<str>, unit_key={}} and the
        options is a dict of update options.
        @param consumer_id: A consumer ID.
        @type consumer_id: str
        """
        body = self.params()
        missing_params = []
        units = body.get('units')
        if units is None:
            missing_params.append('units')
        options = body.get('options')
        if options is None:
            missing_params.append('options')

        if len(missing_params) > 0:
            raise MissingValue(missing_params)

        agent_manager = managers.consumer_agent_manager()
        task = agent_manager.update_content(consumer_id, units, options)
        raise OperationPostponed(TaskResult.from_task_status_dict(task))

    def uninstall(self, consumer_id):
        """
        Uninstall content (units) on a consumer.
        Expected body: {units:[], options:<dict>}
        where unit is: {type_id:<str>, unit_key={}} and the
        options is a dict of uninstall options.
        @param consumer_id: A consumer ID.
        @type consumer_id: str
        """
        body = self.params()
        missing_params = []
        units = body.get('units')
        if units is None:
            missing_params.append('units')
        options = body.get('options')
        if options is None:
            missing_params.append('options')

        if len(missing_params) > 0:
            raise MissingValue(missing_params)

        agent_manager = managers.consumer_agent_manager()
        task = agent_manager.uninstall_content(consumer_id, units, options)
        raise OperationPostponed(TaskResult.from_task_status_dict(task))


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

        results = managers.consumer_history_manager().query(consumer_id=id,
                                                            event_type=event_type,
                                                            limit=limit,
                                                            sort=sort,
                                                            start_date=start_date,
                                                            end_date=end_date)

        if results:
            return self.ok(results)
        else:
            return self.not_found()


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
        # Check that the consumer exists and raise a MissingResource exception, in case it doesn't.
        managers.consumer_manager().get_consumer(consumer_id)

        manager = managers.consumer_profile_manager()
        profiles = manager.get_profiles(consumer_id)
        profiles = [serialization.consumer.profile(p) for p in profiles]
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

        manager = managers.consumer_profile_manager()
        new_profile = manager.create(consumer_id, content_type, profile)
        link = serialization.link.child_link_obj(consumer_id, content_type)
        new_profile.update(link)
        return self.created(link['_href'], new_profile)


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
        serialized = serialization.consumer.profile(profile)
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

        manager = managers.consumer_profile_manager()
        consumer = manager.update(consumer_id, content_type, profile)

        link = serialization.link.child_link_obj(consumer_id, content_type)
        consumer.update(link)

        return self.ok(consumer)

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
        return self.ok(manager.delete(consumer_id, content_type))


class ProfileSearch(SearchController):
    """
    Profile search.
    """
    def __init__(self):
        SearchController.__init__(self, managers.consumer_profile_manager().find_by_criteria)


class ContentApplicability(JSONController):
    """
    Query content applicability.
    """
    @auth_required(READ)
    def POST(self):
        """
        Query content applicability for a given consumer criteria query.

        body {criteria: <object>,
              content_types: <array>[optional]}

        This method returns a JSON document containing an array of objects that each have two
        keys: 'consumers', and 'applicability'. 'consumers' will index an array of consumer_ids,
        for consumers that have the same repository bindings and profiles. 'applicability' will
        index an object that will have keys for each content type that is applicable, and the
        content type ids will index the applicability data for those content types. For example,

        [{'consumers': ['consumer_1', 'consumer_2'],
          'applicability': {'content_type_1': ['unit_1', 'unit_3']}},
         {'consumers': ['consumer_2', 'consumer_3'],
          'applicability': {'content_type_1': ['unit_1', 'unit_2']}}]

        :return: applicability data matching the consumer criteria query
        :rtype:  str
        """
        # Get the consumer_ids that match the consumer criteria query that the requestor queried
        # with, and build a map from consumer_id to a dict with profiles and repo_ids for each
        # consumer
        try:
            consumer_criteria = self._get_consumer_criteria()
            content_types = self._get_content_types()
        except InvalidValue, e:
            return self.bad_request(str(e))

        return self.ok(retrieve_consumer_applicability(consumer_criteria, content_types))

    def _get_consumer_criteria(self):
        """
        Process the POST data, finding the criteria given by the user, and resolve it to Criteria
        object.

        :return: A Criteria object
        :rtype:  pulp.server.db.model.criteria.Criteria
        """
        body = self.params()

        try:
            consumer_criteria = body.get('criteria')
        except AttributeError:
            raise InvalidValue('The input to this method must be a JSON object with a '
                               "'criteria' key.")
        consumer_criteria = Criteria.from_client_input(consumer_criteria)
        return consumer_criteria

    def _get_content_types(self):
        """
        Get the list of content_types that the caller wishes to limit the response to. If the
        caller did not include content types, this will return None.

        :return: The list of content_types that the applicability query should be limited to,
                 or None if not specified
        :rtype:  list or None
        """
        body = self.params()

        content_types = body.get('content_types', None)
        if content_types is not None and not isinstance(content_types, list):
            raise InvalidValue('content_types must index an array.')

        return content_types


class ContentApplicabilityRegeneration(JSONController):
    """
    Content applicability regeneration for updated consumers.
    """
    @auth_required(CREATE)
    def POST(self):
        """
        Creates an async task to regenerate content applicability data for given consumers.

        body {consumer_criteria:<dict>}
        """
        body = self.params()
        consumer_criteria = body.get('consumer_criteria', None)
        if consumer_criteria is None:
            raise MissingValue('consumer_criteria')
        try:
            consumer_criteria = Criteria.from_client_input(consumer_criteria)
        except:
            raise InvalidValue('consumer_criteria')

        task_tags = [tags.action_tag('content_applicability_regeneration')]
        async_result = regenerate_applicability_for_consumers.apply_async_with_reservation(
            tags.RESOURCE_REPOSITORY_PROFILE_APPLICABILITY_TYPE, tags.RESOURCE_ANY_ID,
            (consumer_criteria.as_dict(),), tags=task_tags)
        raise OperationPostponed(async_result)


class ConsumerContentApplicabilityRegeneration(JSONController):
    """
    Content applicability regeneration for a given consumer. Since our permission model is closely
    tied to API URIs, this is a separate API than the one above, so that individual consumers can
    request applicability generation for themselves.
    """
    @auth_required(CREATE)
    def POST(self, consumer_id):
        """
        Creates an async task to regenerate content applicability data for given consumer.

        :param consumer_id: The consumer ID.
        :type consumer_id: basestring
        """
        consumer_query_manager = managers.consumer_query_manager()
        if consumer_query_manager.find_by_id(consumer_id) is None:
            raise MissingResource(consumer_id=consumer_id)
        consumer_criteria = Criteria(filters={'consumer_id': consumer_id})

        task_tags = [tags.action_tag('consumer_content_applicability_regeneration')]
        async_result = regenerate_applicability_for_consumers.apply_async_with_reservation(
            tags.RESOURCE_CONSUMER_TYPE,
            consumer_id,
            (consumer_criteria.as_dict(),),
            tags=task_tags)
        raise OperationPostponed(async_result)


class UnitActionScheduleCollection(JSONController):
    ACTION = None

    def __init__(self):
        super(UnitActionScheduleCollection, self).__init__()
        self.manager = managers.consumer_schedule_manager()

    @auth_required(READ)
    def GET(self, consumer_id):
        manager = managers.consumer_schedule_manager()
        schedules = manager.get(consumer_id, self.ACTION)

        schedule_objs = []
        for schedule in schedules:
            obj = serialization.dispatch.scheduled_unit_management_obj(
                schedule.for_display())
            obj.update(serialization.link.child_link_obj(obj['_id']))
            schedule_objs.append(obj)

        # this behavior is debatable, but I'm keeping it for backward-compatibility.
        if not schedule_objs:
            raise MissingResource(schedule=None)
        return self.ok(schedule_objs)

    @auth_required(CREATE)
    def POST(self, consumer_id):
        params = self.params()
        units = params.pop('units', None)
        options = params.pop('options', {})
        schedule = params.pop('schedule', None)
        failure_threshold = params.pop('failure_threshold', None)
        enabled = params.pop('enabled', True)
        if params:
            raise UnsupportedValue(params.keys())

        scheduled_call = self.manager.create_schedule(
            self.ACTION, consumer_id, units, options, schedule, failure_threshold, enabled)

        scheduled_obj = serialization.dispatch.scheduled_unit_management_obj(
            scheduled_call.for_display())
        scheduled_obj.update(serialization.link.child_link_obj(scheduled_call.id))
        return self.created(scheduled_obj['_href'], scheduled_obj)


class UnitActionScheduleResource(JSONController):
    ACTION = None

    def __init__(self):
        super(UnitActionScheduleResource, self).__init__()
        self.manager = managers.consumer_schedule_manager()

    @auth_required(READ)
    def GET(self, consumer_id, schedule_id):
        scheduled_call = None
        for call in self.manager.get(consumer_id, self.ACTION):
            if call.id == schedule_id:
                scheduled_call = call
                break
        if scheduled_call is None:
            raise MissingResource(consumer_id=consumer_id, schedule_id=schedule_id)

        scheduled_obj = serialization.dispatch.scheduled_unit_management_obj(
            scheduled_call.for_display())
        scheduled_obj.update(serialization.link.current_link_obj())
        return self.ok(scheduled_obj)

    @auth_required(UPDATE)
    def PUT(self, consumer_id, schedule_id):
        schedule_data = self.params()
        options = schedule_data.pop('options', None)
        units = schedule_data.pop('units', None)

        if 'schedule' in schedule_data:
            schedule_data['iso_schedule'] = schedule_data.pop('schedule')

        schedule = self.manager.update_schedule(consumer_id, schedule_id, units,
                                                options, schedule_data)

        scheduled_obj = serialization.dispatch.scheduled_unit_management_obj(schedule.for_display())
        scheduled_obj.update(serialization.link.current_link_obj())
        return self.ok(scheduled_obj)

    @auth_required(DELETE)
    def DELETE(self, consumer_id, schedule_id):
        self.manager.delete_schedule(consumer_id, schedule_id)
        return self.ok(None)


class UnitInstallScheduleCollection(UnitActionScheduleCollection):
    ACTION = UNIT_INSTALL_ACTION


class UnitInstallScheduleResource(UnitActionScheduleResource):
    ACTION = UNIT_INSTALL_ACTION


class UnitUpdateScheduleCollection(UnitActionScheduleCollection):
    ACTION = UNIT_UPDATE_ACTION


class UnitUpdateScheduleResource(UnitActionScheduleResource):
    ACTION = UNIT_UPDATE_ACTION


class UnitUninstallScheduleCollection(UnitActionScheduleCollection):
    ACTION = UNIT_UNINSTALL_ACTION


class UnitUninstallScheduleResource(UnitActionScheduleResource):
    ACTION = UNIT_UNINSTALL_ACTION

# -- web.py application -------------------------------------------------------

urls = (
    '/$', Consumers,
    '/actions/content/regenerate_applicability/$', ContentApplicabilityRegeneration,
    '/binding/search/$', BindingSearch,
    '/content/applicability/$', ContentApplicability,
    '/profile/search/$', ProfileSearch,
    '/search/$', ConsumerSearch,
    '/([^/]+)/actions/content/regenerate_applicability/$', ConsumerContentApplicabilityRegeneration,
    '/([^/]+)/bindings/$', Bindings,
    '/([^/]+)/bindings/([^/]+)/$', Bindings,
    '/([^/]+)/bindings/([^/]+)/([^/]+)/$', Binding,
    '/([^/]+)/profiles/$', Profiles,
    '/([^/]+)/profiles/([^/]+)/$', Profile,
    '/([^/]+)/schedules/content/install/', UnitInstallScheduleCollection,
    '/([^/]+)/schedules/content/install/([^/]+)/', UnitInstallScheduleResource,
    '/([^/]+)/schedules/content/update/', UnitUpdateScheduleCollection,
    '/([^/]+)/schedules/content/update/([^/]+)/', UnitUpdateScheduleResource,
    '/([^/]+)/schedules/content/uninstall/', UnitUninstallScheduleCollection,
    '/([^/]+)/schedules/content/uninstall/([^/]+)/', UnitUninstallScheduleResource,
    '/([^/]+)/actions/content/(install|update|uninstall)/$', Content,
    '/([^/]+)/history/$', ConsumerHistory,
    '/([^/]+)/$', Consumer,
)

application = web.application(urls, globals())
