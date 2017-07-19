from logging import getLogger


log = getLogger(__name__)


class Event:
    """
    An (abstract) download event.

    Attributes:

        download (pulpcore.download.Download): A download object on which the
            event occurred.
    """

    # Event
    PREPARED = 'PREPARED'
    SENT = 'SENT'
    REPLIED = 'REPLIED'
    FETCHED = 'FETCHED'
    SUCCEEDED = 'SUCCEEDED'
    FAILED = 'FAILED'
    ERROR = 'ERROR'

    NAME = ''

    def __init__(self, download):
        """
        Args:
            download (pulpcore.download.Download): A download object on which the
                event occurred.
        """
        self.download = download

    def __str__(self):
        return str(self.__dict__)


class Prepared(Event):
    """
    The download has been prepared.
    """

    NAME = Event.PREPARED


class Sent(Event):
    """
    The download request has been sent.
    """

    NAME = Event.SENT


class Replied(Event):
    """
    The download has received a reply.
    """

    NAME = Event.REPLIED


class Succeeded(Event):
    """
    The download has succeeded.
    """

    NAME = Event.SUCCEEDED


class Failed(Event):
    """
    The download has failed.
    """

    NAME = Event.FAILED


class Error(Event):
    """
    The download has experienced an error.
    The handler has the opportunity to "repair" the download so that
    it can be retried.

    Attributes:
        download (pulpcore.download.Download): A download object on which the
            event occurred.
        repaired (bool): Indicates whether the handler has repaired
            the download and it should be retried.
    """

    NAME = Event.ERROR

    def __init__(self, download, error):
        """
        Args:
            download (pulpcore.download.Download): A download object on which the
                event occurred.
            error (Exception): The error that occurred.
        """
        super().__init__(download)
        self.error = error
        self.repaired = False


class Fetched(Event):
    """
    A buffer has been fetched.

    Attributes:
        download (pulpcore.download.Download): A download object on which the
            event occurred.
        buffer (bytes): A fetched buffer.
    """

    NAME = Event.FETCHED

    def __init__(self, download, buffer):
        """
        Args:
            download (pulpcore.download.Download): A download object on which the
                event occurred.
            buffer (bytes): A fetched buffer.
        """
        super().__init__(download)
        self.buffer = buffer


class EventRouter:
    """
    Provides event handler registration and forwarding of raised
    events to registered handlers.

    Attributes:
        handler (dict): Mapping of Event classes to handlers.
    """

    def __init__(self):
        self.handler = {}

    def register(self, event, handler):
        """
        Register a handler to receive events.

        The *handler* is a callable that takes a single (Event) argument.

        Args:
            event (str): The event name that the handler is interested in.
            handler (callable): A callable registered to receive the event.

        Examples:
            >>>
            >>> def on_error(event):
            >>>     ...
            >>> router = ..
            >>> router.register(Event.ERROR, on_error)
            >>>

        See Also:
            Event
        """
        self.handler.setdefault(event, []).append(handler)

    def send(self, event):
        """
        Send an event to all registered handlers.
        Exceptions raised by handlers are logged and swallowed.

        Args:
            event (Event): The raised event object.

        Returns:
            (Event): The sent event.
        """
        for handler in self.handler.get(event.NAME, tuple()):
            try:
                handler(event)
            except Exception:
                log.exception(str(event))
        return event
