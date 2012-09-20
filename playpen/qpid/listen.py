#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import argparse

from qpid.messaging import Connection

# This is a modest script that will connect to a qpid broker and print messages
# sent to a specified exchange.

def get_args():
    parser = argparse.ArgumentParser(
        description='print messages sent to a qpid exchange')
    parser.add_argument(
        '-e', '--exchange', help='name of a qpid exchange (default: amq.topic)',
        default='amq.topic')
    parser.add_argument(
        '-s', '--subject', help='message subject to bind to', required=False)
    parser.add_argument(
        '-a', '--address', help='hostname to connect to (default:localhost)',
        default='localhost')
    parser.add_argument(
        '-p', '--port', help='port to connect to (default: 5672)', default='5672')
    parser.add_argument(
        '-q', '--quiet', help='show message subject only',
        default=False, action='store_true')
    return parser.parse_args()

args = get_args()

source = args.exchange
if args.subject:
    source = '%s/%s' % (source, args.subject)

receiver = Connection.establish('%s:%s' % (args.address, args.port)).session().receiver(source)

try:
    while True:
        message = receiver.fetch()
        if args.quiet:
            print message.subject
        else:
            print '------------------'
            print message
except KeyboardInterrupt:
    print ''
