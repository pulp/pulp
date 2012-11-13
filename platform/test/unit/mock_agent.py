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

from mock import Mock
from gofer.rmi import mock as mock
from pulp.server.agent.direct.services import Services, HeartbeatListener
from pulp.server.agent.hub import pulpagent as restagent
from pulp.agent.lib.report import DispatchReport
from pulp.server.compat import json


def install():
    reset()
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
    Consumer.reset()
    Content.reset()
    Profile.reset()

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
        return (202, result)

    def method(self, path):
        try:
            Class = path[5]
            Method = path[6]
            inst = globals()[Class]()
            return getattr(inst, Method)
        except KeyError:
            raise Exception, '%s, not mocked' % Class
        except AttributeError:
            raise Exception, '%s, not mocked' % Method


def dispatch(*args):
    # test json serialization
    for a in args:
        json.dumps(a)
    # return a dispatch report
    r = DispatchReport()
    return r.dict()

#
# Capabilities
#

class Consumer(object):
    """
    Mock consumer capability.
    """
    
    @classmethod
    def reset(cls):
        cls.bind.reset_mock()
        cls.unbind.reset_mock()
        cls.unregistered.reset_mock()

    bind = Mock(side_effect=dispatch)
    unbind = Mock(side_effect=dispatch)
    unregistered = Mock()


class Content(object):
    """
    Mock content capability.
    """
    
    @classmethod
    def reset(cls):
        cls.install.reset_mock()
        cls.update.reset_mock()
        cls.uninstall.reset_mock()

    install = Mock(side_effect=dispatch)
    update = Mock(side_effect=dispatch)
    uninstall = Mock(side_effect=dispatch)


class Profile(object):
    """
    Mock profile capability.
    """
    
    @classmethod
    def reset(cls):
        cls.send.reset_mock()

    send = Mock(side_effect=dispatch)