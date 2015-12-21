from unittest import TestCase

from mock import Mock

from pulp.server.content.sources.event import Listener, Event, Started, Succeeded, Failed


ALL_EVENT = (Started, Succeeded, Failed)


class TestEvent(TestCase):

    def test_init(self):
        name = 'test'
        request = 123
        event = Event(name, request)
        self.assertEqual(event.name, name)
        self.assertEqual(event.request, request)

    def test_call(self):
        name = 'test'
        request = 123
        listener = Mock()
        event = Event(name, request)
        event(listener)
        listener.on_event.assert_called_once_with(event)

    def test_call_none(self):
        name = 'test'
        request = 123
        listener = None
        event = Event(name, request)
        event(listener)

    def test_call_raised(self):
        name = 'test'
        request = 123
        listener = Mock()
        listener.on_event.side_effect = ValueError()
        event = Event(name, request)
        event(listener)
        listener.on_event.assert_called_once_with(event)

    def test_concrete(self):
        request = 123
        for T in ALL_EVENT:
            event = T(request)
            self.assertEqual(event.name, T.NAME)
            self.assertEqual(event.request, request)


class TestListener(TestCase):

    class Test(Listener):
        def __init__(self):
            for T in ALL_EVENT:
                method = 'on_{t}'.format(t=T.NAME)
                setattr(self, method, Mock())

    def test_just_coverage(self):
        listener = Listener()
        listener.on_started(123)
        listener.on_succeeded(123)
        listener.on_failed(123)

    def test_on_event(self):
        request = Mock()
        for T in ALL_EVENT:
            event = T(request)
            listener = TestListener.Test()
            listener.on_event(event)
            name = 'on_{t}'.format(t=T.NAME)
            method = getattr(listener, name)
            method.assert_called_once_with(request)

    def test_on_event_raised(self):
        listener = TestListener.Test()
        listener.on_started(side_effect=ValueError)
        listener.on_event(Started(123))

    def test_on_event_no_method(self):
        listener = TestListener.Test()
        listener.on_event(Mock(name='foo'))
