from django.core.urlresolvers import reverse
from django.http import HttpResponseBadRequest
from django.views.generic import View

from pulp.common import tags
from pulp.server.async.tasks import TaskResult
from pulp.server.auth import authorization
from pulp.server.db.model.criteria import Criteria
from pulp.server.exceptions import (InvalidValue, MissingResource, MissingValue,
                                    OperationPostponed, UnsupportedValue)
from pulp.server.managers import factory
from pulp.server.managers.consumer import bind
from pulp.server.managers.consumer import profile
from pulp.server.managers.consumer import query as query_manager
from pulp.server.managers.consumer.applicability import (regenerate_applicability_for_consumers,
                                                         retrieve_consumer_applicability)
from pulp.server.managers.schedule.consumer import (UNIT_INSTALL_ACTION, UNIT_UNINSTALL_ACTION,
                                                    UNIT_UPDATE_ACTION)
from pulp.server.tasks import consumer as consumer_task
from pulp.server.webservices.views import search
from pulp.server.webservices.views.decorators import auth_required
from pulp.server.webservices.views.serializers import binding as serial_binding
from pulp.server.webservices.views.util import (_ensure_input_encoding,
                                                generate_json_response,
                                                generate_json_response_with_pulp_encoder,
                                                generate_redirect_response,
                                                json_body_required,
                                                json_body_allow_empty)


def add_link(consumer):
    """
    Add link to the consumer object.

    :param consumer: consumer object
    :type consumer: dict

    :return: link containing the href
    :rtype: dict
    """

    link = {'_href': reverse('consumer_resource',
            kwargs={'consumer_id': consumer['id']})}
    consumer.update(link)
    return link


def add_link_profile(consumer):
    """
    Add link to the consumer profile object.

    :param consumer: consumer profile object
    :type consumer: dict

    :return: link containing the href
    :rtype: dict
    """

    link = {'_href': reverse('consumer_profile_resource',
            kwargs={'consumer_id': consumer['consumer_id'],
                    'content_type': consumer['content_type']})}
    consumer.update(link)
    return link


def add_link_schedule(schedule, action_type, consumer_id):
    """
    Add link to the schedule object.

    :param schedule: schedule object
    :type schedule: dict
    :param action_type: action type to perform
    :type action_type: str
    :param consumer_id: id of the consumer
    :type consumer_id: str

    :return: link containing the href
    :rtype: dict
    """

    action = action_type.split("_")[-1]
    link = {'_href': reverse('schedule_content_%s_resource' % action,
            kwargs={'consumer_id': consumer_id,
                    'schedule_id': schedule['_id']})}
    schedule.update(link)
    return link


def scheduled_unit_management_obj(scheduled_call):
    """
    Modify scheduled unit management object.

    :param scheduled_call: scheduled unit manag. object
    :type scheduled_call: dict

    :return: updated scheduled unit manag. object
    :rtype: updated scheduled unit manag. object
    """

    scheduled_call['options'] = scheduled_call['kwargs']['options']
    scheduled_call['units'] = scheduled_call['kwargs']['units']
    return scheduled_call


def expand_consumers(details, bindings, consumers):
    """
    Expand a list of users based on the flag specified in the query parameters.
    The _href is always added by the serialization function used.
    Supported options:
      details - include details
      bindings - include bindings

    :param details: if True, details will be included in the response
    :type  details: bool
    :param bindings:    if True, bindings will be included with each returned consumer
    :type  bindings:    bool
    :param consumers: A list of consumers
    :type consumers: list

    :return: A list of expanded consumers.
    :rtype: list
    """

    if details:
        bindings = True
    # add bindings
    if bindings:
        ids = [c['id'] for c in consumers]
        manager = factory.consumer_bind_manager()
        criteria = Criteria({'consumer_id': {'$in': ids}})
        bindings = manager.find_by_criteria(criteria)
        collated = {}
        for b in bindings:
            lst = collated.setdefault(b['consumer_id'], [])
            lst.append(b)
        for c in consumers:
            c['bindings'] = [
                serial_binding.serialize(b, False) for b in collated.get(c['id'], [])
            ]
    return consumers


class ConsumersView(View):
    """
    View for consumers.
    """

    @auth_required(authorization.READ)
    def get(self, request):
        """
        List the available consumers.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest

        :return: Response containing a list of consumers
        :rtype: django.http.HttpResponse
        """

        query_params = request.GET
        details = query_params.get('details', 'false').lower() == 'true'
        bindings = query_params.get('bindings', 'false').lower() == 'true'

        manager = factory.consumer_query_manager()
        consumers = expand_consumers(details, bindings, manager.find_all())
        for consumer in consumers:
            add_link(consumer)
        return generate_json_response_with_pulp_encoder(consumers)

    @auth_required(authorization.CREATE)
    @json_body_required
    def post(self, request):
        """
        Create a consumer and return a serialized object containing just created consumer.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest

        :raises MissingValue: if ID is not provided

        :return: Response containing the consumer
        :rtype: django.http.HttpResponse
        """

        params = request.body_as_json
        consumer_id = params.get('id')
        if consumer_id is None:
            raise MissingValue(['id'])
        display_name = params.get('display_name')
        description = params.get('description')
        notes = params.get('notes')
        rsa_pub = params.get('rsa_pub')

        manager = factory.consumer_manager()

        consumer, certificate = manager.register(
            consumer_id,
            display_name=display_name,
            description=description,
            notes=notes,
            rsa_pub=rsa_pub)

        link = add_link(consumer)

        document = {
            'consumer': consumer,
            'certificate': certificate
        }
        response = generate_json_response_with_pulp_encoder(document)
        redirect_response = generate_redirect_response(response, link['_href'])
        return redirect_response


class ConsumerResourceView(View):
    """
    View for single consumer.
    """

    @auth_required(authorization.READ)
    def get(self, request, consumer_id):
        """
        Return a serialized object representing the requested consumer.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param consumer_id: id for the requested consumer
        :type consumer_id: str

        :return: Response containing data for the requested consumer
        :rtype: django.http.HttpResponse
        """

        query_params = request.GET
        details = query_params.get('details', 'false').lower() == 'true'
        bindings = query_params.get('bindings', 'false').lower() == 'true'

        manager = factory.consumer_manager()
        consumer = manager.get_consumer(consumer_id)
        consumer = expand_consumers(details, bindings, [consumer])[0]
        add_link(consumer)
        return generate_json_response_with_pulp_encoder(consumer)

    @auth_required(authorization.DELETE)
    def delete(self, request, consumer_id):
        """
        Delete a specified consumer.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param consumer_id: id for the requested consumer
        :type consumer_id: str

        :return: An empty response
        :rtype: django.http.HttpResponse
        """

        manager = factory.consumer_manager()
        response = manager.unregister(consumer_id)
        return generate_json_response(response)

    @auth_required(authorization.UPDATE)
    @json_body_required
    def put(self, request, consumer_id):
        """
        Update a specified consumer.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param consumer_id: id for the requested consumer
        :type consumer_id: str

        :return: Response representing the updated consumer
        :rtype: django.http.HttpResponse
        """

        params = request.body_as_json
        delta = params.get('delta')
        manager = factory.consumer_manager()
        consumer = manager.update(consumer_id, delta)
        add_link(consumer)
        return generate_json_response_with_pulp_encoder(consumer)


class ConsumerSearchView(search.SearchView):
    """
    This view provides GET and POST searching for Consumers.
    """
    optional_bool_fields = ('details', 'bindings')
    response_builder = staticmethod(generate_json_response_with_pulp_encoder)
    manager = query_manager.ConsumerQueryManager()

    @classmethod
    def get_results(cls, query, search_method, options, *args):
        """
        This overrides the base class implementation so we can include optional information.

        :param query: The criteria that should be used to search for objects
        :type  query: dict
        :param search_method: function that should be used to search
        :type  search_method: func
        :param options: additional options for including extra data. In this case, this can contain
                        only 'details' and 'bindings' as keys.
        :type  options: dict

        :return: results, expanded and serialized
        :rtype:  list
        """
        results = list(search_method(query))
        results = expand_consumers(options.get('details', False),
                                   options.get('bindings', False),
                                   results)
        for consumer in results:
            add_link(consumer)
        return results


class ConsumerBindingSearchView(search.SearchView):
    """
    This view provides GET and POST searching for Consumer Bindings.
    """
    response_builder = staticmethod(generate_json_response_with_pulp_encoder)
    manager = bind.BindManager()


class ConsumerProfileSearchView(search.SearchView):
    """
    This view provides GET and POST searching for Consumer Profiles.
    """
    response_builder = staticmethod(generate_json_response_with_pulp_encoder)
    manager = profile.ProfileManager()


class ConsumerBindingsView(View):
    """
    View for Consumer bindings - represents the collection of
    objects used to associate a consumer and a repo-distributor
    association.  Users wanting to create this association will
    create an object in this collection.  Both bind and unbind
    is idempotent.
    """

    @auth_required(authorization.READ)
    def get(self, request, consumer_id, repo_id=None):
        """
        Fetch all bind objects referencing the specified consumer_id. Optionally,
        specify a repo_id to fetch all bind objects for the consumer_id to the repo_id.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param consumer_id: The specified consumer.
        :type  consumer_id: str
        :param repo_id: The repository to retrieve bindings for (optional)
        :type  repo_id: str

        :raises MissingResource: if some resource is missing

        :return: Response representing the bindings
        :rtype: django.http.HttpResponse
        """

        # Check to make sure the resources exist
        missing_resources = {}
        if repo_id is not None:
            repo = factory.repo_query_manager().find_by_id(repo_id)
            if repo is None:
                missing_resources['repo_id'] = repo_id
        # If get_consumer raises MissingResource we might miss reporting a bad repo_id
        try:
            factory.consumer_manager().get_consumer(consumer_id)
        except MissingResource:
            missing_resources['consumer_id'] = consumer_id

        if missing_resources:
            raise MissingResource(**missing_resources)

        manager = factory.consumer_bind_manager()
        bindings = manager.find_by_consumer(consumer_id, repo_id)
        bindings = [serial_binding.serialize(b) for b in bindings]
        return generate_json_response_with_pulp_encoder(bindings)

    @auth_required(authorization.CREATE)
    @json_body_required
    def post(self, request, consumer_id):
        """
        Create a bind association between the specified
        consumer by id included in the URL path and a repo-distributor
        specified in the POST body: {repo_id:<str>, distributor_id:<str>}.
        Designed to be idempotent so only MissingResource is expected to
        be raised by manager.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param consumer_id: consumer to bind.
        :type  consumer_id: str

        :raises OperationPostponed: will dispatch a task if 'notify_agent' is set to True
        :raises InvalidValue: if binding_config is invalid

        :return: Response representing the binding(in case 'notify agent' is set to False)
        :rtype: django.http.HttpResponse
        """

        # get other options and validate them
        body = request.body_as_json
        repo_id = body.get('repo_id')
        distributor_id = body.get('distributor_id')
        binding_config = body.get('binding_config', {})
        options = body.get('options', {})
        notify_agent = body.get('notify_agent', True)

        if not isinstance(binding_config, dict):
            raise InvalidValue(['binding_config'])

        call_report = consumer_task.bind(
            consumer_id, repo_id, distributor_id, notify_agent, binding_config, options)

        if call_report.spawned_tasks:
            raise OperationPostponed(call_report)
        else:
            return generate_json_response_with_pulp_encoder(call_report.serialize())


class ConsumerBindingResourceView(View):
    """
    Represents a specific bind resource.
    """

    @auth_required(authorization.READ)
    def get(self, request, consumer_id, repo_id, distributor_id):
        """
        Fetch a specific bind object which represents a specific association
        between a consumer and repo-distributor.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param consumer_id: A consumer ID.
        :type consumer_id: str
        :param repo_id: A repo ID.
        :type repo_id: str
        :param distributor_id: A distributor ID.
        :type distributor_id: str

        :return: Response representing the binding
        :rtype: django.http.HttpResponse
        """

        manager = factory.consumer_bind_manager()
        bind = manager.get_bind(consumer_id, repo_id, distributor_id)
        serialized_bind = serial_binding.serialize(bind)
        return generate_json_response_with_pulp_encoder(serialized_bind)

    @auth_required(authorization.DELETE)
    @json_body_allow_empty
    def delete(self, request, consumer_id, repo_id, distributor_id):
        """
        Delete a bind association between the specified
        consumer and repo-distributor.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param consumer_id: A consumer ID.
        :type consumer_id: str
        :param repo_id: A repo ID.
        :type repo_id: str
        :param distributor_id: A distributor ID.
        :type distributor_id: str

        :raises OperationPostponed: will dispatch a task if 'notify_agent' is set to True
        :raises InvalidValue: if some parameters are invalid

        :return: Response representing the deleted binding(in case 'notify agent' is set to False)
        :rtype: django.http.HttpResponse
        """

        body = request.body_as_json
        forced = body.get('force', False)
        if not isinstance(forced, bool):
            raise InvalidValue(['force'])
        options = body.get('options', {})
        if not isinstance(options, dict):
            raise InvalidValue(['options'])
        if forced:
            call_report = consumer_task.force_unbind(consumer_id, repo_id, distributor_id, options)
        else:
            call_report = consumer_task.unbind(consumer_id, repo_id, distributor_id, options)

        if call_report.spawned_tasks:
            raise OperationPostponed(call_report)
        else:
            return generate_json_response_with_pulp_encoder(call_report.serialize())


class ConsumerContentActionView(View):
    """
    Views for content manipulation on the consumer.
    """

    @auth_required(authorization.CREATE)
    @json_body_required
    def post(self, request, consumer_id, action):
        """
        Install/update/uninstall content unit/s on the consumer.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param consumer_id: A consumer ID.
        :type consumer_id: str
        :param action: type of action to perform
        :type action: str

        :raises MissingResource: if consumer id does not exist
        :raises MissingValue: if some required values are missing
        """

        method = getattr(self, action, None)
        if method:
            try:
                factory.consumer_manager().get_consumer(consumer_id)
            except MissingResource:
                raise MissingResource(consumer_id=consumer_id)
            else:
                body = request.body_as_json
                missing_params = []
                units = body.get('units')
                if units is None:
                    missing_params.append('units')
                options = body.get('options')
                if options is None:
                    missing_params.append('options')

                if missing_params:
                    raise MissingValue(missing_params)
            return method(request, consumer_id, units, options)
        else:
            return HttpResponseBadRequest('bad request')

    def install(self, request, consumer_id, units, options):
        """
        Install content (units) on a consumer.

        Expected body: {units:[], options:<dict>}
        where unit is: {type_id:<str>, unit_key={}} and the
        options is a dict of install options.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param consumer_id: A consumer ID.
        :type consumer_id: str
        :param units: units to install
        :type units: list
        :param options: install options
        :type options: dict

        :raises OperationPostponed: when an async operation is performed.
        """

        agent_manager = factory.consumer_agent_manager()
        task = agent_manager.install_content(consumer_id, units, options)
        raise OperationPostponed(TaskResult.from_task_status_dict(task))

    def update(self, request, consumer_id, units, options):
        """
        Update content (units) on a consumer.

        Expected body: {units:[], options:<dict>}
        where unit is: {type_id:<str>, unit_key={}} and the
        options is a dict of update options.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param consumer_id: A consumer ID.
        :type consumer_id: str
        :param units: units to install
        :type units: list
        :param options: install options
        :type options: dict

        :raises OperationPostponed: when an async operation is performed.
        """

        agent_manager = factory.consumer_agent_manager()
        task = agent_manager.update_content(consumer_id, units, options)
        raise OperationPostponed(TaskResult.from_task_status_dict(task))

    def uninstall(self, request, consumer_id, units, options):
        """
        Uninstall content (units) on a consumer.

        Expected body: {units:[], options:<dict>}
        where unit is: {type_id:<str>, unit_key={}} and the
        options is a dict of uninstall options.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param consumer_id: A consumer ID.
        :type consumer_id: str
        :param units: units to install
        :type units: list
        :param options: install options
        :type options: dict

        :raises OperationPostponed: when an async operation is performed.
        """

        agent_manager = factory.consumer_agent_manager()
        task = agent_manager.uninstall_content(consumer_id, units, options)
        raise OperationPostponed(TaskResult.from_task_status_dict(task))


class ConsumerHistoryView(View):
    """
    View for consumer history retrieval.
    """

    @auth_required(authorization.READ)
    def get(self, request, consumer_id):
        """
        Retrieve histroy for the specified consumer

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param consumer_id: A consumer ID.
        :type consumer_id: str

        :return: Response representing the binding
        :rtype: django.http.HttpResponse
        """

        # Check that the consumer exists and raise a MissingResource exception, in case it doesn't.
        factory.consumer_manager().get_consumer(consumer_id)

        query_param = request.GET
        filters = _ensure_input_encoding(query_param)
        event_type = filters.get('event_type', None)
        limit = filters.get('limit', None)
        sort = filters.get('sort', 'descending')
        start_date = filters.get('start_date', None)
        end_date = filters.get('end_date', None)

        if limit:
            try:
                limit = int(limit)
            except ValueError:
                raise InvalidValue('limit')

        results = factory.consumer_history_manager().query(consumer_id=consumer_id,
                                                           event_type=event_type,
                                                           limit=limit,
                                                           sort=sort,
                                                           start_date=start_date,
                                                           end_date=end_date)
        return generate_json_response_with_pulp_encoder(results)


class ConsumerProfilesView(View):
    """
    View Consumer profiles represents the collection of
    objects used to associate consumers and installed content
    unit profiles.
    """

    @auth_required(authorization.READ)
    def get(self, request, consumer_id):
        """
        Get all profiles associated with a consumer.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param consumer_id: A consumer ID.
        :type consumer_id: str

        :return: Response representing list of profiles
        :rtype: django.http.HttpResponse
        """

        # Check that the consumer exists and raise a MissingResource exception, in case it doesn't.
        factory.consumer_manager().get_consumer(consumer_id)

        manager = factory.consumer_profile_manager()
        profiles = manager.get_profiles(consumer_id)
        for consumer_profile in profiles:
            add_link_profile(consumer_profile)
        return generate_json_response_with_pulp_encoder(profiles)

    @auth_required(authorization.CREATE)
    @json_body_required
    def post(self, request, consumer_id):
        """
        Associate a profile with a consumer by content type ID.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param consumer_id: A consumer ID.
        :type consumer_id: str

        :raises MissingValue: if some parameter were not provided

        :return: Response representing the created profile
        :rtype: django.http.HttpResponse
        """

        body = request.body_as_json
        content_type = body.get('content_type')
        profile = body.get('profile')

        manager = factory.consumer_profile_manager()
        new_profile = manager.create(consumer_id, content_type, profile)
        if content_type is None:
            raise MissingValue('content_type')
        link = add_link_profile(new_profile)
        response = generate_json_response_with_pulp_encoder(new_profile)
        redirect_response = generate_redirect_response(response, link['_href'])
        return redirect_response


class ConsumerProfileResourceView(View):
    """
    View Consumer profiles represents the collection of
    objects used to associate consumer and installed content
    unit profiles.
    """

    @auth_required(authorization.READ)
    def get(self, request, consumer_id, content_type):
        """
        Get profile by content type associated with consumer.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param consumer_id: The consumer ID.
        :type consumer_id: str
        :param content_type: The content type
        :type consumer_id: str

        :return: Response representing consumer's profile
        :rtype: django.http.HttpResponse
        """

        manager = factory.consumer_profile_manager()
        profile = manager.get_profile(consumer_id, content_type)
        add_link_profile(profile)
        return generate_json_response_with_pulp_encoder(profile)

    @auth_required(authorization.UPDATE)
    @json_body_required
    def put(self, request, consumer_id, content_type):
        """
        Update the association of a profile with a consumer by content type ID.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param consumer_id: A consumer ID.
        :type consumer_id: str
        :param content_type: A content unit type ID.
        :type content_type: str

        :return: Response representing the updated profile
        :rtype: django.http.HttpResponse
        """

        body = request.body_as_json
        profile = body.get('profile')

        manager = factory.consumer_profile_manager()
        consumer = manager.update(consumer_id, content_type, profile)

        add_link_profile(consumer)

        return generate_json_response_with_pulp_encoder(consumer)

    @auth_required(authorization.DELETE)
    def delete(self, request, consumer_id, content_type):
        """
        Delete an association between the specified
        consumer and profile.  Designed to be idempotent.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param consumer_id: A consumer ID.
        :type consumer_id: str
        :param content_type: The content type ID.
        :type content_type: str

        :return: An empty response
        :rtype: django.http.HttpResponse
        """

        manager = factory.consumer_profile_manager()
        response = manager.delete(consumer_id, content_type)
        return generate_json_response(response)


class ConsumerContentApplicabilityView(View):
    """
    View for query content applicability.
    """
    @auth_required(authorization.READ)
    @json_body_required
    def post(self, request):
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

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest

        :return: Response containing applicability data matching the consumer criteria query
        :rtype:  jango.http.HttpResponse
        """

        # Get the consumer_ids that match the consumer criteria query that the requestor queried
        # with, and build a map from consumer_id to a dict with profiles and repo_ids for each
        # consumer
        try:
            consumer_criteria = self._get_consumer_criteria(request)
            content_types = self._get_content_types(request)
        except InvalidValue, e:
            return HttpResponseBadRequest(str(e))

        response = retrieve_consumer_applicability(consumer_criteria, content_types)
        return generate_json_response_with_pulp_encoder(response)

    def _get_consumer_criteria(self, request):
        """
        Process the POST data, finding the criteria given by the user, and resolve it to Criteria
        object.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest

        :raises InvalidValue: if some parameters were invalid

        :return: A Criteria object
        :rtype:  pulp.server.db.model.criteria.Criteria
        """

        body = request.body_as_json

        consumer_criteria = body.get('criteria')
        if consumer_criteria is None:
            raise InvalidValue("The input to this method must be a JSON object with a "
                               "'criteria' key.")
        consumer_criteria = Criteria.from_client_input(consumer_criteria)
        return consumer_criteria

    def _get_content_types(self, request):
        """
        Get the list of content_types that the caller wishes to limit the response to. If the
        caller did not include content types, this will return None.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest

        :raises InvalidValue: if some parameters were invalid

        :return: The list of content_types that the applicability query should be limited to,
                 or None if not specified
        :rtype:  list or None
        """

        body = request.body_as_json

        content_types = body.get('content_types', None)
        if content_types is not None and not isinstance(content_types, list):
            raise InvalidValue('content_types must index an array.')

        return content_types


class ConsumerContentApplicRegenerationView(View):
    """
    Content applicability regeneration for updated consumers.
    """

    @auth_required(authorization.CREATE)
    @json_body_required
    def post(self, request):
        """
        Creates an async task to regenerate content applicability data for given consumers.

        body {consumer_criteria:<dict>}

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest

        :raises MissingValue: if some parameters are missing
        :raises InvalidValue: if some parameters are invalid
        :raises OperationPostponed: when an async operation is performed.
        """

        body = request.body_as_json
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


class ConsumerResourceContentApplicRegenerationView(View):
    """
    View Content applicability regeneration for a given consumer.
    """

    @auth_required(authorization.CREATE)
    @json_body_allow_empty
    def post(self, request, consumer_id):
        """
        Creates an async task to regenerate content applicability data for given consumer.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param consumer_id: The consumer ID.
        :type consumer_id: str

        :raises MissingResource: if some parameters are missing
        :raises OperationPostponed: when an async operation is performed.
        """

        consumer_query_manager = factory.consumer_query_manager()
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


class ConsumerUnitActionSchedulesView(View):
    """
    View for scheduled content manipulation on the consumer.
    """

    ACTION = None

    def __init__(self):
        super(ConsumerUnitActionSchedulesView, self).__init__()
        self.manager = factory.consumer_schedule_manager()

    @auth_required(authorization.READ)
    def get(self, request, consumer_id):
        """
        List schedules <action>.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param consumer_id: The consumer ID.
        :type consumer_id: str

        :raises MissingResource: if consumer does not exist

        :return: Response containing consumer's schedules <action>
        :rtype: django.http.HttpResponse
        """

        try:
            factory.consumer_manager().get_consumer(consumer_id)
        except MissingResource:
            raise MissingResource(consumer_id=consumer_id)
        schedules = self.manager.get(consumer_id, self.ACTION)

        schedule_objs = []
        for schedule in schedules:
            obj = scheduled_unit_management_obj(schedule.for_display())
            add_link_schedule(obj, self.ACTION, consumer_id)
            schedule_objs.append(obj)

        return generate_json_response_with_pulp_encoder(schedule_objs)

    @auth_required(authorization.CREATE)
    @json_body_required
    def post(self, request, consumer_id):
        """
        Create a schedule.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param consumer_id: The consumer ID.
        :type consumer_id: str

        :raises UnsupportedValue: if some extra unsupported keys were specified.

        :return: Response containing just created schedule
        :rtype: django.http.HttpResponse
        """

        params = request.body_as_json
        units = params.pop('units', None)
        options = params.pop('options', {})
        schedule = params.pop('schedule', None)
        failure_threshold = params.pop('failure_threshold', None)
        enabled = params.pop('enabled', True)
        if params:
            raise UnsupportedValue(params.keys())
        scheduled_call = self.manager.create_schedule(
            self.ACTION, consumer_id, units, options, schedule, failure_threshold, enabled)

        scheduled_obj = scheduled_unit_management_obj(scheduled_call.for_display())
        link = add_link_schedule(scheduled_obj, self.ACTION, consumer_id)
        response = generate_json_response_with_pulp_encoder(scheduled_obj)
        redirect_response = generate_redirect_response(response, link['_href'])
        return redirect_response


class ConsumerUnitActionScheduleResourceView(View):
    """
    View for a single scheduled consumer unit action.
    """

    ACTION = None

    def __init__(self):
        super(ConsumerUnitActionScheduleResourceView, self).__init__()
        self.manager = factory.consumer_schedule_manager()

    @auth_required(authorization.READ)
    def get(self, request, consumer_id, schedule_id):
        """
        List a specific schedule <action>.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param consumer_id: The consumer ID.
        :type consumer_id: str
        :param schedule_id: the schedule id
        :type schedule_id: str

        :raises MissingResource: if consumer/schedule does not exist

        :return: Response containing consumer's schedule <action>
        :rtype: django.http.HttpResponse
        """

        scheduled_call = None
        for call in self.manager.get(consumer_id, self.ACTION):
            if call.id == schedule_id:
                scheduled_call = call
                break
        if scheduled_call is None:
            raise MissingResource(consumer_id=consumer_id, schedule_id=schedule_id)

        scheduled_obj = scheduled_unit_management_obj(scheduled_call.for_display())
        add_link_schedule(scheduled_obj, self.ACTION, consumer_id)
        return generate_json_response_with_pulp_encoder(scheduled_obj)

    @auth_required(authorization.UPDATE)
    @json_body_allow_empty
    def put(self, request, consumer_id, schedule_id):
        """
        Update a specific schedule <action>.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param consumer_id: The consumer ID.
        :type consumer_id: str
        :param schedule_id: the schedule id
        :type schedule_id: str

        :return: Response containing consumer's updated schedule <action>
        :rtype: django.http.HttpResponse
        """

        schedule_data = request.body_as_json
        options = schedule_data.pop('options', None)
        units = schedule_data.pop('units', None)

        if 'schedule' in schedule_data:
            schedule_data['iso_schedule'] = schedule_data.pop('schedule')

        schedule = self.manager.update_schedule(consumer_id, schedule_id, units,
                                                options, schedule_data)

        scheduled_obj = scheduled_unit_management_obj(schedule.for_display())
        add_link_schedule(scheduled_obj, self.ACTION, consumer_id)
        return generate_json_response_with_pulp_encoder(scheduled_obj)

    @auth_required(authorization.DELETE)
    def delete(self, request, consumer_id, schedule_id):
        """
        Delete a specific schedule <action>.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param consumer_id: The consumer ID.
        :type consumer_id: str
        :param schedule_id: the schedule id
        :type schedule_id: str

        :return: An empty response
        :rtype: django.http.HttpResponse
        """

        self.manager.delete_schedule(consumer_id, schedule_id)
        return generate_json_response(None)


class UnitInstallSchedulesView(ConsumerUnitActionSchedulesView):
    """
    View for scheduled content install on the consumer.
    """

    ACTION = UNIT_INSTALL_ACTION


class UnitInstallScheduleResourceView(ConsumerUnitActionScheduleResourceView):
    """
    View for a single scheduled consumer unit install.
    """

    ACTION = UNIT_INSTALL_ACTION


class UnitUpdateSchedulesView(ConsumerUnitActionSchedulesView):
    """
    View for scheduled content update on the consumer.
    """

    ACTION = UNIT_UPDATE_ACTION


class UnitUpdateScheduleResourceView(ConsumerUnitActionScheduleResourceView):
    """
    View for a single scheduled consumer unit update.
    """

    ACTION = UNIT_UPDATE_ACTION


class UnitUninstallSchedulesView(ConsumerUnitActionSchedulesView):
    """
    View for scheduled content uninstall on the consumer.
    """

    ACTION = UNIT_UNINSTALL_ACTION


class UnitUninstallScheduleResourceView(ConsumerUnitActionScheduleResourceView):
    """
    View for a single scheduled consumer unit uninstall.
    """

    ACTION = UNIT_UNINSTALL_ACTION
