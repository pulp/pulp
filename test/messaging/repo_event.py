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

from pulp.server.event.producer import EventProducer
from pulp.server.event.dispatcher import EventDispatcher
from optparse import Option, OptionParser

class RepoDriver:

    def update(self):
        p = EventProducer()
        d = dict(
            id='REPO1',
            description='Repo updated',
            path='/etc/foo/bar')
        p.send('repo.updated', d)

def main():
    options_table = [
    Option("--update", action="store_true",
        help="Raise a REPO event"),
    ]
    parser = OptionParser(option_list=options_table)
    (options, args) = parser.parse_args()
    driver = RepoDriver()
    if options.update:
        driver.update()
        print("Raised REPO updated event")

if __name__ == '__main__':
    main()
