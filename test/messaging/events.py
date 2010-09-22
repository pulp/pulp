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

from pulp.messaging.producer import EventProducer
from pulp.server.event.dispatcher import EventDispatcher
from time import sleep
from logging import INFO, basicConfig

basicConfig(filename='/tmp/messaging.log', level=INFO)

def main():
    #ed = EventDispatcher()
    #ed.start()
    p = EventProducer()
    for n in range(0, 1000):
        d = dict(
            id='repo%d' % n,
            name='Repository%d' % n,
            arch='noarch',)
        p.send('bogus', 'bogus')
        #p.send('user', 'user without subject')
        #p.send('user.hello', 'user.%d' % n)
        #p.send('user.created', '{%d} user.created' % n)
        #p.send('user.updated', '{%d} user.updated' % n)
        #p.send('user.deleted', '{%d} user-deleted' % n)
        p.send('repo.created', d)
        #p.send('repo.updated', d)
        #p.send('repo.deleted', d)
        #p.send('product.created', d)
        sleep(3)

if __name__ == '__main__':
    main()
