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

from time import sleep

from pmf.proxy import Proxy
from pmf.base import AgentProxy as Base
from pmf.producer import QueueProducer
from pmf.policy import *
from pmf.window import *
from datetime import datetime as dt
from datetime import timedelta as delta
from logging import INFO, basicConfig

basicConfig(filename='/tmp/pmf.log', level=INFO)


class RepoLib(Proxy):
    pass

class Dog(Proxy):
    pass


class Agent(Base):

    def __init__(self, id, tag=None):
        producer = QueueProducer()
        if tag or isinstance(id, (tuple,list)):
            method = Asynchronous(producer, tag)
        else:
            method = Synchronous(producer)
        Base.__init__(self,
            id,
            method,
            repolib=RepoLib,
            dog=Dog)


def demo(agent):
    print agent.dog.bark('hello')
    print agent.dog.wag(3)
    print agent.dog.bark('hello')
    print agent.repolib.update()
    try:
        print agent.repolib.updated()
    except Exception, e:
        print repr(e)

    try:
        print agent.dog.notpermitted()
    except Exception, e:
        print repr(e)


if __name__ == '__main__':
    # synchronous
    agent = Agent('123')
    demo(agent)
    agent = None
    # asynchronous
    tag = 'jortel'
    ids = ('123',)
    agent = Agent(ids, tag)
    agent.setWindow(Window.create(minutes=1))
    demo(agent)
    # future
    print 'FUTURE'
    agent.setAny('group 2')
    later = dt.utcnow()+delta(seconds=20)
    agent.setWindow(Window.create(later, minutes=10))
    demo(agent)
    agent.setAny('group 1')
    later = dt.utcnow()+delta(seconds=10)
    agent.setWindow(Window.create(later, minutes=10))
    demo(agent)
    agent = None