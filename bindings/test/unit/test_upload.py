import unittest

import mock

from pulp.bindings.upload import UploadAPI


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
