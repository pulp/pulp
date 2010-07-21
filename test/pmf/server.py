#! /usr/bin/env python
#
# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: Jeff Ortel <jortel@redhat.com>
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

import sys
sys.path.append('../../')

from pmf.stub import Stub
from pmf.decorators import stub
from pmf.base import Container
from pmf.producer import QueueProducer
from pmf.window import *
from time import sleep
from datetime import datetime as dt
from datetime import timedelta as delta
from logging import INFO, basicConfig

basicConfig(filename='/tmp/pmf.log', level=INFO)

@stub('repolib')
class RepoLib(Stub):
    pass

@stub('dog')
class Dog(Stub):
    pass


class Agent(Container):

    def __init__(self, id, **options):
        producer = QueueProducer()
        Container.__init__(self, id, producer, **options)


def demo(agent):
    print agent.dog.bark('hello')
    print agent.dog.wag(3)
    print agent.dog.bark('hello again')
    print agent.repolib.update()
    try:
        print agent.repolib.updated()
    except Exception, e:
        print repr(e)
    try:
        print agent.dog.notpermitted()
    except Exception, e:
        print repr(e)

def later(**offset):
    return dt.utcnow()+delta(**offset)

if __name__ == '__main__':
    # synchronous
    print '(demo) synchronous'
    agent = Agent('123')
    demo(agent)
    agent = None

    # asynchronous (fire and forget)
    print '(demo) asynchronous fire-and-forget'
    agent = Agent('123', async=True)
    demo(agent)

    # asynchronous
    print '(demo) asynchronous'
    tag = 'xyz'
    window = Window(begin=dt.utcnow(), minutes=1)
    agent = Agent('123', ctag=tag, window=window)
    demo(agent)

    # asynchronous
    print '(demo) group asynchronous'
    tag = 'xyz'
    group = ('123', 'ABC',)
    window = Window(begin=dt.utcnow(), minutes=1)
    agent = Agent(group, ctag=tag)
    demo(agent)

    # future
    print 'maintenance window'

    # group 2
    print 'group 2'
    begin = later(seconds=20)
    window = Window(begin=begin, minutes=10)
    opts = dict(window=window, any='group 2')
    print agent.dog.bark('hello', **opts)
    print agent.dog.wag(3, **opts)
    print agent.dog.bark('hello again', **opts)

    # group 1
    
    print 'group 1'
    begin = later(seconds=10)
    window = Window(begin=begin, minutes=10)
    opts = dict(window=window, any='group 1')
    print agent.dog.bark('hello', **opts)
    print agent.dog.wag(3, **opts)
    print agent.dog.bark('hello again', **opts)
    agent = None