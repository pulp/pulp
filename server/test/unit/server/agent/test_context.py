# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.


import hashlib

from unittest import TestCase

from mock import patch

from pulp.server.agent.context import Context
from pulp.server.agent.direct.services import Services


pulp_conf = {
    'messaging': {
        'url': 'http://broker'
    }
}


class TestContext(TestCase):

    @patch('pulp.server.agent.context.pulp_conf', pulp_conf)
    def test_context(self):
        consumer = {'id': 'gc', 'certificate': 'XXX'}
        h = hashlib.sha256()
        h.update(consumer['certificate'])
        secret = h.hexdigest()
        details = {'task_id': '3456'}

        # test context

        context = Context(consumer, **details)

        # validation

        self.assertEqual(context.uuid, consumer['id'])
        self.assertEqual(context.url, pulp_conf.get('messaging', 'url'))
        self.assertEqual(context.secret, secret)
        self.assertEqual(context.details, details)
        self.assertEqual(context.reply_queue, Services.REPLY_QUEUE)
        self.assertEqual(context.watchdog, Services.watchdog)