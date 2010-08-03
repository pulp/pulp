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

from pmf.producer import EventProducer
from time import sleep
from logging import INFO, basicConfig

basicConfig(filename='/tmp/pmf.log', level=INFO)

def main():
    p = EventProducer()
    for n in range(0, 1000):
        p.send('bogus', 'bogus')
        p.send('user', 'user without subject')
        p.send('user.hello', 'user.%d' % n)
        p.send('user.created', '{%d} user.created' % n)
        p.send('user.updated', '{%d} user.updated' % n)
        p.send('user.deleted', '{%d} user-deleted' % n)
        p.send('repo.created', '{%d} repo.created' % n)
        p.send('repo.updated', '{%d} repo.updated' % n)
        p.send('repo.deleted', '{%d} repo-deleted' % n)
        sleep(3)

if __name__ == '__main__':
    main()