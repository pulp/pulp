#!/usr/bin/python
#
# Copyright (c) 2011 Red Hat, Inc.
#
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
# Contains agent (gofer) mocks used for testing.
# Most only do argument checking.  Add additional functionality
# as needed.
#

from gofer.rmi import mock
from pulp.server.gc_agent.direct.services import Services, HeartbeatListener
from pulp.server.gc_agent.hub import pulpagent as restagent
from pulp.gc_client.agent.lib.report import DispatchReport
from pulp.server.dispatch import factory


def install():
    restagent.Rest = MockRest
    Services.heartbeat_listener = HeartbeatListener(None)
    mock.install()
    mock.reset()
    mock.register(
        Consumer=Consumer,
        Content=Content,
        Profile=Profile)

def reset():
    mock.reset()

def all():
    return mock.all()
    

class MockRest:
    
    def get(self, path):
        # status
        parts = path.split('/')
        if len(parts) == 5:
            return (200, {})
        raise Exception, 'GET: unhandled path: %s' % path
    
    def post(self, path, body):
        path = path.split('/')
        if path[4] == 'call':
            return self.call(path, body)
        # unknown
        raise Exception, 'POST: unhandled path: %s' % path
        
    def call(self, path, body):
        method = self.method(path)
        options = body['options']
        request = body['request']
        args = request['args']
        kwargs = request['kwargs']
        taskid = options.get('any')
        result = method(*args, **kwargs)
        if taskid and result[0] == 202:
            self.notify_coordinator(taskid, result)
        return result
    
    def notify_coordinator(self, taskid, result):
        # TODO: notify coordinator
        pass

    def method(self, path):
        try:
            Class = 'Rest'+path[5]
            Method = path[6]
            inst = globals()[Class]()
            return getattr(inst, Method)
        except KeyError:
            raise Exception, '%s, not mocked' % Class
        except AttributeError:
            raise Exception, '%s, not mocked' % Method

#
# Capabilities
#

#
# Direct Impl
#

class Consumer(object):
    """
    Mock consumer capability.
    """

    def unregistered(self):
        pass

    def bind(self, repoid):
        pass

    def rebind(self):
        pass

    def unbind(self, repoid):
        pass


class Content(object):
    """
    Mock content capability.
    """

    def install(self, units, options):
        report = DispatchReport()
        report.details = \
            dict(units=units, options=options)
        return report.dict()

    def update(self, units, options):
        report = DispatchReport()
        report.details = \
            dict(units=units, options=options)
        return report.dict()

    def uninstall(self, units, options):
        report = DispatchReport()
        report.details = \
            dict(units=units, options=options)
        return report.dict()


class Profile(object):
    """
    Mock profile capability.
    """

    def send(self):
        pass

#
# Agenthub Impl
#

class RestConsumer(object):
    """
    Mock consumer capability.
    """

    def unregistered(self):
        return (202, None)
    
    def bind(self, repoid):
        return (202, repoid)
    
    def rebind(self):
        return (202, None)

    def unbind(self, repoid):
        return (202, repoid)


class RestContent(object):
    """
    Mock content capability.
    """
    
    def install(self, units, options):
        report = DispatchReport()
        report.details = \
            dict(units=units, options=options)
        return (202, report.dict())
    
    def update(self, units, options):
        report = DispatchReport()
        report.details = \
            dict(units=units, options=options)
        return (202, report.dict())
    
    def uninstall(self, units, options):
        report = DispatchReport()
        report.details = \
            dict(units=units, options=options)
        return (202, report.dict())


class RestProfile(object):
    """
    Mock profile capability.
    """
    
    def send(self):
        return (202, None)