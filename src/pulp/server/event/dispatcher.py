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
Contains QPID event classes.
"""

import os
from pulp.server.event import *
from pulp.messaging.consumer import EventConsumer
from threading import RLock as Mutex
import pulp.server.event.handler as hpx
from logging import getLogger

log = getLogger(__name__)
mutex = Mutex()
flags = EventFlags()


# decorator workspace for correlating
# methods to classes.
_method = ({},{})


def handler(entity):
    """
    Event handler decorator.
    Associate a handler class with an entity.
    @param entity: The I{entity} part of an AMQP subject.
    @type entity: str
    """
    def decorator(cls):
        mutex.acquire()
        try:
            global _method
            EventDispatcher.register(
                entity,
                cls,
                _method[0],
                _method[1])
            _method = ({},{})
        finally:
            mutex.release()
        return cls
    return decorator

def inbound(action):
    """
    Event (inbound) method decorator.
    Associate a handler method with an action.
    @param action: The I{action} part of an AMQP subject.
    @type action: str
    """
    def decorator(fn):
        mutex.acquire()
        try:
            _method[0][action] = fn
        finally:
            mutex.release()
        return fn
    return decorator

def outbound(action):
    """
    Event (inbound) method decorator.
    Associate a handler method with an action.
    @param action: The I{action} part of an AMQP subject.
    @type action: str
    """
    def decorator(fn):
        mutex.acquire()
        try:
            _method[1][action] = fn
        finally:
            mutex.release()
        return fn
    return decorator

def event(subject):
    """
    The decorator for API methods.
    Using the dispatcher, an event is resied when the method is invoked.
    The I{noevent} param specifies whether an event should be raised.
    Used mostly by the I{inbound} event handlers.
    @param subject: An AMQP subject form: <entity>.<action>.
    @type subject: str
    """
    def decorator(fn):
        def call(*args, **kwargs):
            retval = fn(*args, **kwargs)
            if not flags.suspended(subject):
                entity, action = subject.split('.',1)
                inst, method = \
                    EventDispatcher.handler(entity, outbound=action)
                method(inst, *args, **kwargs)
            return retval
        return call
    return decorator


class Handler:
    """
    Handler specification.
    @ivar hclass: The handler class name.
    @type hclass: str
    @ivar ibmethod: registered I{inbound} methods.
    @type ibmethod: method
    @ivar obmethod: registered I{outbound} methods.
    @type obmethod: method
    """

    def __init__(self, hclass, inbound, outbound):
        """
        @param hclass: The handler class name.
        @type hclass: str
        @param ibmethod: registered I{inbound} methods.
        @type ibmethod: method
        @param obmethod: registered I{outbound} methods.
        @type obmethod: method
        """
        self.hclass = hclass
        self.ibmethod = inbound
        self.obmethod = outbound

    def inst(self):
        """
        Get an instance of the handler.
        @return: An instance of the handler.
        @rtype: L{EventHandler}
        """
        return self.hclass()

    def inbound(self, action):
        """
        Find  the I{inbound} method for the specified action.
        @param action: An event subject action.
        @type action: str
        @return: The method registered for the (inbound) action.
        @rtype: method
        """
        method = self.ibmethod.get(action)
        if method:
            return method
        raise Exception,\
            'handler %s has not method registered for (inbound) action: %s' %\
            (self.hclass.__name__,
            action)

    def outbound(self, action):
        """
        Find the I{outbound} method for the specified action.
        @param action: An event subject action.
        @type action: str
        @return: The method registered for the (outbound) action.
        @rtype: method
        """
        method = self.obmethod.get(action)
        if method:
            return method
        raise Exception,\
            'handler %s has not method registered for (outbound) action: %s' %\
            (self.hclass.__name__,
            action)


class EventDispatcher(EventConsumer):
    """
    The main event dispatcher.
    Dispatches events by subject to the registered handler.
    @cvar handlers: Registered event handler classes.
        Key: entity.
    @type handlers: dict
    """

    handlers = {}

    def __init__(self):
        EventConsumer.__init__(self, None)

    def start(self):
        EventConsumer.start(self)
        log.info('Event dispatcher - started.')

    @classmethod
    def register(cls, entity, hclass, inbound, outbound):
        """
        Register a handler.
        @param entity: The entity name.
        @type entity: str
        @param hclass: The handler class.
        @param hclass: class
        @param inbound: The I{inbound} method mappings.
        @type inbound: dict
        @param outbound: The I{outbound} method mappings.
        @type outbound: dict
        """
        cls.handlers[entity] = \
            Handler(hclass, inbound, outbound)

    @classmethod
    def load(cls):
        """
        Load handlers.
        """
        mutex.acquire()
        try:
            if cls.handlers:
                return
            loader = DynLoader(hpx)
            loader.load()
        finally:
            mutex.release()

    @classmethod
    def handler(cls, entity, inbound=None, outbound=None):
        """
        Get a handler class associated with the specified entity.
        @param entity: The I{entity} part of an AMQP subject.
        @type entity: str
        @param inbound: The I{inbound} action.
        @type inbound: str
        @param outbound: The I{outbound} action.
        @type outbound: str
        @return: The handler instance and method based on whether the
            I{inbound} or I{outbound} param is specified.
        @rtype: tuple (inst,method)
        """
        mutex.acquire()
        try:
            cls.load()
            handler = cls.handlers.get(entity)
            if handler is None:
                raise Exception,\
                    'handler for entity "%s", not found' % entity
            inst = handler.inst()
            if inbound:
                method = handler.inbound(inbound)
            else:
                method = handler.outbound(outbound)
            return (inst, method)
        finally:
            mutex.release()

    def raised(self, subject, event):
        """
        Entry point (callback) for received AMQP events.
        The event is dispatched to the registered handler and the
        I{inbound} method is called.
        @param subject: The event (message) subject used for routing.
        @type subject: str
        @param event: The event payload.
        @type event: dict
        """
        try:
            log.info('received event (%s): %s',
                subject,
                event)
            entity, action = subject.split('.',1)
            inst, method = self.handler(entity, inbound=action)
            log.info('dispatching event (%s): %s\n to handler: %s.%s()',
                subject,
                event,
                inst.__class__,
                method.__name__)
            flags.suspend(subject)
            try:
                method(inst, event)
            finally:
                flags.resume(subject)
        except:
            log.error('{inbound} event failed (%s):\n%s',
                subject,
                event,
                exc_info=True)


class EventHandler:
    """
    The event handler base class.
    """
    pass


class DynLoader:
    """
    A dynamic module loader.
    @ivar pkg: A package object.
    @type pkg: python module
    """

    def __init__(self, pkg):
        """
        @param pkg: A package object.
        @type pkg: python module
        """
        self.pkg = pkg

    def load(self):
        """
        Load all modules within the package.
        """
        loaded = []
        path = os.path.dirname(self.pkg.__file__)
        for fn in os.listdir(path):
            if fn.startswith('__'):
                continue
            mod, ext = fn.rsplit('.',1)
            if mod in loaded:
                continue
            part = path.split('/')
            part.append(mod)
            self.__import(part[1:])
            loaded.append(mod)

    def __import(self, path):
        """
        Import modules the the specified path.
        @param path: A list of path elements.
        @type path: list
        """
        for i in range(0, len(path)):
            mod = '.'.join(path[i:])
            try:
                __import__(mod)
                log.info('%s - imported.', mod)
                return # succeeded
            except:
                pass
        raise ImportError, '.'.join(path)
