# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
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
import sys
import tempfile
import shutil
import random
import tarfile

from copy import deepcopy

from mock import Mock, patch
from base import WebTest

from nectar.downloaders.local import LocalFileDownloader
from nectar.config import DownloaderConfig

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/mocks")

from pulp_node.distributors.http.distributor import NodesHttpDistributor, entry_point as dist_entry_point
from pulp_node.importers.http.importer import NodesHttpImporter, entry_point as imp_entry_point
from pulp_node.profilers.nodes import NodeProfiler, entry_point as profiler_entry_point
from pulp_node.handlers.handler import NodeHandler, RepositoryHandler

from pulp.plugins.loader import api as plugin_api
from pulp.plugins.types import database as unit_db
from pulp.server.db import connection
from pulp.server.db.model.repository import Repo, RepoDistributor, RepoImporter
from pulp.server.db.model.repository import RepoContentUnit
from pulp.server.db.model.consumer import Consumer, Bind
from pulp.server.db.model.content import ContentType
from pulp.plugins import model as plugin_model
from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.conduits.repo_publish import RepoPublishConduit
from pulp.plugins.conduits.repo_sync import RepoSyncConduit
from pulp.plugins.util.nectar_config import importer_config_to_nectar_config
from pulp.common.plugins import importer_constants
from pulp.common.config import Config
from pulp.server.managers import factory as managers
from pulp.server.content.sources import Request as DownloadRequest
from pulp.server.config import config as pulp_conf
from pulp.agent.lib.conduit import Conduit
from pulp_node.manifest import Manifest, RemoteManifest, MANIFEST_FILE_NAME, UNITS_FILE_NAME
from pulp_node.handlers.strategies import Mirror, Additive
from pulp_node import error
from pulp_node import constants
from pulp_node import pathlib


FAKE_DISTRIBUTOR = 'test_distributor'
FAKE_ID = 'fake_plugin_id'
FAKE_DISTRIBUTOR_CONFIG = {'A': 0}

NODE_CERTIFICATE = """
    -----BEGIN RSA PRIVATE KEY-----
    PULPROCKSPULPROCKSPULPROCKS
    -----END RSA PRIVATE KEY-----
    -----BEGIN CERTIFICATE-----
    PULPROCKSPULPROCKSPULPROCKS
    -----END CERTIFICATE-----
"""

REPO_NAME = 'pulp-nodes'
REPO_DESCRIPTION = 'full of goodness'
REPO_NOTES = {'the answer to everything': 42}
REPO_SCRATCHPAD = {'a': 1, 'b': 2}

# --- testing mock classes ---------------------------------------------------


class Repository(object):

    def __init__(self, repo_id, working_dir=None):
        self.id = repo_id
        self.working_dir = working_dir


class FakeDistributor(object):

    @classmethod
    def metadata(cls):
        return {
            'id' : FAKE_DISTRIBUTOR,
            'display_name' : 'Fake Distributor',
            'types' : ['node',]
        }

    def validate_config(self, *unused):
        return True, None

    def publish_repo(self, repo, conduit, config):
        return conduit.build_success_report('succeeded', {})

    def distributor_added(self, *unused):
        pass


class TestStrategy:

    def __init__(self, tester, **options):
        self.tester = tester
        self.options = options

    def __call__(self):
        self.tester.clean(**self.options)
        return self._impl()()

    def _impl(self):
        raise NotImplementedError()


class MirrorTestStrategy(TestStrategy):

    def _impl(self):
        return Mirror


class AdditiveTestStrategy(TestStrategy):

    def _impl(self):
        return Additive


class BadDownloadRequest(DownloadRequest):

    def __init__(self, *args, **kwargs):
        DownloadRequest.__init__(self, *args, **kwargs)
        self.url = 'http:/NOWHERE/FAIL_ME_%f' % random.random()

class AgentConduit(Conduit):

    def __init__(self, node_id=None):
        self.node_id = node_id

    @property
    def consumer_id(self):
        return self.node_id


# --- testing base classes ---------------------------------------------------


class PluginTestBase(WebTest):

    REPO_ID = 'test-repo'
    UNIT_TYPE_ID = 'rpm'
    UNIT_ID = 'test_unit_%d'
    UNIT_KEY = {'A': 'a', 'B': 'b', 'N': 0}
    UNIT_METADATA = {'name': 'Elvis', 'age': 42}
    TYPEDEF_ID = UNIT_TYPE_ID
    NUM_UNITS = 10
    NUM_EXTRA_UNITS = 5
    EXTRA_REPO_IDS = ('extra_1', 'extra_2')

    PARENT_SETTINGS = {
        constants.HOST: 'pulp.redhat.com',
        constants.PORT: 443,
        constants.NODE_CERTIFICATE: NODE_CERTIFICATE,
    }

    @classmethod
    def tmpdir(cls, role):
        tmp_dir = tempfile.mkdtemp(dir=cls.TMP_ROOT, prefix=role)
        return tmp_dir

    def setUp(self):
        WebTest.setUp(self)
        self.parentfs = self.tmpdir('parent-')
        self.childfs = self.tmpdir('child-')
        self.alias = (self.parentfs, self.parentfs)
        Consumer.get_collection().remove()
        Bind.get_collection().remove()
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        RepoImporter.get_collection().remove()
        RepoContentUnit.get_collection().remove()
        unit_db.clean()
        self.define_plugins()
        plugin_api._create_manager()
        imp_conf = dict(strategy=constants.MIRROR_STRATEGY)
        plugin_api._MANAGER.importers.add_plugin(constants.HTTP_IMPORTER, NodesHttpImporter, imp_conf)
        plugin_api._MANAGER.distributors.add_plugin(constants.HTTP_DISTRIBUTOR, NodesHttpDistributor, {})
        plugin_api._MANAGER.distributors.add_plugin(FAKE_DISTRIBUTOR, FakeDistributor, FAKE_DISTRIBUTOR_CONFIG)
        plugin_api._MANAGER.profilers.add_plugin(constants.PROFILER_ID, NodeProfiler, {})

    def tearDown(self):
        WebTest.tearDown(self)
        shutil.rmtree(self.parentfs)
        shutil.rmtree(self.childfs)
        Consumer.get_collection().remove()
        Bind.get_collection().remove()
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        RepoImporter.get_collection().remove()
        RepoContentUnit.get_collection().remove()
        unit_db.clean()

    def define_plugins(self):
        collection = ContentType.get_collection()
        collection.save(dict(id=self.TYPEDEF_ID, unit_key=self.UNIT_KEY.keys()), safe=True)

    def populate(self):
        # make content/ dir.
        os.makedirs(os.path.join(self.parentfs, 'content'))
        pulp_conf.set('server', 'storage_dir', self.parentfs)
        # create repo
        manager = managers.repo_manager()
        manager.create_repo(
            self.REPO_ID, display_name=REPO_NAME, description=REPO_DESCRIPTION, notes=REPO_NOTES)
        manager.set_repo_scratchpad(self.REPO_ID, REPO_SCRATCHPAD)
        # add units
        units = self.add_units(0, self.NUM_UNITS)
        self.units = units

    def node_configuration(self):
        path = os.path.join(self.parentfs, 'node.crt')
        with open(path, 'w+') as fp:
            fp.write(NODE_CERTIFICATE)
        node_conf = Config({'main': {constants.NODE_CERTIFICATE: path}})
        return node_conf.graph()

    def add_units(self, begin, end):
        units = []
        storage_dir = os.path.join(pulp_conf.get('server', 'storage_dir'), 'content')
        if not os.path.exists(storage_dir):
            os.makedirs(storage_dir)
        for n in range(begin, end):
            unit_id = self.UNIT_ID % n
            unit = dict(self.UNIT_KEY)
            unit.update(self.UNIT_METADATA)
            unit['N'] = n
            # add unit file
            storage_path = os.path.join(storage_dir, '.'.join((unit_id, self.UNIT_TYPE_ID)))
            if n % 2 == 0:  # even numbered has file associated
                unit['_storage_path'] = storage_path
                if n == 0:  # 1st one is a directory of files
                    os.makedirs(storage_path)
                    dist_path = os.path.join(os.path.dirname(__file__), 'data/distribution.tar')
                    tb = tarfile.open(dist_path)
                    tb.extractall(path=storage_path)
                    tb.close()
                else:
                    with open(storage_path, 'w+') as fp:
                        fp.write(unit_id)
            # add unit
            manager = managers.content_manager()
            manager.add_content_unit(
                self.UNIT_TYPE_ID,
                unit_id,
                unit)
            manager = managers.repo_unit_association_manager()
            # associate unit
            manager.associate_unit_by_id(
                self.REPO_ID,
                self.UNIT_TYPE_ID,
                unit_id,
                RepoContentUnit.OWNER_TYPE_IMPORTER,
                constants.HTTP_IMPORTER)
            units.append(unit)
        return units

    def dist_conf(self):
        return {
            'protocol':'file',
            'http':{'alias':self.alias},
            'https':{'alias':self.alias},
            'file':{'alias':self.alias},
        }


# --- handler tests ------------------------------------------------


class AgentHandlerTest(PluginTestBase):

    @patch('pulp_node.handlers.model.RepositoryBinding.fetch_all')
    def test_node_handler_get_bindings_failed(self, mock_fetch):
        # Setup
        handler = NodeHandler({})
        mock_fetch.side_effect = error.GetBindingsError(500)
        # Test
        options = {
            constants.PARENT_SETTINGS: self.PARENT_SETTINGS,
            constants.STRATEGY_KEYWORD: constants.MIRROR_STRATEGY,
        }
        conduit = AgentConduit()
        report = handler.update(conduit, [], options)
        # Verify
        details = report.details
        errors = details['errors']
        self.assertFalse(report.succeeded)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['error_id'], error.GetBindingsError.ERROR_ID)
        self.assertTrue(errors[0]['details']['http_code'], 500)

    @patch('pulp_node.handlers.model.RepositoryBinding.fetch',
           side_effect=error.GetBindingsError(500))
    def test_repository_handler_get_bindings_failed(self, *unused):
        # Setup
        handler = RepositoryHandler({})
        # Test & Verify
        options = {
            constants.PARENT_SETTINGS: self.PARENT_SETTINGS,
            constants.STRATEGY_KEYWORD: constants.MIRROR_STRATEGY,
        }
        self.assertRaises(error.GetBindingsError, handler.update, AgentConduit(), [], options)


# --- pulp plugin tests --------------------------------------------


class TestProfiler(PluginTestBase):

    def test_entry_point(self):
        _class, conf = profiler_entry_point()
        plugin = _class()
        self.assertTrue(isinstance(plugin, NodeProfiler))

    @patch('pulp_node.profilers.nodes.read_config')
    def test_update_units(self, mock_read_config):
        # Setup
        mock_read_config.return_value = self.node_configuration()
        # Test
        host = 'abc'
        port = 443
        units = [1, 2, 3]
        options = {}
        p = NodeProfiler()
        pulp_conf.set('server', 'server_name', host)
        _units = p.update_units(None, units, options, None, None)
        # Verify
        self.assertTrue(constants.PARENT_SETTINGS in options)
        settings = options[constants.PARENT_SETTINGS]
        self.assertEqual(settings[constants.HOST], host)
        self.assertEqual(settings[constants.PORT], port)
        self.assertEqual(settings[constants.NODE_CERTIFICATE], NODE_CERTIFICATE)
        self.assertEqual(units, _units)


class TestDistributor(PluginTestBase):

    VALID_CONFIGURATION = {
        constants.PROTOCOL_KEYWORD: 'https',
        'http': {
            'alias': [
                '/pulp/nodes/http/repos',
                '/var/www/pulp/nodes/http/repos'
            ]
        },
        'https': {
            'alias': [
                '/pulp/nodes/https/repos',
                '/var/www/pulp/nodes/https/repos'
            ]
        }
    }

    PAYLOAD = {
        'repository': None,
        'distributors': [],
        'importers': [
            {'id': 'nodes_http_importer',
             'importer_type_id': 'nodes_http_importer',
             'config': {
                 'manifest_url': 'file://localhost/%(tmp_dir)s/%(repo_id)s/manifest.json',
                 'strategy': constants.ADDITIVE_STRATEGY
             }, }
        ]
    }

    def test_entry_point(self):
        repo = plugin_model.Repository(self.REPO_ID)
        _class, conf = dist_entry_point()
        plugin = _class()
        plugin.validate_config(repo, conf, [])

    def test_metadata(self):
        # Test
        md = NodesHttpDistributor.metadata()
        self.assertTrue(isinstance(md, dict))
        # Verify
        self.assertTrue('node' in md['types'])

    def test_valid_config(self):
        # Test
        dist = NodesHttpDistributor()
        repo = plugin_model.Repository(self.REPO_ID)
        report = dist.validate_config(repo, self.VALID_CONFIGURATION, [])
        # Verify
        self.assertTrue(isinstance(report, tuple))
        self.assertTrue(len(report), 2)
        self.assertTrue(isinstance(report[0], bool))
        self.assertTrue(report[0])
        self.assertEqual(report[1], None)

    def test_config_missing_protocol(self):
        # Test
        conf = deepcopy(self.VALID_CONFIGURATION)
        del conf[constants.PROTOCOL_KEYWORD]
        dist = NodesHttpDistributor()
        repo = plugin_model.Repository(self.REPO_ID)
        report = dist.validate_config(repo, {}, [])
        # Verify
        self.assertTrue(isinstance(report, tuple))
        self.assertTrue(len(report), 2)
        self.assertTrue(isinstance(report[0], bool))
        self.assertFalse(report[0])
        self.assertFalse(report[1] is None)

    def test_config_missing_http_protocol(self):
        # Test
        conf = deepcopy(self.VALID_CONFIGURATION)
        for protocol in ('http', 'https'):
            del conf[protocol]
            dist = NodesHttpDistributor()
            repo = plugin_model.Repository(self.REPO_ID)
            report = dist.validate_config(repo, {}, [])
            # Verify
            self.assertTrue(isinstance(report, tuple))
            self.assertTrue(len(report), 2)
            self.assertTrue(isinstance(report[0], bool))
            self.assertFalse(report[0])
            self.assertFalse(report[1] is None)

    def test_config_missing_alias(self):
        # Test
        conf = deepcopy(self.VALID_CONFIGURATION)
        del conf['https']['alias']
        dist = NodesHttpDistributor()
        repo = plugin_model.Repository(self.REPO_ID)
        report = dist.validate_config(repo, {}, [])
        # Verify
        self.assertTrue(isinstance(report, tuple))
        self.assertTrue(len(report), 2)
        self.assertTrue(isinstance(report[0], bool))
        self.assertFalse(report[0])
        self.assertFalse(report[1] is None)

    def test_config_missing_invalid_alias(self):
        # Test
        conf = deepcopy(self.VALID_CONFIGURATION)
        conf['https']['alias'] = None
        dist = NodesHttpDistributor()
        repo = plugin_model.Repository(self.REPO_ID)
        report = dist.validate_config(repo, {}, [])
        # Verify
        self.assertTrue(isinstance(report, tuple))
        self.assertTrue(len(report), 2)
        self.assertTrue(isinstance(report[0], bool))
        self.assertFalse(report[0])
        self.assertFalse(report[1] is None)

    def test_payload(self):
        # Setup
        self.populate()
        pulp_conf.set('server', 'storage_dir', self.parentfs)
        # Test
        dist = NodesHttpDistributor()
        repo = Repository(self.REPO_ID)
        payload = dist.create_consumer_payload(repo, self.dist_conf(), {})
        f = open('/tmp/payload', 'w+')
        f.write(repr(payload['importers']))
        f.close()
        # Verify
        distributors = payload['distributors']
        importers = payload['importers']
        repository = payload['repository']
        self.assertTrue(isinstance(distributors, list))
        self.assertTrue(isinstance(importers, list))
        self.assertTrue(isinstance(repository, dict))
        self.assertTrue(len(importers), 1)
        for key in ('id', 'importer_type_id', 'config'):
            self.assertTrue(key in importers[0])
        for key in (constants.MANIFEST_URL_KEYWORD, constants.STRATEGY_KEYWORD):
            self.assertTrue(key in importers[0]['config'])

    def test_publish(self):
        # Setup
        self.populate()
        pulp_conf.set('server', 'storage_dir', self.parentfs)
        # Test
        dist = NodesHttpDistributor()
        repo = Repository(self.REPO_ID)
        conduit = RepoPublishConduit(self.REPO_ID, constants.HTTP_DISTRIBUTOR)
        dist.publish_repo(repo, conduit, self.dist_conf())
        # Verify
        conf = DownloaderConfig()
        downloader = LocalFileDownloader(conf)
        pub = dist.publisher(repo, self.dist_conf())
        url = pathlib.url_join(pub.base_url, pub.manifest_path())
        working_dir = self.childfs
        manifest = RemoteManifest(url, downloader, working_dir)
        manifest.fetch()
        manifest.fetch_units()
        units = [u for u, r in manifest.get_units()]
        self.assertEqual(len(units), self.NUM_UNITS)
        for n in range(0, self.NUM_UNITS):
            unit = units[n]
            created = self.units[n]
            for p, v in unit['unit_key'].items():
                self.assertEqual(created[p], v)
            for p, v in unit['metadata'].items():
                if p in ('_ns', '_content_type_id'):
                    continue
                self.assertEqual(created[p], v)
            self.assertEqual(created.get('_storage_path'), unit['storage_path'])
            self.assertEqual(unit['type_id'], self.UNIT_TYPE_ID)


class ImporterTest(PluginTestBase):

    VALID_CONFIGURATION = {
        constants.STRATEGY_KEYWORD: constants.DEFAULT_STRATEGY,
        constants.MANIFEST_URL_KEYWORD: 'http://redhat.com',
    }

    def test_entry_point(self):
        repo = plugin_model.Repository(self.REPO_ID)
        _class, conf = imp_entry_point()
        plugin = _class()
        plugin.validate_config(repo, conf)

    def test_metadata(self):
        # Test
        md = NodesHttpImporter.metadata()
        # Verify
        self.assertTrue(isinstance(md, dict))
        self.assertTrue('node' in md['types'])
        self.assertTrue('repository' in md['types'])

    def test_valid_config(self):
        # Test
        importer = NodesHttpImporter()
        repo = plugin_model.Repository(self.REPO_ID)
        report = importer.validate_config(repo, self.VALID_CONFIGURATION)
        # Verify
        self.assertTrue(isinstance(report, tuple))
        self.assertTrue(len(report), 2)
        self.assertTrue(isinstance(report[0], bool))
        self.assertTrue(report[0])
        self.assertEqual(len(report[1]), 0)

    def test_config_missing_properties(self):
        # Test
        importer = NodesHttpImporter()
        repo = plugin_model.Repository(self.REPO_ID)
        report = importer.validate_config(repo, {})
        # Verify
        self.assertTrue(isinstance(report, tuple))
        self.assertTrue(len(report), 2)
        self.assertTrue(isinstance(report[0], bool))
        self.assertFalse(report[0])
        self.assertTrue(len(report[1]), 3)

    def test_invalid_strategy(self):
        # Test
        conf = deepcopy(self.VALID_CONFIGURATION)
        conf[constants.STRATEGY_KEYWORD] = '---',
        importer = NodesHttpImporter()
        repo = plugin_model.Repository(self.REPO_ID)
        report = importer.validate_config(repo, conf)
        # Verify
        self.assertTrue(isinstance(report, tuple))
        self.assertTrue(len(report), 2)
        self.assertTrue(isinstance(report[0], bool))
        self.assertFalse(report[0])
        self.assertTrue(len(report[1]), 1)

    @patch('pulp.server.async.task_status_manager.TaskStatusManager.update_task_status')
    @patch('pulp_node.importers.http.importer.Downloader', LocalFileDownloader)
    @patch('pulp_node.importers.http.importer.importer_config_to_nectar_config',
           wraps=importer_config_to_nectar_config)
    def test_import(self, *mocks):
        # Setup
        self.populate()
        max_concurrency = 5
        max_bandwidth = 12345
        pulp_conf.set('server', 'storage_dir', self.parentfs)
        dist = NodesHttpDistributor()
        working_dir = os.path.join(self.childfs, 'working_dir')
        os.makedirs(working_dir)
        repo = Repository(self.REPO_ID, working_dir)
        cfg = self.dist_conf()
        conduit = RepoPublishConduit(self.REPO_ID, constants.HTTP_DISTRIBUTOR)
        dist.publish_repo(repo, conduit, cfg)
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        RepoContentUnit.get_collection().remove()
        unit_db.clean()
        self.define_plugins()
        # Test
        importer = NodesHttpImporter()
        publisher = dist.publisher(repo, cfg)
        manifest_url = pathlib.url_join(publisher.base_url, publisher.manifest_path())
        configuration = {
            constants.MANIFEST_URL_KEYWORD: manifest_url,
            constants.STRATEGY_KEYWORD: constants.MIRROR_STRATEGY,
            importer_constants.KEY_MAX_DOWNLOADS: max_concurrency,
            importer_constants.KEY_MAX_SPEED: max_bandwidth,
        }
        configuration = PluginCallConfiguration(configuration, {})
        conduit = RepoSyncConduit(
            self.REPO_ID,
            constants.HTTP_IMPORTER,
            RepoContentUnit.OWNER_TYPE_IMPORTER,
            constants.HTTP_IMPORTER)
        pulp_conf.set('server', 'storage_dir', self.childfs)
        importer.sync_repo(repo, conduit, configuration)
        # Verify
        units = conduit.get_units()
        self.assertEquals(len(units), self.NUM_UNITS)
        mock_importer_config_to_nectar_config = mocks[0]
        mock_importer_config_to_nectar_config.assert_called_with(configuration.flatten())

    @patch('pulp.server.async.task_status_manager.TaskStatusManager.update_task_status')
    @patch('pulp_node.importers.http.importer.Downloader', LocalFileDownloader)
    @patch('pulp_node.manifest.RemoteManifest.fetch_units')
    def test_import_cached_manifest_matched(self, mock_fetch, *unused):
        # Setup
        self.populate()
        pulp_conf.set('server', 'storage_dir', self.parentfs)
        dist = NodesHttpDistributor()
        working_dir = os.path.join(self.childfs, 'working_dir')
        os.makedirs(working_dir)
        repo = Repository(self.REPO_ID, working_dir)
        configuration = self.dist_conf()
        conduit = RepoPublishConduit(self.REPO_ID, constants.HTTP_DISTRIBUTOR)
        dist.publish_repo(repo, conduit, configuration)
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        RepoContentUnit.get_collection().remove()
        unit_db.clean()
        self.define_plugins()
        publisher = dist.publisher(repo, configuration)
        manifest_path = publisher.manifest_path()
        units_path = os.path.join(os.path.dirname(manifest_path), UNITS_FILE_NAME)
        manifest = Manifest(manifest_path)
        manifest.read()
        shutil.copy(manifest_path, os.path.join(working_dir, MANIFEST_FILE_NAME))
        shutil.copy(units_path, os.path.join(working_dir, UNITS_FILE_NAME))
        # Test
        importer = NodesHttpImporter()
        manifest_url = pathlib.url_join(publisher.base_url, manifest_path)
        configuration = {
            constants.MANIFEST_URL_KEYWORD: manifest_url,
            constants.STRATEGY_KEYWORD: constants.MIRROR_STRATEGY,
        }
        configuration = PluginCallConfiguration(configuration, {})
        conduit = RepoSyncConduit(
            self.REPO_ID,
            constants.HTTP_IMPORTER,
            RepoContentUnit.OWNER_TYPE_IMPORTER,
            constants.HTTP_IMPORTER)
        pulp_conf.set('server', 'storage_dir', self.childfs)
        importer.sync_repo(repo, conduit, configuration)
        # Verify
        units = conduit.get_units()
        self.assertEquals(len(units), self.NUM_UNITS)
        self.assertFalse(mock_fetch.called)

    @patch('pulp.server.async.task_status_manager.TaskStatusManager.update_task_status')
    @patch('pulp_node.importers.http.importer.Downloader', LocalFileDownloader)
    def test_import_cached_manifest_missing_units(self, *unused):
        # Setup
        self.populate()
        pulp_conf.set('server', 'storage_dir', self.parentfs)
        dist = NodesHttpDistributor()
        working_dir = os.path.join(self.childfs, 'working_dir')
        os.makedirs(working_dir)
        repo = Repository(self.REPO_ID, working_dir)
        configuration = self.dist_conf()
        conduit = RepoPublishConduit(self.REPO_ID, constants.HTTP_DISTRIBUTOR)
        dist.publish_repo(repo, conduit, configuration)
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        RepoContentUnit.get_collection().remove()
        unit_db.clean()
        self.define_plugins()
        publisher = dist.publisher(repo, configuration)
        manifest_path = publisher.manifest_path()
        manifest = Manifest(manifest_path)
        manifest.read()
        shutil.copy(manifest_path, os.path.join(working_dir, MANIFEST_FILE_NAME))
        # Test
        importer = NodesHttpImporter()
        manifest_url = pathlib.url_join(publisher.base_url, manifest_path)
        configuration = {
            constants.MANIFEST_URL_KEYWORD: manifest_url,
            constants.STRATEGY_KEYWORD: constants.MIRROR_STRATEGY,
        }
        configuration = PluginCallConfiguration(configuration, {})
        conduit = RepoSyncConduit(
            self.REPO_ID,
            constants.HTTP_IMPORTER,
            RepoContentUnit.OWNER_TYPE_IMPORTER,
            constants.HTTP_IMPORTER)
        pulp_conf.set('server', 'storage_dir', self.childfs)
        importer.sync_repo(repo, conduit, configuration)
        # Verify
        units = conduit.get_units()
        self.assertEquals(len(units), self.NUM_UNITS)

    @patch('pulp.server.async.task_status_manager.TaskStatusManager.update_task_status')
    @patch('pulp_node.importers.http.importer.Downloader', LocalFileDownloader)
    def test_import_cached_manifest_units_invalid(self, *unused):
        # Setup
        self.populate()
        pulp_conf.set('server', 'storage_dir', self.parentfs)
        dist = NodesHttpDistributor()
        working_dir = os.path.join(self.childfs, 'working_dir')
        os.makedirs(working_dir)
        repo = Repository(self.REPO_ID, working_dir)
        configuration = self.dist_conf()
        conduit = RepoPublishConduit(self.REPO_ID, constants.HTTP_DISTRIBUTOR)
        dist.publish_repo(repo, conduit, configuration)
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        RepoContentUnit.get_collection().remove()
        unit_db.clean()
        self.define_plugins()
        publisher = dist.publisher(repo, configuration)
        manifest_path = publisher.manifest_path()
        manifest = Manifest(manifest_path)
        manifest.read()
        shutil.copy(manifest_path, os.path.join(working_dir, MANIFEST_FILE_NAME))
        with open(os.path.join(working_dir, UNITS_FILE_NAME), 'w+') as fp:
            fp.write('invalid-units')
        # Test
        importer = NodesHttpImporter()
        manifest_url = pathlib.url_join(publisher.base_url, manifest_path)
        configuration = {
            constants.MANIFEST_URL_KEYWORD: manifest_url,
            constants.STRATEGY_KEYWORD: constants.MIRROR_STRATEGY,
        }
        configuration = PluginCallConfiguration(configuration, {})
        conduit = RepoSyncConduit(
            self.REPO_ID,
            constants.HTTP_IMPORTER,
            RepoContentUnit.OWNER_TYPE_IMPORTER,
            constants.HTTP_IMPORTER)
        pulp_conf.set('server', 'storage_dir', self.childfs)
        importer.sync_repo(repo, conduit, configuration)
        # Verify
        units = conduit.get_units()
        self.assertEquals(len(units), self.NUM_UNITS)

    @patch('pulp.server.async.task_status_manager.TaskStatusManager.update_task_status')
    @patch('pulp_node.importers.http.importer.Downloader', LocalFileDownloader)
    @patch('pulp_node.importers.http.importer.importer_config_to_nectar_config',
           wraps=importer_config_to_nectar_config)
    def test_import_unit_files_already_exist(self, *mocks):
        # Setup
        self.populate()
        pulp_conf.set('server', 'storage_dir', self.parentfs)
        dist = NodesHttpDistributor()
        working_dir = os.path.join(self.childfs, 'working_dir')
        os.makedirs(working_dir)
        repo = Repository(self.REPO_ID, working_dir)
        cfg = self.dist_conf()
        conduit = RepoPublishConduit(self.REPO_ID, constants.HTTP_DISTRIBUTOR)
        dist.publish_repo(repo, conduit, cfg)
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        RepoContentUnit.get_collection().remove()
        unit_db.clean()
        self.define_plugins()
        parent_content = os.path.join(self.parentfs, 'content')
        child_content = os.path.join(self.childfs, 'content')
        shutil.copytree(parent_content, child_content)
        # Test
        importer = NodesHttpImporter()
        publisher = dist.publisher(repo, cfg)
        manifest_url = pathlib.url_join(publisher.base_url, publisher.manifest_path())
        configuration = {
            constants.MANIFEST_URL_KEYWORD: manifest_url,
            constants.STRATEGY_KEYWORD: constants.MIRROR_STRATEGY,
        }
        configuration = PluginCallConfiguration(configuration, {})
        conduit = RepoSyncConduit(
            self.REPO_ID,
            constants.HTTP_IMPORTER,
            RepoContentUnit.OWNER_TYPE_IMPORTER,
            constants.HTTP_IMPORTER)
        pulp_conf.set('server', 'storage_dir', self.childfs)
        importer.sync_repo(repo, conduit, configuration)
        # Verify
        units = conduit.get_units()
        self.assertEquals(len(units), self.NUM_UNITS)
        mock_importer_config_to_nectar_config = mocks[0]
        mock_importer_config_to_nectar_config.assert_called_with(configuration.flatten())

    @patch('pulp.server.async.task_status_manager.TaskStatusManager.update_task_status')
    @patch('pulp_node.importers.http.importer.Downloader', LocalFileDownloader)
    @patch('pulp_node.importers.http.importer.importer_config_to_nectar_config',
           wraps=importer_config_to_nectar_config)
    def test_import_unit_files_already_exist_size_mismatch(self, *mocks):
        # Setup
        self.populate()
        pulp_conf.set('server', 'storage_dir', self.parentfs)
        dist = NodesHttpDistributor()
        working_dir = os.path.join(self.childfs, 'working_dir')
        os.makedirs(working_dir)
        repo = Repository(self.REPO_ID, working_dir)
        cfg = self.dist_conf()
        conduit = RepoPublishConduit(self.REPO_ID, constants.HTTP_DISTRIBUTOR)
        dist.publish_repo(repo, conduit, cfg)
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        RepoContentUnit.get_collection().remove()
        unit_db.clean()
        self.define_plugins()
        parent_content = os.path.join(self.parentfs, 'content')
        child_content = os.path.join(self.childfs, 'content')
        shutil.copytree(parent_content, child_content)
        for fn in os.listdir(child_content):
            path = os.path.join(child_content, fn)
            if os.path.isdir(path):
                continue
            with open(path, 'w') as fp:
                fp.truncate()
        # Test
        importer = NodesHttpImporter()
        publisher = dist.publisher(repo, cfg)
        manifest_url = pathlib.url_join(publisher.base_url, publisher.manifest_path())
        configuration = {
            constants.MANIFEST_URL_KEYWORD: manifest_url,
            constants.STRATEGY_KEYWORD: constants.MIRROR_STRATEGY,
        }
        configuration = PluginCallConfiguration(configuration, {})
        conduit = RepoSyncConduit(
            self.REPO_ID,
            constants.HTTP_IMPORTER,
            RepoContentUnit.OWNER_TYPE_IMPORTER,
            constants.HTTP_IMPORTER)
        pulp_conf.set('server', 'storage_dir', self.childfs)
        importer.sync_repo(repo, conduit, configuration)
        # Verify
        units = conduit.get_units()
        self.assertEquals(len(units), self.NUM_UNITS)
        mock_importer_config_to_nectar_config = mocks[0]
        mock_importer_config_to_nectar_config.assert_called_with(configuration.flatten())

    @patch('pulp.server.async.task_status_manager.TaskStatusManager.update_task_status')
    @patch('pulp_node.importers.http.importer.Downloader', LocalFileDownloader)
    @patch('pulp_node.importers.http.importer.importer_config_to_nectar_config',
           wraps=importer_config_to_nectar_config)
    def test_import_modified_units(self, *mocks):
        # Setup
        self.populate()
        max_concurrency = 5
        max_bandwidth = 12345
        pulp_conf.set('server', 'storage_dir', self.parentfs)
        dist = NodesHttpDistributor()
        working_dir = os.path.join(self.childfs, 'working_dir')
        os.makedirs(working_dir)
        repo = Repository(self.REPO_ID, working_dir)
        cfg = self.dist_conf()
        conduit = RepoPublishConduit(self.REPO_ID, constants.HTTP_DISTRIBUTOR)
        dist.publish_repo(repo, conduit, cfg)
        # make the published unit have a newer _last_updated.
        collection = connection.get_collection(unit_db.unit_collection_name(self.UNIT_TYPE_ID))
        unit = collection.find_one({'N': 0})
        unit['age'] = 84
        unit['_last_updated'] -= 1
        collection.update({'N': 0}, unit, safe=True)
        # Test
        importer = NodesHttpImporter()
        publisher = dist.publisher(repo, cfg)
        manifest_url = pathlib.url_join(publisher.base_url, publisher.manifest_path())
        configuration = {
            constants.MANIFEST_URL_KEYWORD: manifest_url,
            constants.STRATEGY_KEYWORD: constants.MIRROR_STRATEGY,
            importer_constants.KEY_MAX_DOWNLOADS: max_concurrency,
            importer_constants.KEY_MAX_SPEED: max_bandwidth,
        }
        configuration = PluginCallConfiguration(configuration, {})
        conduit = RepoSyncConduit(
            self.REPO_ID,
            constants.HTTP_IMPORTER,
            RepoContentUnit.OWNER_TYPE_IMPORTER,
            constants.HTTP_IMPORTER)
        pulp_conf.set('server', 'storage_dir', self.childfs)
        importer.sync_repo(repo, conduit, configuration)
        # Verify
        unit = collection.find_one({'N': 0})
        self.assertEqual(unit['age'], 42)
