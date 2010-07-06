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

from pmf.consumer import ReplyConsumer
from time import sleep

class ReplyGroup:

    def __init__(self, groupid):
        r = ReplyConsumer(groupid)
        r.start(self)

    def succeeded(self, sn, retval):
        print 'sn: %s, succeeded: (%s' % (sn, retval)

    def raised(self, sn, exval):
        print 'sn: %s, raised: (%s' % (sn, exval)


if __name__ == '__main__':
    ReplyGroup('task')
    while True:
        print 'waiting ...'
        sleep(5)