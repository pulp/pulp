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
from uuid import uuid4

from nectar.config import DownloaderConfig
from nectar.downloaders.curl import HTTPCurlDownloader

from pulp.plugins.model import Unit
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


class TestRequest(SyncRequest):

    def __init__(self, cancel_on, *args, **kwargs):
        super(TestRequest, self).__init__(*args, **kwargs)
        self.cancel_on = cancel_on
        self.cancelled_call_count = 0

    def cancelled(self):
        self.cancelled_call_count += 1
        return self.cancel_on and self.cancelled_call_count >= self.cancel_on


class TestRepo(object):

    def __init__(self, repo_id, working_dir):
        self.id = repo_id
        self.working_dir = working_dir


class TestManifest:

    def __init__(self, units):
        self.units = [(u, TestUnitRef(u)) for u in units]
        self.publishing_details = {constants.BASE_URL: ''}

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
            repo=TestRepo(REPO_ID, self.tmp_dir)
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
        unit = dict(unit_id='abc', type_id='T', unit_key={}, metadata={})
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
        unit = dict(unit_id='abc', type_id='T', unit_key={}, metadata={})
        inventory = UnitInventory('', [], [unit])
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
    @patch('pulp_node.manifest.RemoteManifest.fetch', side_effect=ValueError())
    def test_get_parent_units_exception(self, *unused):
        # Setup
        request = self.request()
        # Test
        strategy = ImporterStrategy()
        self.assertRaises(GetParentUnitsError, strategy._unit_inventory, request)

    @patch('pulp_node.conduit.NodesConduit.get_units', return_value=[])
    @patch('pulp_node.manifest.RemoteManifest.fetch', side_effect=MANIFEST_ERROR)
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
        unit = dict(unit_id='abc', type_id='T', unit_key={}, metadata={})
        units = [unit]
        manifest = TestManifest(units)
        inventory = UnitInventory('', manifest.get_units(), [])
        # Test
        strategy = ImporterStrategy()
        strategy._add_units(request, inventory)
        self.assertEqual(request.cancelled_call_count, 1)
        self.assertFalse(request.downloader.download.called)

    def test_cancel_at_delete_units(self):
        # Setup
        request = self.request(1)
        unit = dict(unit_id='abc', type_id='T', unit_key={}, metadata={})
        inventory = UnitInventory('', [], [unit])
        request.conduit.remove_unit = Mock()
        # Test
        strategy = ImporterStrategy()
        strategy._delete_units(request, inventory)
        self.assertEqual(request.cancelled_call_count, 1)
        request.conduit.remove_unit.assert_not_called()

    def test_cancel_just_before_downloading(self):
        # Setup
        unit_id = str(uuid4())
        request = self.request(2)
        request.downloader.download = Mock()
        unit = dict(
            unit_id=unit_id,
            type_id='T',
            unit_key={},
            metadata={},
            storage_path='/tmp/node/testing/%s' % unit_id,
            relative_path='testing/%s' % unit_id)
        units = [unit]
        manifest = TestManifest(units)
        inventory = UnitInventory('', manifest.get_units(), [])
        # Test
        strategy = ImporterStrategy()
        strategy._add_units(request, inventory)
        self.assertEqual(request.cancelled_call_count, 2)
        self.assertFalse(request.downloader.download.called)

    def test_cancel_begin_downloading(self):
        # Setup
        unit_id = str(uuid4())
        request = self.request(3)
        request.downloader = HTTPCurlDownloader(DownloaderConfig())
        request.downloader.download = Mock(side_effect=request.downloader.download)
        request.downloader.cancel = Mock()
        unit = dict(
            unit_id=unit_id,
            type_id='T',
            unit_key={},
            metadata={},
            storage_path='/tmp/node/testing/%s' % unit_id,
            relative_path='testing/%s' % unit_id)
        units = [unit]
        manifest = TestManifest(units)
        inventory = UnitInventory('', manifest.get_units(), [])
        # Test
        strategy = ImporterStrategy()
        strategy._add_units(request, inventory)
        self.assertTrue(request.cancelled_call_count >= 3)
        self.assertTrue(request.downloader.download.called)
        self.assertTrue(request.downloader.cancel.called)

    def test_cancel_during_download_failed(self):
        # Setup
        unit_id = str(uuid4())
        request = self.request(4)
        request.downloader = HTTPCurlDownloader(DownloaderConfig())
        request.downloader.download = Mock(side_effect=request.downloader.download)
        request.downloader.cancel = Mock()
        unit = dict(
            unit_id=unit_id,
            type_id='T',
            unit_key={},
            metadata={},
            storage_path='/tmp/node/testing/%s' % unit_id,
            relative_path='testing/%s' % unit_id)
        units = [unit]
        manifest = TestManifest(units)
        inventory = UnitInventory('', manifest.get_units(), [])
        # Test
        strategy = ImporterStrategy()
        strategy._add_units(request, inventory)
        self.assertEqual(request.cancelled_call_count, 4)
        self.assertTrue(request.downloader.download.called)
        self.assertTrue(request.downloader.cancel.called)

    def test_cancel_during_download_succeeded(self):
        # Setup
        unit_id = str(uuid4())
        request = self.request(4)
        request.downloader = HTTPCurlDownloader(DownloaderConfig())
        request.downloader.download = Mock(side_effect=request.downloader.download)
        request.downloader.cancel = Mock()
        unit = dict(
            unit_id=unit_id,
            type_id='T',
            unit_key={},
            metadata={},
            storage_path='/tmp/node/testing/%s' % unit_id,
            relative_path='testing/%s' % unit_id)
        units = [unit]
        manifest = TestManifest(units)
        inventory = UnitInventory('', manifest.get_units(), [])
        # Test
        strategy = ImporterStrategy()
        strategy._add_units(request, inventory)
        self.assertEqual(request.cancelled_call_count, 4)
        self.assertTrue(request.downloader.download.called)
        self.assertTrue(request.downloader.cancel.called)

    def test_needs_update(self):
        # Setup
        path = os.path.join(self.TMP_ROOT, 'unit_1')
        with open(path, 'w+') as fp:
            fp.write('123')
        size = os.path.getsize(path)
        strategy = ImporterStrategy()
        # Test
        unit = {constants.STORAGE_PATH: path, constants.FILE_SIZE: size}
        self.assertFalse(strategy._needs_download(unit))
        unit = {constants.STORAGE_PATH: '&&&&&&&', constants.FILE_SIZE: size}
        self.assertTrue(strategy._needs_download(unit))
        unit = {constants.STORAGE_PATH: path, constants.FILE_SIZE: size + 1}
        self.assertTrue(strategy._needs_download(unit))

    def test_strategy_factory(self):
        for name, strategy in STRATEGIES.items():
            self.assertEqual(find_strategy(name), strategy)
        self.assertRaises(StrategyUnsupported, find_strategy, '---')
