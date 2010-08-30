#! /usr/bin/env python
#
# This Driver script simulates a product create event on the bus
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
from logging import INFO, basicConfig

basicConfig(filename='/tmp/messaging.log', level=INFO)
# change these paths appropriately to suit your env
CERT_FILE="/home/pkilambi/certs/nimbus_cloude_debug.crt"
CERT_KEY="/home/pkilambi/certs/nimbus_cloude_debug.key"
CA_CERT="/home/pkilambi/certs/cdn.redhat.com-chain.crt"

def repo_driver():
    ed = EventDispatcher()
    ed.start()
    p = EventProducer()
    content_set = {
            "rhel-server" : "/content/dist/rhel/server/$releasever/$basearch/os"}
    cert_data = {'ca' : open(CA_CERT, "rb").read(),
                 'cert' : open(CERT_FILE, "rb").read(),
                 'key' : open(CERT_KEY, 'rb').read()}
    d = dict(
        id='rhel-server',
        content_set=content_set,
        cert_data = cert_data)
    p.send('product.created', d)
    ed.stop()

if __name__ == '__main__':
    repo_driver()
