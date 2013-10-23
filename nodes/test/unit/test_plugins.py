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
from nectar.request import DownloadRequest
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
from pulp.bindings.bindings import Bindings
from pulp.bindings.server import PulpConnection
from pulp.server.config import config as pulp_conf
from pulp.agent.lib.conduit import Conduit
from pulp.agent.lib.container import CONTENT, Container
from pulp.agent.lib.dispatcher import Dispatcher
from pulp_node.manifest import Manifest, RemoteManifest, MANIFEST_FILE_NAME, UNITS_FILE_NAME
from pulp_node.handlers.strategies import Mirror, Additive
from pulp_node.handlers.reports import RepositoryReport
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

    def __init__(self, url, *args, **kwargs):
        url = 'http:/NOWHERE/FAIL_ME_%d' % random.random()
        DownloadRequest.__init__(self, url, *args, **kwargs)


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
        manager.create_repo(self.REPO_ID)
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

    @patch('pulp_node.handlers.model.RepositoryBinding.fetch_all',
           side_effect=error.GetBindingsError(500))
    def test_node_handler_get_bindings_failed(self, *unused):
        # Setup
        handler = NodeHandler({})
        # Test & Verify
        options = {
            constants.PARENT_SETTINGS: self.PARENT_SETTINGS,
            constants.STRATEGY_KEYWORD: constants.MIRROR_STRATEGY,
        }
        self.assertRaises(error.GetBindingsError, handler.update, AgentConduit(), [], options)

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

    @patch('pulp_node.resources.node_configuration')
    def test_update_units(self, mock_get_node_conf):
        # Setup
        mock_get_node_conf.return_value = self.node_configuration()
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


# --- testing end-to-end -----------------------------------------------------

class TestEndToEnd(PluginTestBase):
    """
    These tests perform end-to-end testing using a pulp server as both the parent and child.
    Then, we basically synchronize the server to itself.
    Here is how it works:
      1. Create (2) directories in /tmp that act as the storage location for the parent and child
      2. Populate a pulp sever with repositories and content units using the 'parent'
         storage directory as the _storage_path.
      3. Mock the strategies to point to our testing classes.  Their job is to act as a hook into
         the synchronization process.  At this hook, we transform the pulp server that had been
         acting as our parent into our child node.  The transformation is mainly removing specified
         items from the inventory to simulate certain senarios.
      4. Initiate the node synchronization.
      5. Verify the result.

    File system tree (example):

            nodes/
            ├── child-2BUtUa
            │   ├── content
            │   │   └── test_unit.rpm
            │   └── working
            │       └── repos
            │           └── test-repo
            │               ├── distributors
            │               │   └── nodes_http_distributor
            │               └── importers
            │                   └── nodes_http_importer
            ├── storage
            └── Parent-SgASM7
                ├── content
                │   └── test_unit.rpm
                ├── test-repo
                │   ├── content
                │   │   └── 3ae69ea97c -> /tmp/pulp/nodes/Parent-SgASM7/content/test_unit.rpm
                │   └── units.json
                └── working
                    └── repos
                        └── test-repo
                            ├── distributors
                            │   └── nodes_http_distributor
                            └── importers
                                └── nodes_http_importer

    """

    PULP_ID = 'child'

    def populate(self, strategy=constants.DEFAULT_STRATEGY):
        PluginTestBase.populate(self)
        # register child
        manager = managers.consumer_manager()
        manager.register(self.PULP_ID)
        manager = managers.repo_importer_manager()
        # add importer
        importer_conf = {
            constants.MANIFEST_URL_KEYWORD: 'http://redhat.com',
            constants.STRATEGY_KEYWORD: constants.DEFAULT_STRATEGY,
        }
        manager.set_importer(self.REPO_ID, constants.HTTP_IMPORTER, importer_conf)
        # add distributors
        dist_conf = self.dist_conf()
        manager = managers.repo_distributor_manager()
        manager.add_distributor(
            self.REPO_ID,
            constants.HTTP_DISTRIBUTOR,
            dist_conf,
            False,
            constants.HTTP_DISTRIBUTOR)
        manager.add_distributor(self.REPO_ID, FAKE_DISTRIBUTOR, FAKE_DISTRIBUTOR_CONFIG, False, FAKE_ID)
        # bind
        conf = {constants.STRATEGY_KEYWORD: strategy}
        manager = managers.consumer_bind_manager()
        manager.bind(self.PULP_ID, self.REPO_ID, constants.HTTP_DISTRIBUTOR, False, conf)

    def clean(self,
              repo=True,
              units=True,
              plugins=False,
              extra_units=0,
              extra_repos=None,
              dist_config=None):
        # remove repository & bindings
        if repo:
            Bind.get_collection().remove()
            Repo.get_collection().remove()
            RepoDistributor.get_collection().remove()
            RepoImporter.get_collection().remove()
        # remove all content units
        if units:
            RepoContentUnit.get_collection().remove()
            unit_db.clean()
            self.define_plugins()
        # add extra content units
        if extra_units:
            self.add_units(self.NUM_UNITS, self.NUM_UNITS + extra_units)
        # add extra repositories
        if extra_repos:
            manager = managers.repo_manager()
            for repo_id in extra_repos:
                manager.create_repo(repo_id)
        # distributor config changed
        if dist_config is not None:
            manager = managers.repo_distributor_manager()
            manager.update_distributor_config(self.REPO_ID, FAKE_ID, dist_config)
        # clear pulp plugins
        if plugins:
            plugin_api._MANAGER.distributors.plugins = {}

    def verify(self, num_units=PluginTestBase.NUM_UNITS):
        # repository
        manager = managers.repo_query_manager()
        manager.get_repository(self.REPO_ID)
        # importer
        manager = managers.repo_importer_manager()
        importer = manager.get_importer(self.REPO_ID)
        manifest_url = importer['config'][constants.MANIFEST_URL_KEYWORD]
        self.assertTrue(manifest_url.endswith('%s/manifest.json' % self.REPO_ID))
        # distributor
        manager = managers.repo_distributor_manager()
        manager.get_distributor(self.REPO_ID, FAKE_ID)
        # check units
        manager = managers.repo_unit_association_query_manager()
        units = manager.get_units(self.REPO_ID)
        #units = dict([(u['metadata']['N'], u) for u in units])
        self.assertEqual(len(units), num_units)
        for unit in units:
            metadata = unit['metadata']
            unit_id = self.UNIT_ID % metadata['N']  # injected by test
            storage_path = metadata['_storage_path']
            if not storage_path:
                # no file associated with the unit
                continue
            storage_path = storage_path.replace('//', '/')
            self.assertEqual(unit['unit_type_id'], self.UNIT_TYPE_ID)
            self.assertEqual(unit['repo_id'], self.REPO_ID)
            self.assertEqual(unit['owner_id'], constants.HTTP_IMPORTER)
            file_path = '.'.join((unit_id, self.UNIT_TYPE_ID))
            self.assertEqual(storage_path, os.path.join(self.childfs, 'content', file_path))
            self.assertTrue(os.path.exists(storage_path))
            if os.path.isfile(storage_path):
                fp = open(storage_path)
                content = fp.read()
                fp.close()
                self.assertEqual(content, unit_id)
            else:
                self.assertTrue(os.path.isdir(storage_path))
                self.assertEqual(len(os.listdir(storage_path)), 4)

    def test_handler_mirror(self):
        """
        Test end-to-end functionality using the mirroring strategy.
        """
        _report = []
        conn = PulpConnection(None, server_wrapper=self)
        binding = Bindings(conn)
        @patch('pulp_node.resources.pulp_bindings', return_value=binding)
        @patch('pulp_node.resources.parent_bindings', return_value=binding)
        @patch('pulp_node.handlers.handler.find_strategy', return_value=MirrorTestStrategy(self))
        @patch('pulp_node.importers.http.importer.Downloader', LocalFileDownloader)
        def test_handler(*unused):
            # publish
            self.populate(constants.MIRROR_STRATEGY)
            pulp_conf.set('server', 'storage_dir', self.parentfs)
            dist = NodesHttpDistributor()
            repo = Repository(self.REPO_ID)
            conduit = RepoPublishConduit(self.REPO_ID, constants.HTTP_DISTRIBUTOR)
            dist.publish_repo(repo, conduit, self.dist_conf())
            options = {
                constants.PARENT_SETTINGS: self.PARENT_SETTINGS,
                constants.STRATEGY_KEYWORD: constants.MIRROR_STRATEGY,
                constants.PURGE_ORPHANS_KEYWORD: True,
            }
            units = [{'type_id':'node', 'unit_key':None}]
            pulp_conf.set('server', 'storage_dir', self.childfs)
            container = Container(self.parentfs)
            dispatcher = Dispatcher(container)
            container.handlers[CONTENT]['node'] = NodeHandler(self)
            container.handlers[CONTENT]['repository'] = RepositoryHandler(self)
            agent_conduit = AgentConduit(self.PULP_ID)
            report = dispatcher.update(agent_conduit, units, options)
            _report.append(report)
        test_handler()
        # Verify
        report = _report[0].details['node']
        self.assertTrue(report['succeeded'])
        errors = report['details']['errors']
        repositories = report['details']['repositories']
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(repositories), 1)
        repository = repositories[0]
        self.assertEqual(repository['repo_id'], self.REPO_ID)
        self.assertEqual(repository['action'], RepositoryReport.ADDED)
        units = repository['units']
        self.assertEqual(units['added'], self.NUM_UNITS)
        self.assertEqual(units['updated'], 0)
        self.assertEqual(units['removed'], 0)
        diff = 'diff %s/content %s/content' % (self.parentfs, self.childfs)
        self.assertEqual(os.system(diff), 0)
        self.verify()

    def test_handler_cancelled(self):
        """
        Test end-to-end functionality using the mirroring strategy.
        """
        _report = []
        conn = PulpConnection(None, server_wrapper=self)
        binding = Bindings(conn)
        @patch('pulp_node.resources.pulp_bindings', return_value=binding)
        @patch('pulp_node.resources.parent_bindings', return_value=binding)
        @patch('pulp_node.handlers.handler.find_strategy', return_value=MirrorTestStrategy(self))
        @patch('pulp.agent.lib.conduit.Conduit.cancelled', return_value=True)
        @patch('pulp_node.importers.http.importer.Downloader', LocalFileDownloader)
        def test_handler(*unused):
            # publish
            self.populate(constants.MIRROR_STRATEGY)
            pulp_conf.set('server', 'storage_dir', self.parentfs)
            dist = NodesHttpDistributor()
            repo = Repository(self.REPO_ID)
            conduit = RepoPublishConduit(self.REPO_ID, constants.HTTP_DISTRIBUTOR)
            dist.publish_repo(repo, conduit, self.dist_conf())
            options = {
                constants.PARENT_SETTINGS: self.PARENT_SETTINGS,
                constants.STRATEGY_KEYWORD: constants.MIRROR_STRATEGY,
                constants.PURGE_ORPHANS_KEYWORD: True,
            }
            units = [{'type_id':'node', 'unit_key':None}]
            pulp_conf.set('server', 'storage_dir', self.childfs)
            container = Container(self.parentfs)
            dispatcher = Dispatcher(container)
            container.handlers[CONTENT]['node'] = NodeHandler(self)
            container.handlers[CONTENT]['repository'] = RepositoryHandler(self)
            agent_conduit = AgentConduit(self.PULP_ID)
            report = dispatcher.update(agent_conduit, units, options)
            _report.append(report)
        test_handler()
        # Verify
        report = _report[0].details['node']
        self.assertTrue(report['succeeded'])
        errors = report['details']['errors']
        repositories = report['details']['repositories']
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(repositories), 1)
        repository = repositories[0]
        self.assertEqual(repository['repo_id'], self.REPO_ID)
        self.assertEqual(repository['action'], RepositoryReport.CANCELLED)
        units = repository['units']
        self.assertEqual(units['added'], 0)
        self.assertEqual(units['updated'], 0)
        self.assertEqual(units['removed'], 0)

    @patch('pulp_node.importers.http.importer.NodesHttpImporter.sync_repo')
    def test_handler_content_skip(self, mock_importer):
        """
        Test end-to-end functionality using the mirroring strategy.
        """
        _report = []
        conn = PulpConnection(None, server_wrapper=self)
        binding = Bindings(conn)
        @patch('pulp_node.resources.pulp_bindings', return_value=binding)
        @patch('pulp_node.resources.parent_bindings', return_value=binding)
        @patch('pulp_node.handlers.handler.find_strategy', return_value=MirrorTestStrategy(self))
        def test_handler(*unused):
            # publish
            self.populate(constants.MIRROR_STRATEGY)
            pulp_conf.set('server', 'storage_dir', self.parentfs)
            dist = NodesHttpDistributor()
            repo = Repository(self.REPO_ID)
            conduit = RepoPublishConduit(self.REPO_ID, constants.HTTP_DISTRIBUTOR)
            dist.publish_repo(repo, conduit, self.dist_conf())
            options = {
                constants.PARENT_SETTINGS: self.PARENT_SETTINGS,
                constants.STRATEGY_KEYWORD: constants.MIRROR_STRATEGY,
                constants.SKIP_CONTENT_UPDATE_KEYWORD: True
            }
            units = [{'type_id': 'node', 'unit_key': None}]
            pulp_conf.set('server', 'storage_dir', self.childfs)
            container = Container(self.parentfs)
            dispatcher = Dispatcher(container)
            container.handlers[CONTENT]['node'] = NodeHandler(self)
            container.handlers[CONTENT]['repository'] = RepositoryHandler(self)
            agent_conduit = AgentConduit(self.PULP_ID)
            report = dispatcher.update(agent_conduit, units, options)
            _report.append(report)
        test_handler()
        # Verify
        report = _report[0].details['node']
        self.assertTrue(report['succeeded'])
        errors = report['details']['errors']
        repositories = report['details']['repositories']
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(repositories), 1)
        repository = repositories[0]
        self.assertEqual(repository['repo_id'], self.REPO_ID)
        self.assertEqual(repository['action'], RepositoryReport.ADDED)
        units = repository['units']
        self.assertEqual(units['added'], 0)
        self.assertEqual(units['updated'], 0)
        self.assertEqual(units['removed'], 0)
        self.assertFalse(mock_importer.called)

    def test_handler_additive(self):
        """
        Test end-to-end functionality using the additive strategy.
        """
        _report = []
        conn = PulpConnection(None, server_wrapper=self)
        binding = Bindings(conn)
        @patch('pulp_node.resources.pulp_bindings', return_value=binding)
        @patch('pulp_node.resources.parent_bindings', return_value=binding)
        @patch('pulp_node.handlers.handler.find_strategy',
               return_value=AdditiveTestStrategy(self, extra_repos=self.EXTRA_REPO_IDS))
        @patch('pulp_node.importers.http.importer.Downloader', LocalFileDownloader)
        def test_handler(*unused):
            # publish
            self.populate(constants.ADDITIVE_STRATEGY)
            pulp_conf.set('server', 'storage_dir', self.parentfs)
            dist = NodesHttpDistributor()
            repo = Repository(self.REPO_ID)
            conduit = RepoPublishConduit(self.REPO_ID, constants.HTTP_DISTRIBUTOR)
            dist.publish_repo(repo, conduit, self.dist_conf())
            options = {
                constants.PARENT_SETTINGS: self.PARENT_SETTINGS,
                constants.STRATEGY_KEYWORD: constants.ADDITIVE_STRATEGY,
            }
            units = [{'type_id':'node', 'unit_key':None}]
            pulp_conf.set('server', 'storage_dir', self.childfs)
            container = Container(self.parentfs)
            dispatcher = Dispatcher(container)
            container.handlers[CONTENT]['node'] = NodeHandler(self)
            container.handlers[CONTENT]['repository'] = RepositoryHandler(self)
            agent_conduit = AgentConduit(self.PULP_ID)
            report = dispatcher.update(agent_conduit, units, options)
            _report.append(report)
        test_handler()
        # Verify
        report = _report[0].details['node']
        self.assertTrue(report['succeeded'])
        errors = report['details']['errors']
        repositories = report['details']['repositories']
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(repositories), 1)
        repository = repositories[0]
        self.assertEqual(repository['repo_id'], self.REPO_ID)
        self.assertEqual(repository['action'], RepositoryReport.ADDED)
        units = repository['units']
        self.assertEqual(units['added'], self.NUM_UNITS)
        self.assertEqual(units['updated'], 0)
        self.assertEqual(units['removed'], 0)
        self.verify()
        manager = managers.repo_query_manager()
        all = manager.find_all()
        self.assertEqual(len(all), 1 + len(self.EXTRA_REPO_IDS))

    def test_handler_mirror_repository_scope(self):
        """
        Test end-to-end functionality using the mirror strategy and
        invoke using 'repository' units.  The goal is to make sure that the
        extra repositories are not affected.  Behaves like the additive strategy.
        """
        _report = []
        conn = PulpConnection(None, server_wrapper=self)
        binding = Bindings(conn)
        @patch('pulp_node.resources.pulp_bindings', return_value=binding)
        @patch('pulp_node.resources.parent_bindings', return_value=binding)
        @patch('pulp_node.handlers.handler.find_strategy',
               return_value=AdditiveTestStrategy(self, extra_repos=self.EXTRA_REPO_IDS))
        @patch('pulp_node.importers.http.importer.Downloader', LocalFileDownloader)
        def test_handler(*unused):
            # publish
            self.populate(constants.MIRROR_STRATEGY)
            pulp_conf.set('server', 'storage_dir', self.parentfs)
            dist = NodesHttpDistributor()
            repo = Repository(self.REPO_ID)
            conduit = RepoPublishConduit(self.REPO_ID, constants.HTTP_DISTRIBUTOR)
            dist.publish_repo(repo, conduit, self.dist_conf())
            options = {
                constants.PARENT_SETTINGS: self.PARENT_SETTINGS,
                constants.STRATEGY_KEYWORD: constants.MIRROR_STRATEGY,
            }
            units = [{'type_id': 'repository', 'unit_key': {'repo_id': self.REPO_ID}}]
            pulp_conf.set('server', 'storage_dir', self.childfs)
            container = Container(self.parentfs)
            dispatcher = Dispatcher(container)
            container.handlers[CONTENT]['node'] = NodeHandler(self)
            container.handlers[CONTENT]['repository'] = RepositoryHandler(self)
            agent_conduit = AgentConduit(self.PULP_ID)
            report = dispatcher.update(agent_conduit, units, options)
            _report.append(report)
        test_handler()
        # Verify
        report = _report[0].details['repository']
        self.assertTrue(report['succeeded'])
        errors = report['details']['errors']
        repositories = report['details']['repositories']
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(repositories), 1)
        repository = repositories[0]
        self.assertEqual(repository['repo_id'], self.REPO_ID)
        self.assertEqual(repository['action'], RepositoryReport.ADDED)
        units = repository['units']
        self.assertEqual(units['added'], self.NUM_UNITS)
        self.assertEqual(units['updated'], 0)
        self.assertEqual(units['removed'], 0)
        self.verify()
        manager = managers.repo_query_manager()
        all = manager.find_all()
        self.assertEqual(len(all), 1 + len(self.EXTRA_REPO_IDS))

    def test_handler_merge(self):
        """
        Test end-to-end functionality using the mirror strategy. We don't clean the repositories
        to they will be merged instead of added as new.
        """
        _report = []
        conn = PulpConnection(None, server_wrapper=self)
        binding = Bindings(conn)
        @patch('pulp_node.resources.pulp_bindings', return_value=binding)
        @patch('pulp_node.resources.parent_bindings', return_value=binding)
        @patch('pulp_node.handlers.handler.find_strategy',
               return_value=MirrorTestStrategy(self, repo=False, units=True))
        @patch('pulp_node.importers.http.importer.Downloader', LocalFileDownloader)
        def test_handler(*unused):
            # publish
            self.populate(constants.MIRROR_STRATEGY)
            pulp_conf.set('server', 'storage_dir', self.parentfs)
            dist = NodesHttpDistributor()
            repo = Repository(self.REPO_ID)
            conduit = RepoPublishConduit(self.REPO_ID, constants.HTTP_DISTRIBUTOR)
            dist.publish_repo(repo, conduit, self.dist_conf())
            units = []
            options = {
                constants.PARENT_SETTINGS: self.PARENT_SETTINGS,
                constants.STRATEGY_KEYWORD: constants.MIRROR_STRATEGY,
            }
            handler = NodeHandler(self)
            pulp_conf.set('server', 'storage_dir', self.childfs)
            agent_conduit = AgentConduit(self.PULP_ID)
            report = handler.update(agent_conduit, units, options)
            _report.append(report)
        test_handler()
        # Verify
        report = _report[0]
        self.assertTrue(report.succeeded)
        errors = report.details['errors']
        repositories = report.details['repositories']
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(repositories), 1)
        repository = repositories[0]
        self.assertEqual(repository['repo_id'], self.REPO_ID)
        self.assertEqual(repository['action'], RepositoryReport.MERGED)
        units = repository['units']
        self.assertEqual(units['added'], self.NUM_UNITS)
        self.assertEqual(units['updated'], 0)
        self.assertEqual(units['removed'], 0)
        self.verify()

    def test_handler_merge_dist_changed(self):
        """
        Test end-to-end functionality using the mirror strategy. We don't clean the repositories
        to they will be merged instead of added as new.
        """
        _report = []
        conn = PulpConnection(None, server_wrapper=self)
        binding = Bindings(conn)
        @patch('pulp_node.resources.pulp_bindings', return_value=binding)
        @patch('pulp_node.resources.parent_bindings', return_value=binding)
        @patch('pulp_node.handlers.handler.find_strategy',
               return_value=MirrorTestStrategy(self, repo=False, units=True, dist_config={'A': 1}))
        @patch('pulp_node.importers.http.importer.Downloader', LocalFileDownloader)
        def test_handler(*unused):
            # publish
            self.populate(constants.MIRROR_STRATEGY)
            pulp_conf.set('server', 'storage_dir', self.parentfs)
            dist = NodesHttpDistributor()
            repo = Repository(self.REPO_ID)
            conduit = RepoPublishConduit(self.REPO_ID, constants.HTTP_DISTRIBUTOR)
            dist.publish_repo(repo, conduit, self.dist_conf())
            units = []
            options = {
                constants.PARENT_SETTINGS: self.PARENT_SETTINGS,
                constants.STRATEGY_KEYWORD: constants.MIRROR_STRATEGY,
            }
            handler = NodeHandler(self)
            pulp_conf.set('server', 'storage_dir', self.childfs)
            agent_conduit = AgentConduit(self.PULP_ID)
            report = handler.update(agent_conduit, units, options)
            _report.append(report)
        test_handler()
        # Verify
        report = _report[0]
        self.assertTrue(report.succeeded)
        errors = report.details['errors']
        repositories = report.details['repositories']
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(repositories), 1)
        repository = repositories[0]
        self.assertEqual(repository['repo_id'], self.REPO_ID)
        self.assertEqual(repository['action'], RepositoryReport.MERGED)
        units = repository['units']
        self.assertEqual(units['added'], self.NUM_UNITS)
        self.assertEqual(units['updated'], 0)
        self.assertEqual(units['removed'], 0)
        self.verify()
        manager = managers.repo_distributor_manager()
        dist = manager.get_distributor(self.REPO_ID, FAKE_ID)
        self.assertEqual(dist['config'], FAKE_DISTRIBUTOR_CONFIG)

    def test_handler_merge_and_delete_extra_units(self):
        """
        Test end-to-end functionality using the mirror strategy.  We only clean the units so
        the repositories will be merged.  During the clean, we add units on the child that are
        not on the parent and expect them to be removed by the mirror strategy.
        """
        _report = []
        conn = PulpConnection(None, server_wrapper=self)
        binding = Bindings(conn)
        @patch('pulp_node.resources.pulp_bindings', return_value=binding)
        @patch('pulp_node.resources.parent_bindings', return_value=binding)
        @patch('pulp_node.handlers.handler.find_strategy',
               return_value=MirrorTestStrategy(self, repo=False, extra_units=self.NUM_EXTRA_UNITS))
        @patch('pulp_node.importers.http.importer.Downloader', LocalFileDownloader)
        def test_handler(*unused):
            # publish
            self.populate(constants.MIRROR_STRATEGY)
            pulp_conf.set('server', 'storage_dir', self.parentfs)
            dist = NodesHttpDistributor()
            repo = Repository(self.REPO_ID)
            conduit = RepoPublishConduit(self.REPO_ID, constants.HTTP_DISTRIBUTOR)
            dist.publish_repo(repo, conduit, self.dist_conf())
            units = []
            options = {
                constants.PARENT_SETTINGS: self.PARENT_SETTINGS,
                constants.STRATEGY_KEYWORD: constants.MIRROR_STRATEGY,
            }
            handler = NodeHandler(self)
            pulp_conf.set('server', 'storage_dir', self.childfs)
            agent_conduit = AgentConduit(self.PULP_ID)
            report = handler.update(agent_conduit, units, options)
            _report.append(report)
        test_handler()
        # Verify
        report = _report[0]
        self.assertTrue(report.succeeded)
        errors = report.details['errors']
        repositories = report.details['repositories']
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(repositories), 1)
        repository = repositories[0]
        self.assertEqual(repository['repo_id'], self.REPO_ID)
        self.assertEqual(repository['action'], RepositoryReport.MERGED)
        units = repository['units']
        self.assertEqual(units['added'], self.NUM_UNITS)
        self.assertEqual(units['updated'], 0)
        self.assertEqual(units['removed'], self.NUM_EXTRA_UNITS)
        self.verify()

    def test_handler_merge_and_delete_repositories(self):
        """
        Test end-to-end functionality using the mirror strategy.  We only clean the units so
        the repositories will be merged.  During the clean, we add repositories on the child that
        are not on the parent and expect them to be removed by the mirror strategy.
        """
        _report = []
        conn = PulpConnection(None, server_wrapper=self)
        binding = Bindings(conn)
        @patch('pulp_node.resources.pulp_bindings', return_value=binding)
        @patch('pulp_node.resources.parent_bindings', return_value=binding)
        @patch('pulp_node.handlers.handler.find_strategy',
               return_value=MirrorTestStrategy(self, repo=False, units=True, extra_repos=self.EXTRA_REPO_IDS))
        @patch('pulp_node.importers.http.importer.Downloader', LocalFileDownloader)
        def test_handler(*unused):
            # publish
            self.populate(constants.MIRROR_STRATEGY)
            pulp_conf.set('server', 'storage_dir', self.parentfs)
            dist = NodesHttpDistributor()
            repo = Repository(self.REPO_ID)
            conduit = RepoPublishConduit(self.REPO_ID, constants.HTTP_DISTRIBUTOR)
            dist.publish_repo(repo, conduit, self.dist_conf())
            units = []
            options = {
                constants.PARENT_SETTINGS: self.PARENT_SETTINGS,
                constants.STRATEGY_KEYWORD: constants.MIRROR_STRATEGY,
            }
            handler = NodeHandler(self)
            pulp_conf.set('server', 'storage_dir', self.childfs)
            agent_conduit = AgentConduit(self.PULP_ID)
            report = handler.update(agent_conduit, units, options)
            _report.append(report)
        test_handler()
        # Verify
        report = _report[0]
        self.assertTrue(report.succeeded)
        errors = report.details['errors']
        repositories = report.details['repositories']
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(repositories), len(self.EXTRA_REPO_IDS) + 1)
        # merged repository
        repository = repositories[0]
        self.assertEqual(repository['repo_id'], self.REPO_ID)
        self.assertEqual(repository['action'], RepositoryReport.MERGED)
        units = repository['units']
        self.assertEqual(units['added'], self.NUM_UNITS)
        self.assertEqual(units['updated'], 0)
        self.assertEqual(units['removed'], 0)
        # deleted extra repositories
        for i in range(0, len(self.EXTRA_REPO_IDS)):
            repository = repositories[i + 1]
            self.assertEqual(repository['repo_id'], self.EXTRA_REPO_IDS[i])
            self.assertEqual(repository['action'], RepositoryReport.DELETED)
            units = repository['units']
            self.assertEqual(units['added'], 0)
            self.assertEqual(units['updated'], 0)
            self.assertEqual(units['removed'], 0)
        # verify end result
        self.verify()

    def test_handler_unit_errors(self):
        """
        Test end-to-end functionality using the additive strategy with unit download errors.
        """
        _report = []
        conn = PulpConnection(None, server_wrapper=self)
        binding = Bindings(conn)
        @patch('pulp_node.resources.pulp_bindings', return_value=binding)
        @patch('pulp_node.resources.parent_bindings', return_value=binding)
        @patch('pulp_node.importers.download.DownloadRequest', BadDownloadRequest)
        @patch('pulp_node.handlers.handler.find_strategy', return_value=MirrorTestStrategy(self))
        @patch('pulp_node.importers.http.importer.Downloader', LocalFileDownloader)
        def test_handler(*unused):
            # publish
            self.populate(constants.ADDITIVE_STRATEGY)
            pulp_conf.set('server', 'storage_dir', self.parentfs)
            dist = NodesHttpDistributor()
            repo = Repository(self.REPO_ID)
            conduit = RepoPublishConduit(self.REPO_ID, constants.HTTP_DISTRIBUTOR)
            dist.publish_repo(repo, conduit, self.dist_conf())
            units = []
            options = {
                constants.PARENT_SETTINGS: self.PARENT_SETTINGS,
                constants.STRATEGY_KEYWORD: constants.MIRROR_STRATEGY,
            }
            handler = NodeHandler(self)
            pulp_conf.set('server', 'storage_dir', self.childfs)
            os.makedirs(os.path.join(self.childfs, 'content'))
            agent_conduit = AgentConduit(self.PULP_ID)
            report = handler.update(agent_conduit, units, options)
            _report.append(report)
        test_handler()
        # Verify
        report = _report[0]
        self.assertFalse(report.succeeded)
        errors = report.details['errors']
        repositories = report.details['repositories']
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['error_id'], error.UnitDownloadError.ERROR_ID)
        self.assertEqual(errors[0]['details']['repo_id'], self.REPO_ID)
        self.assertEqual(len(repositories), 1)
        repository = repositories[0]
        self.assertEqual(repository['repo_id'], self.REPO_ID)
        self.assertEqual(repository['action'], RepositoryReport.ADDED)
        units = repository['units']
        num_units_added = self.NUM_UNITS / 2
        self.assertEqual(units['added'], num_units_added)
        self.assertEqual(units['updated'], 0)
        self.assertEqual(units['removed'], 0)
        self.verify(num_units_added)

    def test_handler_nothing_updated(self):
        """
        Test end-to-end functionality using the additive strategy with nothing updated.
        """
        _report = []
        conn = PulpConnection(None, server_wrapper=self)
        binding = Bindings(conn)
        @patch('pulp_node.resources.pulp_bindings', return_value=binding)
        @patch('pulp_node.resources.parent_bindings', return_value=binding)
        @patch('pulp_node.importers.download.DownloadRequest', BadDownloadRequest)
        @patch('pulp_node.importers.http.importer.Downloader', LocalFileDownloader)
        def test_handler(*unused):
            # publish
            self.populate(constants.ADDITIVE_STRATEGY)
            pulp_conf.set('server', 'storage_dir', self.parentfs)
            dist = NodesHttpDistributor()
            repo = Repository(self.REPO_ID)
            conduit = RepoPublishConduit(self.REPO_ID, constants.HTTP_DISTRIBUTOR)
            dist.publish_repo(repo, conduit, self.dist_conf())
            units = []
            options = {
                constants.PARENT_SETTINGS: self.PARENT_SETTINGS,
                constants.STRATEGY_KEYWORD: constants.MIRROR_STRATEGY,
            }
            handler = NodeHandler(self)
            pulp_conf.set('server', 'storage_dir', self.childfs)
            os.makedirs(os.path.join(self.childfs, 'content'))
            agent_conduit = AgentConduit(self.PULP_ID)
            report = handler.update(agent_conduit, units, options)
            _report.append(report)
        test_handler()
        # Verify
        report = _report[0]
        self.assertTrue(report.succeeded)
        errors = report.details['errors']
        repositories = report.details['repositories']
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(repositories), 1)
        repository = repositories[0]
        self.assertEqual(repository['repo_id'], self.REPO_ID)
        self.assertEqual(repository['action'], RepositoryReport.MERGED)
        units = repository['units']
        self.assertEqual(units['added'], 0)
        self.assertEqual(units['updated'], 0)
        self.assertEqual(units['removed'], 0)

    @patch('pulp_node.importers.strategies.Mirror._add_units', side_effect=Exception())
    def test_importer_exception(self, *unused):
        """
        Test end-to-end functionality using the mirror strategy with an importer exception
        """
        _report = []
        conn = PulpConnection(None, server_wrapper=self)
        binding = Bindings(conn)
        @patch('pulp_node.resources.pulp_bindings', return_value=binding)
        @patch('pulp_node.resources.parent_bindings', return_value=binding)
        @patch('pulp_node.handlers.handler.find_strategy', return_value=MirrorTestStrategy(self))
        @patch('pulp_node.importers.http.importer.Downloader', LocalFileDownloader)
        def test_handler(*unused):
            # publish
            self.populate(constants.MIRROR_STRATEGY)
            pulp_conf.set('server', 'storage_dir', self.parentfs)
            dist = NodesHttpDistributor()
            repo = Repository(self.REPO_ID)
            cfg = self.dist_conf()
            conduit = RepoPublishConduit(self.REPO_ID, constants.HTTP_DISTRIBUTOR)
            dist.publish_repo(repo, conduit, cfg)
            units = []
            options = {
                constants.PARENT_SETTINGS: self.PARENT_SETTINGS,
                constants.STRATEGY_KEYWORD: constants.MIRROR_STRATEGY,
            }
            handler = NodeHandler(self)
            pulp_conf.set('server', 'storage_dir', self.childfs)
            os.makedirs(os.path.join(self.childfs, 'content'))
            agent_conduit = AgentConduit(self.PULP_ID)
            report = handler.update(agent_conduit, units, options)
            _report.append(report)
        test_handler()
        # Verify
        report = _report[0]
        self.assertFalse(report.succeeded)
        errors = report.details['errors']
        repositories = report.details['repositories']
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['error_id'], error.CaughtException.ERROR_ID)
        self.assertEqual(errors[0]['details']['repo_id'], self.REPO_ID)
        self.assertEqual(len(repositories), 1)
        repository = repositories[0]
        self.assertEqual(repository['repo_id'], self.REPO_ID)
        self.assertEqual(repository['action'], RepositoryReport.ADDED)
        units = repository['units']
        self.assertEqual(units['added'], 0)
        self.assertEqual(units['updated'], 0)
        self.assertEqual(units['removed'], 0)
        self.verify(0)

    def test_missing_plugins(self):
        """
        Test end-to-end functionality using the mirror strategy with missing distributor plugins.
        """
        _report = []
        conn = PulpConnection(None, server_wrapper=self)
        binding = Bindings(conn)
        @patch('pulp_node.resources.pulp_bindings', return_value=binding)
        @patch('pulp_node.resources.parent_bindings', return_value=binding)
        @patch('pulp_node.handlers.handler.find_strategy', return_value=MirrorTestStrategy(self, plugins=True))
        @patch('pulp_node.importers.http.importer.Downloader', LocalFileDownloader)
        def test_handler(*unused):
            # publish
            self.populate(constants.MIRROR_STRATEGY)
            pulp_conf.set('server', 'storage_dir', self.parentfs)
            dist = NodesHttpDistributor()
            repo = Repository(self.REPO_ID)
            conduit = RepoPublishConduit(self.REPO_ID, constants.HTTP_DISTRIBUTOR)
            dist.publish_repo(repo, conduit, self.dist_conf())
            options = {
                constants.PARENT_SETTINGS: self.PARENT_SETTINGS,
                constants.STRATEGY_KEYWORD: constants.MIRROR_STRATEGY,
            }
            units = [{'type_id':'node', 'unit_key':None}]
            pulp_conf.set('server', 'storage_dir', self.childfs)
            container = Container(self.parentfs)
            dispatcher = Dispatcher(container)
            container.handlers[CONTENT]['node'] = NodeHandler(self)
            container.handlers[CONTENT]['repository'] = RepositoryHandler(self)
            agent_conduit = AgentConduit(self.PULP_ID)
            report = dispatcher.update(agent_conduit, units, options)
            _report.append(report)
        test_handler()
        # Verify
        report = _report[0].details['node']
        self.assertFalse(report['succeeded'])
        errors = report['details']['errors']
        repositories = report['details']['repositories']
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['error_id'], error.DistributorNotInstalled.ERROR_ID)
        self.assertEqual(errors[0]['details']['repo_id'], self.REPO_ID)
        self.assertEqual(errors[0]['details']['type_id'], 'test_distributor')
        self.assertEqual(len(repositories), 1)
        repository = repositories[0]
        self.assertEqual(repository['repo_id'], self.REPO_ID)
        self.assertEqual(repository['action'], RepositoryReport.PENDING)
        units = repository['units']
        self.assertEqual(units['added'], 0)
        self.assertEqual(units['updated'], 0)
        self.assertEqual(units['removed'], 0)

    def test_repository_handler(self):
        """
        Test end-to-end functionality using the mirror strategy. We add extra repositories on the
        child that are not on the parent and expect them to be preserved.
        """
        _report = []
        conn = PulpConnection(None, server_wrapper=self)
        binding = Bindings(conn)
        @patch('pulp_node.resources.pulp_bindings', return_value=binding)
        @patch('pulp_node.resources.parent_bindings', return_value=binding)
        @patch('pulp_node.handlers.handler.find_strategy', return_value=MirrorTestStrategy(self))
        @patch('pulp_node.importers.http.importer.Downloader', LocalFileDownloader)
        def test_handler(*unused):
            # publish
            self.populate(constants.ADDITIVE_STRATEGY)
            pulp_conf.set('server', 'storage_dir', self.parentfs)
            dist = NodesHttpDistributor()
            repo = Repository(self.REPO_ID)
            conduit = RepoPublishConduit(self.REPO_ID, constants.HTTP_DISTRIBUTOR)
            dist.publish_repo(repo, conduit, self.dist_conf())
            options = {
                constants.PARENT_SETTINGS: self.PARENT_SETTINGS,
                constants.STRATEGY_KEYWORD: constants.ADDITIVE_STRATEGY,
            }
            units = [{'type_id':'repository', 'unit_key':dict(repo_id=self.REPO_ID)}]
            pulp_conf.set('server', 'storage_dir', self.childfs)
            container = Container(self.parentfs)
            dispatcher = Dispatcher(container)
            container.handlers[CONTENT]['node'] = NodeHandler(self)
            container.handlers[CONTENT]['repository'] = RepositoryHandler(self)
            agent_conduit = AgentConduit(self.PULP_ID)
            report = dispatcher.update(agent_conduit, units, options)
            _report.append(report)
        test_handler()
        # Verify
        report = _report[0].details['repository']
        self.assertTrue(report['succeeded'])
        errors = report['details']['errors']
        repositories = report['details']['repositories']
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(repositories), 1)
        repository = repositories[0]
        self.assertEqual(repository['repo_id'], self.REPO_ID)
        self.assertEqual(repository['action'], RepositoryReport.ADDED)
        units = repository['units']
        self.assertEqual(units['added'], self.NUM_UNITS)
        self.assertEqual(units['updated'], 0)
        self.assertEqual(units['removed'], 0)
        self.verify()
