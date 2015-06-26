import unittest

import mock

from pulp.bindings import server_info


class TestServerstatus(unittest.TestCase):

    def test_correct_passthrough(self):
        # setup
        self.server = mock.MagicMock()
        self.api = server_info.ServerStatusAPI(self.server)

        # test
        self.api.get_status()

        # verify
        self.server.GET.assert_called_once_with('v2/status/')


class TestServerInfo(unittest.TestCase):

    def test_correct_passthrough_types(self):
        # setup
        self.server = mock.MagicMock()
        self.api = server_info.ServerInfoAPI(self.server)

        # test
        self.api.get_types()

        # verify
        self.server.GET.assert_called_once_with('v2/plugins/types/')

    def test_correct_passthrough_importers(self):
        # setup
        self.server = mock.MagicMock()
        self.api = server_info.ServerInfoAPI(self.server)

        # test
        self.api.get_importers()

        # verify
        self.server.GET.assert_called_once_with('v2/plugins/importers/')

    def test_correct_passthrough_distributors(self):
        # setup
        self.server = mock.MagicMock()
        self.api = server_info.ServerInfoAPI(self.server)

        # test
        self.api.get_distributors()

        # verify
        self.server.GET.assert_called_once_with('v2/plugins/distributors/')
