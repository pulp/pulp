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


from unittest import TestCase
from mock import Mock, patch

from pulp.plugins.model import Unit
from pulp_node.importers.strategies import *
from pulp_node.importers.inventory import UnitInventory
from pulp_node.importers.reports import SummaryReport, ProgressListener
from pulp_node.reports import RepositoryProgress
from pulp_node.error import *


class TestConduit:

    def get_units(self):
        return [
            Unit('T', {1:1}, {2:2}, 'path_1'),
            Unit('T', {1:2}, {2:2}, 'path_2'),
            Unit('T', {1:3}, {2:2}, 'path_3'),
        ]

    save_unit = Mock()
    remove_unit = Mock()


class TestUnit:

    def __init__(self, unit_id=None):
        self.id = unit_id


REPO_ID = 'foo'
CONDUIT = TestConduit()
CONFIG = {}
DOWNLOADER = None

DOWNLOADER_ERROR_REPORT = dict(response_code=401, message='go fish')
MANIFEST_ERROR = ManifestDownloadError('http://redhat.com/manifest', DOWNLOADER_ERROR_REPORT)
UNIT_ERROR = UnitDownloadError('http://redhat.com/unit', REPO_ID, DOWNLOADER_ERROR_REPORT)


class TestBase(TestCase):

    REPO_ID = 'foo'
    CONDUIT = TestConduit()
    CONFIG = {}
    DOWNLOADER = None

    def test_abstract(self):
        # Setup
        progress = RepositoryProgress(REPO_ID, ProgressListener(CONDUIT))
        summary = SummaryReport()
        # Test
        strategy = ImporterStrategy(CONDUIT, CONFIG, DOWNLOADER, progress, summary)
        # Verify
        self.assertEqual(CONDUIT, strategy.conduit)
        self.assertEqual(CONFIG, strategy.config)
        self.assertEqual(DOWNLOADER, strategy.downloader)
        self.assertEqual(progress, strategy.progress_report)
        self.assertEqual(strategy.progress_report.listener.conduit, CONDUIT)
        self.assertRaises(NotImplementedError, strategy._synchronize, None)

    @patch('pulp_node.importers.strategies.ImporterStrategy._unit_inventory')
    @patch('pulp_node.importers.strategies.ImporterStrategy._synchronize', side_effect=ValueError())
    def test_synchronize_catch_unknown_exception(self, *unused):
        # Setup
        progress = RepositoryProgress(REPO_ID, ProgressListener(CONDUIT))
        summary = SummaryReport()
        # Test
        strategy = ImporterStrategy(CONDUIT, CONFIG, DOWNLOADER, progress, summary)
        strategy.synchronize(REPO_ID)
        self.assertEqual(len(summary.errors), 1)
        self.assertEqual(summary.errors[0].error_id, CaughtException.ERROR_ID)

    @patch('pulp_node.importers.strategies.ImporterStrategy._unit_inventory')
    @patch('pulp_node.importers.strategies.ImporterStrategy._synchronize', side_effect=UNIT_ERROR)
    def test_synchronize_catch_node_error(self, *unused):
        # Setup
        progress = RepositoryProgress(REPO_ID, ProgressListener(CONDUIT))
        summary = SummaryReport()
        # Test
        strategy = ImporterStrategy(CONDUIT, CONFIG, DOWNLOADER, progress, summary)
        strategy.synchronize(REPO_ID)
        self.assertEqual(len(summary.errors), 1)
        self.assertEqual(summary.errors[0].error_id, UnitDownloadError.ERROR_ID)

    @patch('pulp_node.importers.strategies.ImporterStrategy._unit_inventory')
    @patch('test_importer_strategies.TestConduit.save_unit', ValueError())
    def test_add_unit_exception(self, *unused):
        # Setup
        progress = RepositoryProgress(REPO_ID, ProgressListener(CONDUIT))
        summary = SummaryReport()
        # Test
        unit = TestUnit()
        strategy = ImporterStrategy(CONDUIT, CONFIG, DOWNLOADER, progress, summary)
        strategy.add_unit(REPO_ID, unit)
        self.assertEqual(len(summary.errors), 1)
        self.assertEqual(summary.errors[0].error_id, AddUnitError.ERROR_ID)

    @patch('pulp_node.importers.strategies.ImporterStrategy._unit_inventory')
    @patch('test_importer_strategies.TestConduit.remove_unit', ValueError())
    def test_delete_units_exception(self, *unused):
        # Setup
        progress = RepositoryProgress(REPO_ID, ProgressListener(CONDUIT))
        summary = SummaryReport()
        # Test
        unit = TestUnit()
        inventory = UnitInventory(REPO_ID, {unit.id: unit}, {})
        strategy = ImporterStrategy(CONDUIT, CONFIG, DOWNLOADER, progress, summary)
        strategy._delete_units(inventory)
        self.assertEqual(len(summary.errors), 1)
        self.assertEqual(summary.errors[0].error_id, DeleteUnitError.ERROR_ID)

    @patch('pulp_node.importers.strategies.ImporterStrategy._child_units', side_effect=ValueError())
    def test_get_child_units_exception(self, *unused):
        # Setup
        progress = RepositoryProgress(REPO_ID, ProgressListener(CONDUIT))
        summary = SummaryReport()
        # Test
        strategy = ImporterStrategy(CONDUIT, CONFIG, DOWNLOADER, progress, summary)
        self.assertRaises(GetChildUnitsError, strategy._unit_inventory, REPO_ID)

    @patch('pulp_node.importers.strategies.ImporterStrategy._child_units', side_effect=GetChildUnitsError(REPO_ID))
    def test_get_child_units_manifest_error(self, *unused):
        # Setup
        progress = RepositoryProgress(REPO_ID, ProgressListener(CONDUIT))
        summary = SummaryReport()
        # Test
        strategy = ImporterStrategy(CONDUIT, CONFIG, DOWNLOADER, progress, summary)
        self.assertRaises(GetChildUnitsError, strategy._unit_inventory, REPO_ID)

    @patch('pulp_node.importers.strategies.ImporterStrategy._parent_units', side_effect=ValueError())
    def test_get_parent_units_exception(self, *unused):
        # Setup
        progress = RepositoryProgress(REPO_ID, ProgressListener(CONDUIT))
        summary = SummaryReport()
        # Test
        strategy = ImporterStrategy(CONDUIT, CONFIG, DOWNLOADER, progress, summary)
        self.assertRaises(GetParentUnitsError, strategy._unit_inventory, REPO_ID)

    @patch('pulp_node.importers.strategies.ImporterStrategy._parent_units', side_effect=MANIFEST_ERROR)
    def test_get_parent_units_manifest_error(self, *unused):
        # Setup
        progress = RepositoryProgress(REPO_ID, ProgressListener(CONDUIT))
        summary = SummaryReport()
        # Test
        strategy = ImporterStrategy(CONDUIT, CONFIG, DOWNLOADER, progress, summary)
        self.assertRaises(ManifestDownloadError, strategy._unit_inventory, REPO_ID)

    def test_strategy_factory(self):
        for name, strategy in STRATEGIES.items():
            self.assertEqual(find_strategy(name), strategy)
        self.assertRaises(StrategyUnsupported, find_strategy, '---')