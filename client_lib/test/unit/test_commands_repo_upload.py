# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
"""
This module tests the pulp.client.commands.repo.upload module.
"""
import mock

from pulp.client.commands.repo import upload
from pulp.devel.unit import base


class TestPerformUpload(base.PulpClientTests):
    """
    Test the perform_upload() function.
    """
    @mock.patch('pulp.client.extensions.core.PulpPrompt.render_failure_message')
    def test_import_upload_step_failed(self, render_failure_message):
        """
        Assert that the CLI properly informs the user when an importer reports failure upon
        importing a unit to the repository.
        """
        response_body = {'success_flag': False, 'summary': 'An error message.'}
        response = mock.MagicMock()
        response.response_body = response_body
        response.is_async = mock.MagicMock(return_value=False)
        upload_manager = mock.MagicMock()
        upload_manager.import_upload = mock.MagicMock(return_value=response)
        upload_ids = ['an_id']

        upload.perform_upload(self.context, upload_manager, upload_ids)

        render_failure_message.assert_called_once_with('... failed: %s' % response_body['summary'])

    @mock.patch('pulp.client.extensions.core.PulpPrompt.render_failure_message')
    @mock.patch('pulp.client.extensions.core.PulpPrompt.write')
    def test_import_upload_step_succeeded(self, write, render_failure_message):
        """
        Assert that the CLI properly informs the user when an importer reports success upon
        importing a unit to the repository.
        """
        response_body = {'success_flag': True, 'summary': None}
        response = mock.MagicMock()
        response.response_body = response_body
        response.is_async = mock.MagicMock(return_value=False)
        upload_manager = mock.MagicMock()
        upload_manager.import_upload = mock.MagicMock(return_value=response)
        upload_ids = ['an_id']

        upload.perform_upload(self.context, upload_manager, upload_ids)

        write.assert_any_call('... completed', tag='import_upload_success')
        # No errors should have been rendered
        self.assertEqual(render_failure_message.call_count, 0)