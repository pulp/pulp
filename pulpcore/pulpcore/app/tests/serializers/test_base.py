from unittest import TestCase, mock

from pulpcore.app import models
from pulpcore.app.serializers import base


class TestViewNameForModel(TestCase):
    def test_repository(self):
        """
        Use Repository as an example that should work.
        """
        ret = base.view_name_for_model(models.Repository(), 'foo')
        self.assertEqual(ret, 'repositories-foo')

    @mock.patch.object(base, 'viewset_for_model')
    def test_not_found(self, mock_viewset_for_model):
        """
        Given an unknown viewset (in this case a Mock()), this should raise LookupError.
        """
        self.assertRaises(LookupError, base.view_name_for_model, mock.Mock(), 'foo')
