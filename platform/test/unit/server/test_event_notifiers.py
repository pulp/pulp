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

import unittest

from pulp.server.event import mail, notifiers, rest_api


class TestNotifiers(unittest.TestCase):
    def test_rest_type_present(self):
        ret = notifiers.get_notifier_function(rest_api.TYPE_ID)
        self.assertTrue(callable(ret))
        self.assertEqual(ret, rest_api.handle_event)

    def test_mail_type_present(self):
        ret = notifiers.get_notifier_function(mail.TYPE_ID)
        self.assertTrue(callable(ret))
        self.assertEqual(ret, mail.handle_event)

    def test_validator(self):
        self.assertTrue(notifiers.is_valid_notifier_type_id(mail.TYPE_ID))
        self.assertTrue(notifiers.is_valid_notifier_type_id(rest_api.TYPE_ID))
        self.assertFalse(notifiers.is_valid_notifier_type_id(''))
        self.assertFalse(notifiers.is_valid_notifier_type_id(123))
        self.assertFalse(notifiers.is_valid_notifier_type_id('lhferlihfd'))

