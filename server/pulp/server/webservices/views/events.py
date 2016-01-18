from django.core.urlresolvers import reverse
from django.views.generic import View

from pulp.server.auth import authorization
from pulp.server.managers import factory
from pulp.server.webservices.views.decorators import auth_required
from pulp.server.webservices.views.util import (generate_json_response,
                                                generate_json_response_with_pulp_encoder,
                                                generate_redirect_response,
                                                parse_json_body)


class EventView(View):
    """
    Views for event listeners.
    """

    @auth_required(authorization.READ)
    def get(self, request):
        """
        List all event listeners.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest

        :return: Response containing a list of events
        :rtype: django.http.HttpResponse
        """
        manager = factory.event_listener_manager()
        events = manager.list()

        for event in events:
            add_link(event)
        return generate_json_response_with_pulp_encoder(events)

    @auth_required(authorization.CREATE)
    @parse_json_body(json_type=dict)
    def post(self, request):
        """
        Create a new event listener.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest

        :return: Response containing the event listener
        :rtype: django.http.HttpResponse
        """
        params = request.body_as_json

        notifier_type_id = params.get('notifier_type_id', None)
        notifier_config = params.get('notifier_config', None)
        event_types = params.get('event_types', None)

        manager = factory.event_listener_manager()
        event = manager.create(notifier_type_id, notifier_config, event_types)

        link = add_link(event)

        response = generate_json_response_with_pulp_encoder(event)
        redirect_response = generate_redirect_response(response, link['_href'])
        return redirect_response


class EventResourceView(View):
    """
    Views for a single event listener.
    """

    @auth_required(authorization.READ)
    def get(self, request, event_listener_id):
        """
        Retrieve a specific event listener.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param event_listener_id: id for the requested event listener
        :type event_listener_id: str

        :return: Response containing the event listener
        :rtype: django.http.HttpResponse
        """
        manager = factory.event_listener_manager()

        event = manager.get(event_listener_id)  # will raise MissingResource
        add_link(event)
        return generate_json_response_with_pulp_encoder(event)

    @auth_required(authorization.DELETE)
    def delete(self, request, event_listener_id):
        """
        Delete an event listener.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param event_listener_id: id for the requested event listener
        :type event_listener_id: str

        :return: An empty response
        :rtype: django.http.HttpResponse
        """
        manager = factory.event_listener_manager()

        manager.delete(event_listener_id)  # will raise MissingResource
        return generate_json_response(None)

    @auth_required(authorization.UPDATE)
    @parse_json_body(allow_empty=True, json_type=dict)
    def put(self, request, event_listener_id):
        """
        Update a specific event listener.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param event_listener_id: id for the requested event listener
        :type event_listener_id: str

        :return: Response containing the event listener
        :rtype: django.http.HttpResponse
        """
        params = request.body_as_json

        notifier_config = params.get('notifier_config', None)
        event_types = params.get('event_types', None)

        manager = factory.event_listener_manager()
        event = manager.update(event_listener_id, notifier_config=notifier_config,
                               event_types=event_types)
        add_link(event)
        return generate_json_response_with_pulp_encoder(event)


def add_link(event):
    link = {'_href': reverse('event_resource',
            kwargs={'event_listener_id': event['id']})}
    event.update(link)
    return link
