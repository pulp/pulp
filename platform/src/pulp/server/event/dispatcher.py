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
Contains QPID event classes.
"""

import os
import imp
import inspect
from pulp.server.event import *
from pulp.server.event.consumer import EventConsumer
from threading import RLock as Mutex
from pulp.server.config import config
import pulp.server.event.handler as hpx
from logging import getLogger

log = getLogger(__name__)
mutex = Mutex()
flags = EventFlags()


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
            fn.inbound = action
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
            fn.outbound = action
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
        if config.getboolean('events', 'send_enabled'):
            return call
        else:
            return fn
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
    @cvar loaded: Flag indicating the handlers have been loaded.
    @type loaded: bool
    """

    handlers = {}
    loaded = False

    def __init__(self):
        EventConsumer.__init__(self, None)

    def start(self):
        EventConsumer.start(self)
        log.info('Event dispatcher - started.')

    @classmethod
    def register(cls, entity, hclass):
        """
        Register a handler.
        Find decorated functions and use them to associate
        methods to actions.
        @param entity: The entity name.
        @type entity: str
        @param hclass: The handler class.
        @param hclass: class
        """
        mutex.acquire()
        try:
            inbound = {}
            outbound = {}
            for name, method in inspect.getmembers(hclass, inspect.ismethod):
                fn = method.im_func
                if hasattr(fn, 'inbound'):
                    inbound[fn.inbound] = method
                    continue
                if hasattr(fn, 'outbound'):
                    outbound[fn.outbound] = method
                    continue
            cls.handlers[entity] = \
                Handler(hclass, inbound, outbound)
        finally:
            mutex.release()

    @classmethod
    def load(cls):
        """
        Load handlers.
        """
        mutex.acquire()
        try:
            if cls.loaded:
                return
            loader = DynLoader(hpx)
            loader.load()
            cls.loaded = True
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

    EXTS = ('py',)

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
            if not self.valid(ext):
                continue
            modpath = os.path.join(path, fn)
            imp.load_source(mod, modpath)
            log.info('module: %s at: %s, loaded', mod, modpath)
            loaded.append(mod)

    def valid(self, ext):
        """
        Validate extenson
        @param ext: an extension.
        @type ext: str
        @return: True if valid.
        @rtype: bool
        """
        return ( ext in self.EXTS )
