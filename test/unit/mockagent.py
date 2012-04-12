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

from pulp.server.gc_agent import pulpagent
from pulp.server.dispatch import factory


def install():
    pulpagent.Rest = MockRest
    

class MockRest:
    
    def get(self, path):
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
            Class = path[5]
            Method = path[6]
            inst = globals()[Class]()
            return getattr(inst, Method)
        except KeyError:
            raise Exception, '%s, not mocked' % Class
        except AttributeError:
            raise Exception, '%s, not mocked' % Method
        
    
class Consumer(object):
    """
    Mock consumer API domain.
    """

    def unregistered(self):
        return (200, None)
    
    def bind(self, repoid):
        return (200, repoid)
    
    def unbind(self, repoid):
        return (200, repoid)


class Content(object):
    """
    Mock content API domain.
    """
    
    def install(self, units, options):
        return (202, (units, options))
    
    def update(self, units, options):
        return (202, (units, options))
    
    def uninstall(self, units, options):
        return (202, (units, options))


class Profile(object):
    """
    Mock profile API domain.
    """
    
    def send(self):
        return (200, None)