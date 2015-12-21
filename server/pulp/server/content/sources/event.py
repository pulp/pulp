from gettext import gettext as _
from logging import getLogger


log = getLogger(__name__)


EVENT_FAILED = _('Listener error on event: {event}')


class Event(object):
    """
    Base event.

    :ivar name: The event name.
    :type name: str
    :ivar request: A download request.
    :type request: pulp.server.content.sources.model.Request
    """

    def __init__(self, name, request):
        """
        :param name: The event name.
        :type name: str
        :param request: A download request.
        :type request: pulp.server.content.sources.model.Request
        """
        self.name = name
        self.request = request

    def __call__(self, listener):
        """
        Raise the event on the listener by calling Listener.on_event().

        :param listener: The target of the event.
        :type listener: Listener
        """
        try:
            listener.on_event(self)
        except AttributeError:
            pass
        except Exception:
            log.exception(EVENT_FAILED.format(event=self.name))


class Started(Event):
    """
    The download started event.
    """

    NAME = 'started'

    def __init__(self, request):
        """
        :param request: A download request.
        :type request: pulp.server.content.sources.model.Request
        """
        super(Started, self).__init__(self.NAME, request)


class Succeeded(Event):
    """
    The download has succeeded event.
    """

    NAME = 'succeeded'

    def __init__(self, request):
        """
        :param request: A download request.
        :type request: pulp.server.content.sources.model.Request
        """
        super(Succeeded, self).__init__(self.NAME, request)


class Failed(Event):
    """
    The download failed event.
    """

    NAME = 'failed'

    def __init__(self, request):
        """
        :param request: A download request.
        :type request: pulp.server.content.sources.model.Request
        """
        super(Failed, self).__init__(self.NAME, request)


class Listener(object):
    """
    Download event listener.
    """

    def on_started(self, request):
        """
        Notification that downloading has started for the specified request.

        :param request: A download request.
        :type request: pulp.server.content.sources.model.Request
        """
        pass

    def on_succeeded(self, request):
        """
        Notification that downloading has succeeded for the specified request.

        :param request: A download request.
        :type request: pulp.server.content.sources.model.Request
        """
        pass

    def on_failed(self, request):
        """
        Notification that downloading has failed for the specified request.

        :param request: A download request.
        :type request: pulp.server.content.sources.model.Request
        """
        pass

    def on_event(self, event):
        """
        Event notification.
        Safely Mapped to method with the same name as the event.
        Listener classes can override and handle events directly.

        :param event: An event.
        :type event: Event
        """
        name = 'on_{event}'.format(event=event.name)
        try:
            method = getattr(self, name)
            method(event.request)
        except AttributeError:
            pass
