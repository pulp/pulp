
from unittest import TestCase

from mock import Mock, patch

from pulp_node.importers.strategies import ImporterStrategy


class TestAddUnits(TestCase):

    @patch('pulp.server.content.sources.ContentContainer.download')
    def test_download_reporting(self, fake_download):
        fake_download.return_value = Mock()

        fake_request = Mock()
        fake_request.cancelled.return_value = False

        fake_inventory = Mock()
        fake_inventory.units_on_parent_only.return_value = []

        # test
        strategy = ImporterStrategy()
        strategy._add_units(fake_request, fake_inventory)

        # validation
        self.assertEqual(fake_request.summary.sources, fake_download())

