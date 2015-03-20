import unittest

import mock

from pulp.bindings.consumer import ConsumerSearchAPI


class TestConsumerSearchAPI(unittest.TestCase):
    def test_path_defined(self):
        api = ConsumerSearchAPI(mock.MagicMock())
        self.assertTrue(api.PATH is not None)
        self.assertTrue(len(api.PATH) > 0)
