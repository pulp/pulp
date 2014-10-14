# -*- coding: utf-8 -*-
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

from pulp.client.consumer.exception_handler import ConsumerExceptionHandler
from pulp.client.extensions import exceptions
from pulp.client.extensions.core import TAG_FAILURE, TAG_PARAGRAPH
from pulp.devel.unit import base


class ConsumerExceptionHandlerTests(base.PulpClientTests):

    def setUp(self):
        super(ConsumerExceptionHandlerTests, self).setUp()

        self.handler = ConsumerExceptionHandler(self.prompt, self.config)

    def test_permission(self):
        """
        Tests a client-side error when the connection is rejected due to auth reasons.
        """
        # Test
        response_body = {'auth_error_code': 'authentication_failed'}
        e = exceptions.PermissionsException(response_body)
        code = self.handler.handle_permission(e)

        # Verify
        self.assertEqual(code, exceptions.CODE_PERMISSIONS_EXCEPTION)
        self.assertTrue('Authentication' in self.recorder.lines[0])
        self.assertEqual(TAG_FAILURE, self.prompt.get_write_tags()[0])
        self.assertTrue('A valid' in self.recorder.lines[2]) # skip blank line
        self.assertEqual(TAG_PARAGRAPH, self.prompt.get_write_tags()[1])
