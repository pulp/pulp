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

import os
import shutil

from unittest import TestCase
from mock import Mock, patch
from tempfile import mkdtemp

from pulp.plugins.model import Unit
from pulp.common.download.downloaders.curl import HTTPCurlDownloader
from pulp.common.download.config import DownloaderConfig
from pulp.server.config import config as pulp_conf

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
    set_progress = Mock()


class TestImporter:

    def __init__(self):
        self.cancelled = False


class TestUnit:

    def __init__(self, unit_id=None):
        self.id = unit_id


class TestRequest(SyncRequest):

    def __init__(self, cancel_on, *args, **kwargs):
        super(TestRequest, self).__init__(*args, **kwargs)
        self.cancel_on = cancel_on
        self.cancelled_call_count = 0

    def cancelled(self):
        self.cancelled_call_count += 1
        return self.cancel_on and self.cancelled_call_count >= self.cancel_on


class TestManifest:

    def __init__(self, tmp_dir, units=None):
        self.tmp_dir = tmp_dir
        self.units = units or []

    def get_units(self):
        return self.units


REPO_ID = 'foo'

DOWNLOADER_ERROR_REPORT = dict(response_code=401, message='go fish')
MANIFEST_ERROR = ManifestDownloadError('http://redhat.com/manifest', DOWNLOADER_ERROR_REPORT)
UNIT_ERROR = UnitDownloadError('http://redhat.com/unit', REPO_ID, DOWNLOADER_ERROR_REPORT)


class TestBase(TestCase):

    TMP_ROOT = '/tmp/pulp/nodes'

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(cls.TMP_ROOT):
            os.makedirs(cls.TMP_ROOT)
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
        request = TestRequest(
            cancel_on=cancel_on,
            importer=TestImporter(),
            conduit=conduit,
            config={},
            downloader=Mock(),
            progress=progress,
            summary=summary,
            repo_id=REPO_ID
        )
        return request

    def test_abstract(self):
        # Test
        strategy = ImporterStrategy()
        # Verify
        self.assertRaises(NotImplementedError, strategy._synchronize, None)

    @patch('pulp_node.importers.strategies.ImporterStrategy._unit_inventory')
    @patch('pulp_node.importers.strategies.ImporterStrategy._synchronize', side_effect=ValueError())
    def test_synchronize_catch_unknown_exception(self, *unused):
        # Setup
        request = self.request()
        # Test
        strategy = ImporterStrategy()
        strategy.synchronize(request)
        self.assertEqual(len(request.summary.errors), 1)
        self.assertEqual(request.summary.errors[0].error_id, CaughtException.ERROR_ID)

    @patch('pulp_node.importers.strategies.ImporterStrategy._unit_inventory')
    @patch('pulp_node.importers.strategies.ImporterStrategy._synchronize', side_effect=UNIT_ERROR)
    def test_synchronize_catch_node_error(self, *unused):
        # Setup
        request = self.request()
        # Test
        strategy = ImporterStrategy()
        strategy.synchronize(request)
        self.assertEqual(len(request.summary.errors), 1)
        self.assertEqual(request.summary.errors[0].error_id, UnitDownloadError.ERROR_ID)

    @patch('pulp_node.importers.strategies.ImporterStrategy._unit_inventory')
    @patch('test_importer_strategies.TestConduit.save_unit', ValueError())
    def test_add_unit_exception(self, *unused):
        # Setup
        request = self.request()
        # Test
        unit = TestUnit()
        strategy = ImporterStrategy()
        strategy.add_unit(request, unit)
        self.assertEqual(len(request.summary.errors), 1)
        self.assertEqual(request.summary.errors[0].error_id, AddUnitError.ERROR_ID)

    @patch('pulp_node.importers.strategies.ImporterStrategy._unit_inventory')
    @patch('test_importer_strategies.TestConduit.remove_unit', ValueError())
    def test_delete_units_exception(self, *unused):
        # Setup
        request = self.request()
        # Test
        unit = TestUnit()
        extra_units = [dict(unit_id=unit.id, type_id='T', unit_key={}, metadata={})]
        manifest = TestManifest(self.tmp_dir)
        inventory = UnitInventory(manifest, extra_units)
        strategy = ImporterStrategy()
        strategy._delete_units(request, inventory)
        self.assertEqual(len(request.summary.errors), 1)
        self.assertEqual(request.summary.errors[0].error_id, DeleteUnitError.ERROR_ID)

    @patch('pulp_node.conduit.NodesConduit.get_units', side_effect=ValueError())
    def test_get_child_units_exception(self, *unused):
        # Setup
        request = self.request()
        # Test
        strategy = ImporterStrategy()
        self.assertRaises(GetChildUnitsError, strategy._unit_inventory, request)

    @patch('pulp_node.conduit.NodesConduit.get_units', return_value=[])
    @patch('pulp_node.manifest.ManifestReader.read', side_effect=ValueError())
    def test_get_parent_units_exception(self, *unused):
        # Setup
        request = self.request()
        # Test
        strategy = ImporterStrategy()
        self.assertRaises(GetParentUnitsError, strategy._unit_inventory, request)

    @patch('pulp_node.conduit.NodesConduit.get_units', return_value=[])
    @patch('pulp_node.manifest.ManifestReader.read', side_effect=MANIFEST_ERROR)
    def test_get_parent_units_manifest_error(self, *unused):
        # Setup
        request = self.request()
        # Test
        strategy = ImporterStrategy()
        self.assertRaises(ManifestDownloadError, strategy._unit_inventory, request)

    def test_cancel_at_add_units(self):
        # Setup
        request = self.request(1)
        request.downloader.download = Mock()
        unit = TestUnit()
        units = [dict(unit_id=unit.id, type_id='T', unit_key={}, metadata={})]
        manifest = TestManifest(self.tmp_dir, units)
        inventory = UnitInventory(manifest, [])
        strategy = ImporterStrategy()
        # Test
        strategy = ImporterStrategy()
        strategy._add_units(request, inventory)
        self.assertEqual(request.cancelled_call_count, 1)
        self.assertFalse(request.downloader.download.called)

    def test_cancel_at_delete_units(self):
        # Setup
        request = self.request(1)
        unit = TestUnit()
        extra_units = [dict(unit_id=unit.id, type_id='T', unit_key={}, metadata={})]
        manifest = TestManifest(self.tmp_dir)
        inventory = UnitInventory(manifest, extra_units)
        request.conduit.remove_unit = Mock()
        # Test
        strategy = ImporterStrategy()
        strategy._delete_units(request, inventory)
        self.assertEqual(request.cancelled_call_count, 1)
        request.conduit.remove_unit.assert_not_called()

    def test_cancel_just_before_downloading(self):
        # Setup
        request = self.request(2)
        request.downloader.download = Mock()
        download = dict(url='http://redhat.com/file')
        unit = dict(
            unit_id='123',
            type_id='T',
            unit_key={},
            metadata={},
            _download=download,
            _storage_path='/tmp/file')
        manifest = TestManifest(self.tmp_dir, [unit])
        inventory = UnitInventory(manifest, [])
        # Test
        strategy = ImporterStrategy()
        strategy._add_units(request, inventory)
        self.assertEqual(request.cancelled_call_count, 2)
        self.assertFalse(request.downloader.download.called)

    def test_cancel_begin_downloading(self):
        # Setup
        request = self.request(3)
        request.downloader = HTTPCurlDownloader(DownloaderConfig())
        request.downloader.download = Mock(side_effect=request.downloader.download)
        request.downloader.cancel = Mock()
        download = dict(url='http://redhat.com/file')
        unit = dict(
            unit_id='123',
            type_id='T',
            unit_key={},
            metadata={},
            _download=download,
            _storage_path='/tmp/file')
        manifest = TestManifest(self.tmp_dir, [unit])
        inventory = UnitInventory(manifest, [])
        # Test
        strategy = ImporterStrategy()
        strategy._add_units(request, inventory)
        self.assertEqual(request.cancelled_call_count, 3)
        self.assertTrue(request.downloader.download.called)
        self.assertTrue(request.downloader.cancel.called)

    def test_cancel_during_download_failed(self):
        # Setup
        request = self.request(4)
        request.downloader = HTTPCurlDownloader(DownloaderConfig())
        request.downloader.download = Mock(side_effect=request.downloader.download)
        request.downloader.cancel = Mock()
        download = dict(url='http://redhat.com/file')
        unit = dict(
            unit_id='123',
            type_id='T',
            unit_key={},
            metadata={},
            _download=download,
            storage_path='/tmp/file',
            relative_path='files/testing')
        manifest = TestManifest(self.tmp_dir, [unit])
        inventory = UnitInventory(manifest, [])
        # Test
        strategy = ImporterStrategy()
        strategy._add_units(request, inventory)
        self.assertEqual(request.cancelled_call_count, 4)
        self.assertTrue(request.downloader.download.called)
        self.assertTrue(request.downloader.cancel.called)

    def test_cancel_during_download_succeeded(self):
        # Setup
        request = self.request(4)
        request.downloader = HTTPCurlDownloader(DownloaderConfig())
        request.downloader.download = Mock(side_effect=request.downloader.download)
        request.downloader.cancel = Mock()
        download = dict(url='http://redhat.com/file')
        unit = dict(
            unit_id='123',
            type_id='T',
            unit_key={},
            metadata={},
            _download=download,
            storage_path='/tmp/file',
            relative_path='files/testing')
        manifest = TestManifest(self.tmp_dir, [unit])
        inventory = UnitInventory(manifest, [])
        # Test
        strategy = ImporterStrategy()
        strategy._add_units(request, inventory)
        self.assertEqual(request.cancelled_call_count, 4)
        self.assertTrue(request.downloader.download.called)
        self.assertTrue(request.downloader.cancel.called)

    def test_strategy_factory(self):
        for name, strategy in STRATEGIES.items():
            self.assertEqual(find_strategy(name), strategy)
        self.assertRaises(StrategyUnsupported, find_strategy, '---')