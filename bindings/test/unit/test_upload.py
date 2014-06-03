# -*- coding: utf-8 -*-
#
# Copyright © 2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License
# (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied, including implied
# warranties of MERCHANTABILITY, NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR
# PURPOSE. You should have received a copy of GPLv2 along with this software;
# if not, see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import unittest

import mock

from pulp.bindings.upload import UploadAPI
from pulp.common.compat import json


class TestUploadAPI(unittest.TestCase):
    def setUp(self):
        self.api = UploadAPI(mock.MagicMock())

    def test_import_upload_with_override_config(self):
        ret = self.api.import_upload('upload_id', 'repo_id', 'unit_type_id', unit_key={},
                                     unit_metadata={}, override_config={'mask-id': 'test-mask-id'})
        expected_body = {
            'upload_id': 'upload_id',
            'unit_type_id': 'unit_type_id',
            'unit_key': {},
            'unit_metadata': {},
            'override_config': {'mask-id': 'test-mask-id'},
        }

        self.api.server.POST.assert_called_once_with('/v2/repositories/%s/actions/import_upload/'
                                                     % 'repo_id', expected_body)
        self.assertEqual(ret, self.api.server.POST.return_value)

    def test_import_upload(self):
        ret = self.api.import_upload('upload_id', 'repo_id', 'unit_type_id', unit_key={},
                                     unit_metadata={})
        expected_body = {
            'upload_id': 'upload_id',
            'unit_type_id': 'unit_type_id',
            'unit_key': {},
            'unit_metadata': {},
            'override_config': None,
        }

        self.api.server.POST.assert_called_once_with('/v2/repositories/%s/actions/import_upload/'
                                                     % 'repo_id', expected_body)
        self.assertEqual(ret, self.api.server.POST.return_value)
