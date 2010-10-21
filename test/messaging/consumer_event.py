#! /usr/bin/env python
#
# This Driver script simulates a consumer events on the bus
# similar to what's expected of candlepin
# 
# Copyright (c) 2010 Red Hat, Inc.
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
#from logging import INFO, basicConfig
from optparse import Option, OptionParser

class ConsumerDriver:
        
    def create(self):
        p = EventProducer()
        d = dict(
                 id='test-consumer',
                 description='candlepin consumer',
                 owner='admin'
                 )
        p.send('consumer.created', d)
        #ed.stop()
        
    def delete(self):
        p = EventProducer()
        d = dict(
                 id='test-consumer',
                 owner = 'admin',
                 )
        p.send('consumer.deleted', d)
        
def main():
    options_table = [
    Option("--create", action="store_true",
        help="Raise a consumer create event on qpid bus"),
    Option("--delete", action="store_true",
        help="Raise a consumer delete event on qpid bus"),
    ]
    parser = OptionParser(option_list=options_table)
    (options, args) = parser.parse_args()
    cd = ConsumerDriver()
    if options.create:
        cd.create()
        print("Raised a consumer.created event on qpid bus")
    if options.delete:
        cd.delete()
        print("Raised a consumer.deleted event on qpid bus")
        


if __name__ == '__main__':
    main()
