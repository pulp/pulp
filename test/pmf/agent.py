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
from pmf.base import Agent as Base
from pmf.decorators import remote, remotemethod
from pmf.consumer import RequestConsumer

@remote
class RepoLib:
    @remotemethod
    def update(self):
        print 'Repo updated'

@remote
class Dog:
    @remotemethod
    def bark(self, words):
        print 'Ruf %s' % words
        return 'Yes master.  I will bark because that is what dogs do.'

    @remotemethod
    def wag(self, n):
        for i in range(0, n):
            print 'wag'
        return 'Yes master.  I will wag my tail because that is what dogs do.'

    def notpermitted(self):
        print 'not permitted.'


class Agent(Base):
    def __init__(self, id):
        Base.__init__(self, RequestConsumer(id))
        while True:
            sleep(10)
            print 'Agent: sleeping...'

if __name__ == '__main__':
    if len(sys.argv) > 1:
        cid = sys.argv[1]
    else:
        cid = '123'
    print 'starting agent (%s)' % cid
    agent = Agent(cid)
