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

from pulp.messaging.consumer import EventConsumer
from logging import INFO, basicConfig

basicConfig(filename='/tmp/messaging.log', level=INFO)

class MyConsumer(EventConsumer):
    def notify(self, subject, body):
        print '(%s) %s' % (subject, body)

def main():
    c = MyConsumer('user.#', 'myqueue')
    c.start()
    c.join()

if __name__ == '__main__':
    main()
