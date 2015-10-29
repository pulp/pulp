import os
import shutil
from tempfile import mkdtemp
from unittest import TestCase
from uuid import uuid4

from mock import Mock, patch

from pulp_node import constants, error
from pulp_node.importers import strategies
from pulp_node.importers.inventory import UnitInventory
from pulp_node.importers.reports import SummaryReport, ProgressListener
from pulp_node.reports import RepositoryProgress


class TestConduit:

    def get_units(self):
        return [
            Unit('T', {1: 1}, {2: 2}, 'path_1'),
            Unit('T', {1: 2}, {2: 2}, 'path_2'),
            Unit('T', {1: 3}, {2: 2}, 'path_3'),
        ]

    save_unit = Mock()
    remove_unit = Mock()
    set_progress = Mock()


class CancelEvent(object):

    def __init__(self, on_call):
        self.on_call = on_call
        self.call_count = 0

    def isSet(self):
        self.call_count += 1
        return self.on_call and self.call_count >= self.on_call


class TestRepo(object):

    def __init__(self, repo_id, working_dir):
        self.id = repo_id
        self.working_dir = working_dir


class TestManifest:

    def __init__(self, units):
        self.units = [(u, TestUnitRef(u)) for u in units]
        self.publishing_details = {constants.BASE_URL: BASE_URL}

    def get_units(self):
        return self.units

    def fetch(self):
        pass

    def fetch_units(self):
        pass


class TestUnitRef:

    def __init__(self, unit):
        self.unit = unit

    def fetch(self):
        return self.unit


REPO_ID = 'foo'
BASE_URL = 'file://'
DOWNLOADER_ERROR_REPORT = dict(response_code=401, message='go fish')
MANIFEST_ERROR = error.ManifestDownloadError('http://redhat.com/manifest', DOWNLOADER_ERROR_REPORT)
UNIT_ERROR = error.UnitDownloadError('http://redhat.com/unit', REPO_ID, DOWNLOADER_ERROR_REPORT)


class TestBase(TestCase):

    @classmethod
    def setUpClass(cls):
        path = os.path.join(
            os.path.abspath(os.path.dirname(__file__)),
            'data',
            'pulp.conf')
        pulp_conf.read(path)

    def setUp(self):
        super(TestBase, self).setUp()
        self.tmp_dir = mkdtemp()

    def tearDown(self):
        super(TestBase, self).tearDown()
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def request(self, cancel_on=0):
        conduit = TestConduit()
        progress = RepositoryProgress(REPO_ID, ProgressListener(conduit))
        summary = SummaryReport()
        cancel_event = CancelEvent(cancel_on)
        request = strategies.Request(
            cancel_event,
            conduit=conduit,
            config={},
            downloader=Mock(),
            progress=progress,
            summary=summary,
            repo=TestRepo(REPO_ID, self.tmp_dir)
        )
        return request

    def test_abstract(self):
        # Test
        strategy = strategies.ImporterStrategy()
        # Verify
        self.assertRaises(NotImplementedError, strategy._synchronize, None)

    @patch('pulp_node.importers.strategies.ImporterStrategy._unit_inventory')
    @patch('pulp_node.importers.strategies.ImporterStrategy._synchronize', side_effect=ValueError())
    def test_synchronize_catch_unknown_exception(self, *unused):
        # Setup
        request = self.request()
        # Test
        strategy = strategies.ImporterStrategy()
        strategy.synchronize(request)
        self.assertEqual(len(request.summary.errors), 1)
        self.assertEqual(request.summary.errors[0].error_id, error.CaughtException.ERROR_ID)

    @patch('pulp_node.importers.strategies.ImporterStrategy._unit_inventory')
    @patch('pulp_node.importers.strategies.ImporterStrategy._synchronize', side_effect=UNIT_ERROR)
    def test_synchronize_catch_node_error(self, *unused):
        # Setup
        request = self.request()
        # Test
        strategy = strategies.ImporterStrategy()
        strategy.synchronize(request)
        self.assertEqual(len(request.summary.errors), 1)
        self.assertEqual(request.summary.errors[0].error_id, error.UnitDownloadError.ERROR_ID)

    @patch('pulp_node.importers.strategies.ImporterStrategy._unit_inventory')
    @patch.object(TestConduit, 'save_unit', ValueError())
    def test_add_unit_exception(self, *unused):
        # Setup
        request = self.request()
        # Test
        unit = dict(unit_id='abc', type_id='T', unit_key={}, metadata={})
        strategy = strategies.ImporterStrategy()
        strategy.add_unit(request, unit)
        self.assertEqual(len(request.summary.errors), 1)
        self.assertEqual(request.summary.errors[0].error_id, error.AddUnitError.ERROR_ID)

    @patch('pulp_node.importers.strategies.ImporterStrategy._unit_inventory')
    @patch.object(TestConduit, 'remove_unit', ValueError())
    def test_delete_units_exception(self, *unused):
        # Setup
        request = self.request()
        # Test
        unit = dict(unit_id='abc', type_id='T', unit_key={}, metadata={})
        inventory = UnitInventory(BASE_URL, [], [unit])
        strategy = strategies.ImporterStrategy()
        strategy._delete_units(request, inventory)
        self.assertEqual(len(request.summary.errors), 1)
        self.assertEqual(request.summary.errors[0].error_id, error.DeleteUnitError.ERROR_ID)

    @patch('pulp_node.conduit.NodesConduit.get_units', side_effect=ValueError())
    def test_get_child_units_exception(self, *unused):
        # Setup
        request = self.request()
        # Test
        strategy = strategies.ImporterStrategy()
        self.assertRaises(error.GetChildUnitsError, strategy._unit_inventory, request)

    @patch('pulp_node.conduit.NodesConduit.get_units', return_value=[])
    @patch('pulp_node.manifest.RemoteManifest.fetch', side_effect=ValueError())
    def test_get_parent_units_exception(self, *unused):
        # Setup
        request = self.request()
        # Test
        strategy = strategies.ImporterStrategy()
        self.assertRaises(error.GetParentUnitsError, strategy._unit_inventory, request)

    @patch('pulp_node.conduit.NodesConduit.get_units', return_value=[])
    @patch('pulp_node.manifest.RemoteManifest.fetch', side_effect=MANIFEST_ERROR)
    def test_get_parent_units_manifest_error(self, *unused):
        # Setup
        request = self.request()
        # Test
        strategy = strategies.ImporterStrategy()
        self.assertRaises(error.ManifestDownloadError, strategy._unit_inventory, request)

    @patch('pulp_node.importers.strategies.ImporterStrategy.add_unit')
    def test_cancel_at_add_units(self, mock_add_unit):
        # Setup
        request = self.request(1)
        request.downloader.download = Mock()
        unit = dict(unit_id='abc', type_id='T', unit_key={}, metadata={})
        units = [unit]
        manifest = TestManifest(units)
        inventory = UnitInventory(BASE_URL, manifest.get_units(), [])
        # Test
        strategy = strategies.ImporterStrategy()
        strategy._add_units(request, inventory)
        self.assertEqual(request.cancel_event.call_count, 1)
        self.assertEqual(mock_add_unit.call_count, 0)

    def test_cancel_at_delete_units(self):
        # Setup
        request = self.request(1)
        unit = dict(unit_id='abc', type_id='T', unit_key={}, metadata={})
        inventory = UnitInventory(BASE_URL, [], [unit])
        request.conduit.remove_unit = Mock()
        # Test
        strategy = strategies.ImporterStrategy()
        strategy._delete_units(request, inventory)
        self.assertEqual(request.cancel_event.call_count, 1)
        request.conduit.remove_unit.assert_not_called()

    @patch('pulp.server.content.sources.container.ContentContainer.download')
    def test_cancel_just_before_downloading(self, mock_download):
        # Setup
        unit_id = str(uuid4())
        request = self.request(2)
        request.downloader.download = Mock()
        unit = dict(
            unit_id=unit_id,
            type_id='T',
            unit_key={},
            metadata={},
            storage_path=os.path.join(self.tmp_dir, unit_id),
            relative_path=os.path.join(self.tmp_dir, 'testing', unit_id))
        units = [unit]
        manifest = TestManifest(units)
        inventory = UnitInventory(BASE_URL, manifest.get_units(), [])
        # Test
        strategy = strategies.ImporterStrategy()
        strategy._add_units(request, inventory)
        self.assertEqual(request.cancel_event.call_count, 2)
        self.assertFalse(mock_download.called)

    def test_needs_update(self):
        # Setup
        path = os.path.join(self.tmp_dir, 'unit_1')
        with open(path, 'w+') as fp:
            fp.write('123')
        size = os.path.getsize(path)
        strategy = strategies.ImporterStrategy()
        # Test
        unit = {constants.STORAGE_PATH: path, constants.FILE_SIZE: size}
        self.assertFalse(strategy._needs_download(unit))
        unit = {constants.STORAGE_PATH: '&&&&&&&', constants.FILE_SIZE: size}
        self.assertTrue(strategy._needs_download(unit))
        unit = {constants.STORAGE_PATH: path, constants.FILE_SIZE: size + 1}
        self.assertTrue(strategy._needs_download(unit))

    def test_strategy_factory(self):
        for name, strategy in strategies.STRATEGIES.items():
            self.assertEqual(strategies.find_strategy(name), strategy)
        self.assertRaises(strategies.StrategyUnsupported, strategies.find_strategy, '---')
