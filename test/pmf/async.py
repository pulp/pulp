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
from pmf.consumer import ReplyConsumer

class Listener:

    def succeeded(self, sn, result):
        print 'succeeded: %s\n\t%s' % (sn, result)

    def failed(self, sn, ex):
        print 'failed: %s\n\t%s' % (sn, ex)


if __name__ == '__main__':
    tag = 'jortel'
    c = ReplyConsumer(tag)
    c.start(Listener())
    while True:
        print 'ReplyListener: sleeping...'
        sleep(10)