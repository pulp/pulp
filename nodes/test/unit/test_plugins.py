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

from copy import deepcopy

from mock import Mock, patch
from base import WebTest

from nectar.downloaders.curl import HTTPSCurlDownloader
from nectar.request import DownloadRequest
from nectar.config import DownloaderConfig

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/mocks")

from pulp_node.distributors.http.distributor import NodesHttpDistributor
from pulp_node.importers.http.importer import NodesHttpImporter
from pulp_node.handlers.handler import NodeHandler, RepositoryHandler

from pulp.plugins.loader import api as plugin_api
from pulp.plugins.types import database as unit_db
from pulp.server.db.model.repository import Repo, RepoDistributor, RepoImporter
from pulp.server.db.model.repository import RepoContentUnit
from pulp.server.db.model.consumer import Consumer, Bind
from pulp.server.exceptions import MissingResource
from pulp.plugins import model as plugin_model
from pulp.plugins.conduits.repo_publish import RepoPublishConduit
from pulp.plugins.conduits.repo_sync import RepoSyncConduit
from pulp.server.managers import factory as managers
from pulp.bindings.bindings import Bindings
from pulp.bindings.server import PulpConnection
from pulp.server.config import config as pulp_conf
from pulp.agent.lib.conduit import Conduit
from pulp.agent.lib.container import CONTENT, Container
from pulp.agent.lib.dispatcher import Dispatcher
from pulp_node.manifest import Manifest
from pulp_node.handlers.strategies import Mirror, Additive
from pulp_node.handlers.reports import RepositoryReport
from pulp_node import error
from pulp_node import constants


FAKE_DISTRIBUTOR = 'test_distributor'


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


# --- testing base classes ---------------------------------------------------


class PluginTestBase(WebTest):

    REPO_ID = 'test-repo'
    UNIT_TYPE_ID = 'rpm'
    UNIT_ID = 'test_unit_%d'
    UNIT_METADATA = {'A':'a','B':'b', 'N': 0}
    TYPEDEF_ID = UNIT_TYPE_ID
    NUM_UNITS = 10
    NUM_EXTRA_UNITS = 5
    EXTRA_REPO_IDS = ('extra_1', 'extra_2')

    CA_CERT = 'CA_CERTIFICATE'
    CLIENT_CERT = 'CLIENT_CERTIFICATE_AND_KEY'

    @classmethod
    def tmpdir(cls, role):
        dir = tempfile.mkdtemp(dir=cls.TMP_ROOT, prefix=role)
        return dir

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
        plugin_api._create_manager()
        imp_conf = dict(strategy=constants.MIRROR_STRATEGY)
        plugin_api._MANAGER.importers.add_plugin(constants.HTTP_IMPORTER, NodesHttpImporter, imp_conf)
        plugin_api._MANAGER.distributors.add_plugin(constants.HTTP_DISTRIBUTOR, NodesHttpDistributor, {})
        plugin_api._MANAGER.distributors.add_plugin(FAKE_DISTRIBUTOR, FakeDistributor, {})
        unit_db.type_definition = \
            Mock(return_value=dict(id=self.TYPEDEF_ID, unit_key=self.UNIT_METADATA))
        unit_db.type_units_unit_key = \
            Mock(return_value=['A', 'B', 'N'])

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

    def populate(self):
        # make content/ dir.
        os.makedirs(os.path.join(self.parentfs, 'content'))
        pulp_conf.set('server', 'storage_dir', self.parentfs)
        # create repo
        manager = managers.repo_manager()
        manager.create_repo(self.REPO_ID)
        # add units
        units = self.add_units(0, self.NUM_UNITS)
        # CA
        self.units = units
        path = os.path.join(self.parentfs, 'ca.crt')
        fp = open(path, 'w+')
        fp.write(self.CA_CERT)
        fp.close()
        # client cert
        path = os.path.join(self.parentfs, 'local.crt')
        fp = open(path, 'w+')
        fp.write(self.CLIENT_CERT)
        fp.close()

    def add_units(self, begin, end):
        units = []
        for n in range(begin, end):
            unit_id = self.UNIT_ID % n
            unit = dict(self.UNIT_METADATA)
            unit['N'] = n
            # add unit file
            storage_dir = os.path.join(pulp_conf.get('server', 'storage_dir'), 'content')
            if not os.path.exists(storage_dir):
                os.makedirs(storage_dir)
            storage_path = os.path.join(storage_dir, '.'.join((unit_id, self.UNIT_TYPE_ID)))
            if n % 2 == 0:  # even numbered has file associated
                unit['_storage_path'] = storage_path
                fp = open(storage_path, 'w+')
                fp.write(unit_id)
                fp.close()
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

    def dist_conf_with_ssl(self):
        ssl = {
            'client_cert':{
                'local':os.path.join(self.parentfs, 'local.crt'),
                'child':os.path.join(self.childfs, 'parent', 'client.crt')
            }
        }
        d = self.dist_conf()
        d['file']['ssl'] = ssl
        return d


# --- handler tests ------------------------------------------------


class AgentHandlerTest(PluginTestBase):

    @patch('pulp_node.handlers.model.BindingsOnParent.fetch_all', side_effect=error.GetBindingsError(500))
    def test_node_handler_get_bindings_failed(self, *unused):
        # Setup
        handler = NodeHandler({})
        # Test & Verify
        self.assertRaises(error.GetBindingsError, handler.update, Conduit(), [], {})

    @patch('pulp_node.handlers.model.BindingsOnParent.fetch', side_effect=error.GetBindingsError(500))
    def test_repository_handler_get_bindings_failed(self, *unused):
        # Setup
        handler = RepositoryHandler({})
        # Test & Verify
        self.assertRaises(error.GetBindingsError, handler.update, Conduit(), [], {})


# --- pulp plugin tests --------------------------------------------


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
            ],
            constants.SSL_KEYWORD: {
                constants.CLIENT_CERT_KEYWORD: {
                    'local': '/etc/pki/pulp/nodes/local.crt',
                    'child': '/etc/pki/pulp/nodes/parent/client.crt'
                }
            }
        }
    }

    PAYLOAD = {
        'distributors': [],
        'importers': [
            {'id': 'nodes_http_importer',
             'importer_type_id': 'nodes_http_importer',
             'config': {
                 'manifest_url': 'file://localhost/%(tmp_dir)s/%(repo_id)s/manifest.json',
                 'protocol': 'file',
                 'ssl': {},
                 'strategy': 'additive'
             }, }
        ],
        'repository': None
    }

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
        for key in (constants.MANIFEST_URL_KEYWORD, constants.STRATEGY_KEYWORD, constants.SSL_KEYWORD):
            self.assertTrue(key in importers[0]['config'])

    def test_payload_with_ssl(self):
        # Setup
        self.populate()
        pulp_conf.set('server', 'storage_dir', self.parentfs)
        # Test
        dist = NodesHttpDistributor()
        repo = Repository(self.REPO_ID)
        payload = dist.create_consumer_payload(repo, self.dist_conf_with_ssl(), {})
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
        for key in (constants.MANIFEST_URL_KEYWORD, constants.STRATEGY_KEYWORD, constants.SSL_KEYWORD):
            self.assertTrue(key in importers[0]['config'])
        for key in (constants.CLIENT_CERT_KEYWORD,):
            self.assertTrue(key in importers[0]['config'][constants.SSL_KEYWORD])

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
        downloader = HTTPSCurlDownloader(conf)
        manifest = Manifest()
        pub = dist.publisher(repo, self.dist_conf())
        url = '/'.join((pub.base_url, pub.manifest_path()))
        manifest = Manifest()
        manifest.fetch(url, self.childfs, downloader)
        manifest.fetch_units(url, downloader)
        units = [u for u, r in manifest.get_units()]
        self.assertEqual(len(units), self.NUM_UNITS)
        for n in range(0, self.NUM_UNITS):
            unit = units[n]
            created = self.units[n]
            for p, v in unit['unit_key'].items():
                self.assertEqual(created[p], v)
            self.assertEqual(created.get('_storage_path'), unit['storage_path'])
            self.assertEqual(unit['type_id'], self.UNIT_TYPE_ID)


class ImporterTest(PluginTestBase):

    VALID_CONFIGURATION = {
        constants.STRATEGY_KEYWORD: constants.DEFAULT_STRATEGY,
        constants.MANIFEST_URL_KEYWORD: 'http://redhat.com',
        constants.PROTOCOL_KEYWORD: 'http'
    }

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
        report = importer.validate_config(repo, self.VALID_CONFIGURATION, [])
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
        report = importer.validate_config(repo, {}, [])
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
        report = importer.validate_config(repo, conf, [])
        # Verify
        self.assertTrue(isinstance(report, tuple))
        self.assertTrue(len(report), 2)
        self.assertTrue(isinstance(report[0], bool))
        self.assertFalse(report[0])
        self.assertTrue(len(report[1]), 1)

    def test_import(self):
        # Setup
        self.populate()
        pulp_conf.set('server', 'storage_dir', self.parentfs)
        dist = NodesHttpDistributor()
        working_dir = os.path.join(self.childfs, 'working_dir')
        os.makedirs(working_dir)
        repo = Repository(self.REPO_ID, working_dir)
        cfg = {
            'protocol':'file',
            'http':{'alias':self.alias},
            'https':{'alias':self.alias},
            'file':{'alias':self.alias},
        }
        conduit = RepoPublishConduit(self.REPO_ID, constants.HTTP_DISTRIBUTOR)
        dist.publish_repo(repo, conduit, cfg)
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        RepoContentUnit.get_collection().remove()
        unit_db.clean()
        # Test
        importer = NodesHttpImporter()
        publisher = dist.publisher(repo, cfg)
        manifest_url = 'file://' + publisher.manifest_path()
        cfg = dict(manifest_url=manifest_url, strategy=constants.MIRROR_STRATEGY)
        conduit = RepoSyncConduit(
            self.REPO_ID,
            constants.HTTP_IMPORTER,
            RepoContentUnit.OWNER_TYPE_IMPORTER,
            constants.HTTP_IMPORTER)
        pulp_conf.set('server', 'storage_dir', self.childfs)
        report = importer.sync_repo(repo, conduit, cfg)
        # Verify
        units = conduit.get_units()
        self.assertEquals(len(units), self.NUM_UNITS)


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

    def populate(self, strategy=constants.DEFAULT_STRATEGY, ssl=False):
        PluginTestBase.populate(self)
        # register child
        manager = managers.consumer_manager()
        manager.register(self.PULP_ID)
        manager = managers.repo_importer_manager()
        # add importer
        importer_conf = {
            constants.MANIFEST_URL_KEYWORD: 'http://redhat.com',
            constants.STRATEGY_KEYWORD: constants.DEFAULT_STRATEGY,
            constants.PROTOCOL_KEYWORD: 'file',
        }
        manager.set_importer(self.REPO_ID, constants.HTTP_IMPORTER, importer_conf)
        # add distributors
        if ssl:
            dist_conf = self.dist_conf_with_ssl()
        else:
            dist_conf = self.dist_conf()
        manager = managers.repo_distributor_manager()
        manager.add_distributor(
            self.REPO_ID,
            constants.HTTP_DISTRIBUTOR,
            dist_conf,
            False,
            constants.HTTP_DISTRIBUTOR)
        manager.add_distributor(self.REPO_ID, FAKE_DISTRIBUTOR, {}, False, FAKE_DISTRIBUTOR)
        # bind
        conf = {constants.STRATEGY_KEYWORD: strategy}
        manager = managers.consumer_bind_manager()
        manager.bind(self.PULP_ID, self.REPO_ID, constants.HTTP_DISTRIBUTOR, False, conf)

    def clean(self, repo=True, units=True, plugins=False, extra_units=0, extra_repos=None):
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
        # add extra content units
        if extra_units:
            self.add_units(self.NUM_UNITS, self.NUM_UNITS + extra_units)
        # add extra repositories
        if extra_repos:
            manager = managers.repo_manager()
            for repo_id in extra_repos:
                manager.create_repo(repo_id)
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
        manager.get_distributor(self.REPO_ID, FAKE_DISTRIBUTOR)
        self.assertRaises(MissingResource, manager.get_distributor, self.REPO_ID, constants.HTTP_DISTRIBUTOR)
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
            fp = open(storage_path)
            content = fp.read()
            fp.close()
            self.assertEqual(content, unit_id)

    @patch('pulp_node.handlers.strategies.Bundle.cn', return_value=PULP_ID)
    def test_handler_mirror(self, *unused):
        """
        Test end-to-end functionality using the mirroring strategy.
        """
        _report = []
        conn = PulpConnection(None, server_wrapper=self)
        binding = Bindings(conn)
        @patch('pulp_node.handlers.strategies.ChildEntity.binding', binding)
        @patch('pulp_node.handlers.strategies.ParentEntity.binding', binding)
        @patch('pulp_node.handlers.handler.find_strategy', return_value=MirrorTestStrategy(self))
        def test_handler(*unused):
            # publish
            self.populate(constants.MIRROR_STRATEGY)
            pulp_conf.set('server', 'storage_dir', self.parentfs)
            dist = NodesHttpDistributor()
            repo = Repository(self.REPO_ID)
            conduit = RepoPublishConduit(self.REPO_ID, constants.HTTP_DISTRIBUTOR)
            dist.publish_repo(repo, conduit, self.dist_conf())
            options = dict(strategy=constants.MIRROR_STRATEGY, purge_orphans=True)
            units = [{'type_id':'node', 'unit_key':None}]
            pulp_conf.set('server', 'storage_dir', self.childfs)
            container = Container(self.parentfs)
            dispatcher = Dispatcher(container)
            container.handlers[CONTENT]['node'] = NodeHandler(self)
            container.handlers[CONTENT]['repository'] = RepositoryHandler(self)
            report = dispatcher.update(Conduit(), units, options)
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

    @patch('pulp_node.handlers.strategies.Bundle.cn', return_value=PULP_ID)
    def test_handler_cancelled(self, *unused):
        """
        Test end-to-end functionality using the mirroring strategy.
        """
        _report = []
        conn = PulpConnection(None, server_wrapper=self)
        binding = Bindings(conn)
        @patch('pulp_node.handlers.strategies.ChildEntity.binding', binding)
        @patch('pulp_node.handlers.strategies.ParentEntity.binding', binding)
        @patch('pulp_node.handlers.handler.find_strategy', return_value=MirrorTestStrategy(self))
        @patch('pulp.agent.lib.conduit.Conduit.cancelled', return_value=True)
        def test_handler(*unused):
            # publish
            self.populate(constants.MIRROR_STRATEGY)
            pulp_conf.set('server', 'storage_dir', self.parentfs)
            dist = NodesHttpDistributor()
            repo = Repository(self.REPO_ID)
            conduit = RepoPublishConduit(self.REPO_ID, constants.HTTP_DISTRIBUTOR)
            dist.publish_repo(repo, conduit, self.dist_conf())
            options = dict(strategy=constants.MIRROR_STRATEGY, purge_orphans=True)
            units = [{'type_id':'node', 'unit_key':None}]
            pulp_conf.set('server', 'storage_dir', self.childfs)
            container = Container(self.parentfs)
            dispatcher = Dispatcher(container)
            container.handlers[CONTENT]['node'] = NodeHandler(self)
            container.handlers[CONTENT]['repository'] = RepositoryHandler(self)
            report = dispatcher.update(Conduit(), units, options)
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

    @patch('pulp_node.handlers.strategies.Bundle.cn', return_value=PULP_ID)
    def test_handler_additive(self, *unused):
        """
        Test end-to-end functionality using the additive strategy.
        """
        _report = []
        conn = PulpConnection(None, server_wrapper=self)
        binding = Bindings(conn)
        @patch('pulp_node.handlers.strategies.ChildEntity.binding', binding)
        @patch('pulp_node.handlers.strategies.ParentEntity.binding', binding)
        @patch('pulp_node.handlers.handler.find_strategy',
               return_value=AdditiveTestStrategy(self, extra_repos=self.EXTRA_REPO_IDS))
        def test_handler(*unused):
            # publish
            self.populate(constants.ADDITIVE_STRATEGY)
            pulp_conf.set('server', 'storage_dir', self.parentfs)
            dist = NodesHttpDistributor()
            repo = Repository(self.REPO_ID)
            conduit = RepoPublishConduit(self.REPO_ID, constants.HTTP_DISTRIBUTOR)
            dist.publish_repo(repo, conduit, self.dist_conf())
            options = dict(strategy=constants.ADDITIVE_STRATEGY)
            units = [{'type_id':'node', 'unit_key':None}]
            pulp_conf.set('server', 'storage_dir', self.childfs)
            container = Container(self.parentfs)
            dispatcher = Dispatcher(container)
            container.handlers[CONTENT]['node'] = NodeHandler(self)
            container.handlers[CONTENT]['repository'] = RepositoryHandler(self)
            report = dispatcher.update(Conduit(), units, options)
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

    @patch('pulp_node.handlers.strategies.Bundle.cn', return_value=PULP_ID)
    def test_handler_merge(self, unused):
        """
        Test end-to-end functionality using the mirror strategy. We don't clean the repositories
        to they will be merged instead of added as new.
        """
        _report = []
        conn = PulpConnection(None, server_wrapper=self)
        binding = Bindings(conn)
        @patch('pulp_node.handlers.strategies.ChildEntity.binding', binding)
        @patch('pulp_node.handlers.strategies.ParentEntity.binding', binding)
        @patch('pulp_node.handlers.handler.find_strategy',
               return_value=MirrorTestStrategy(self, repo=False, units=True))
        def test_handler(*unused):
            # publish
            self.populate(constants.MIRROR_STRATEGY, ssl=True)
            pulp_conf.set('server', 'storage_dir', self.parentfs)
            dist = NodesHttpDistributor()
            repo = Repository(self.REPO_ID)
            conduit = RepoPublishConduit(self.REPO_ID, constants.HTTP_DISTRIBUTOR)
            dist.publish_repo(repo, conduit, self.dist_conf())
            units = []
            options = dict(strategy=constants.MIRROR_STRATEGY)
            handler = NodeHandler(self)
            pulp_conf.set('server', 'storage_dir', self.childfs)
            report = handler.update(Conduit(), units, options)
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
        path = os.path.join(self.childfs, 'parent', 'client.crt')
        self.assertTrue(os.path.exists(path))

    @patch('pulp_node.handlers.strategies.Bundle.cn', return_value=PULP_ID)
    def test_handler_merge_and_delete_extra_units(self, unused):
        """
        Test end-to-end functionality using the mirror strategy.  We only clean the units so
        the repositories will be merged.  During the clean, we add units on the child that are
        not on the parent and expect them to be removed by the mirror strategy.
        """
        _report = []
        conn = PulpConnection(None, server_wrapper=self)
        binding = Bindings(conn)
        @patch('pulp_node.handlers.strategies.ChildEntity.binding', binding)
        @patch('pulp_node.handlers.strategies.ParentEntity.binding', binding)
        @patch('pulp_node.handlers.handler.find_strategy',
               return_value=MirrorTestStrategy(self, repo=False, extra_units=self.NUM_EXTRA_UNITS))
        def test_handler(*unused):
            # publish
            self.populate(constants.MIRROR_STRATEGY, ssl=True)
            pulp_conf.set('server', 'storage_dir', self.parentfs)
            dist = NodesHttpDistributor()
            repo = Repository(self.REPO_ID)
            conduit = RepoPublishConduit(self.REPO_ID, constants.HTTP_DISTRIBUTOR)
            dist.publish_repo(repo, conduit, self.dist_conf())
            units = []
            options = dict(strategy=constants.MIRROR_STRATEGY)
            handler = NodeHandler(self)
            pulp_conf.set('server', 'storage_dir', self.childfs)
            report = handler.update(Conduit(), units, options)
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
        path = os.path.join(self.childfs, 'parent', 'client.crt')
        self.assertTrue(os.path.exists(path))

    @patch('pulp_node.handlers.strategies.Bundle.cn', return_value=PULP_ID)
    def test_handler_merge_and_delete_repositories(self, unused):
        """
        Test end-to-end functionality using the mirror strategy.  We only clean the units so
        the repositories will be merged.  During the clean, we add repositories on the child that
        are not on the parent and expect them to be removed by the mirror strategy.
        """
        _report = []
        conn = PulpConnection(None, server_wrapper=self)
        binding = Bindings(conn)
        @patch('pulp_node.handlers.strategies.ChildEntity.binding', binding)
        @patch('pulp_node.handlers.strategies.ParentEntity.binding', binding)
        @patch('pulp_node.handlers.handler.find_strategy',
               return_value=MirrorTestStrategy(self, repo=False, units=True, extra_repos=self.EXTRA_REPO_IDS))
        def test_handler(*unused):
            # publish
            self.populate(constants.MIRROR_STRATEGY, ssl=True)
            pulp_conf.set('server', 'storage_dir', self.parentfs)
            dist = NodesHttpDistributor()
            repo = Repository(self.REPO_ID)
            conduit = RepoPublishConduit(self.REPO_ID, constants.HTTP_DISTRIBUTOR)
            dist.publish_repo(repo, conduit, self.dist_conf())
            units = []
            options = dict(strategy=constants.MIRROR_STRATEGY)
            handler = NodeHandler(self)
            pulp_conf.set('server', 'storage_dir', self.childfs)
            report = handler.update(Conduit(), units, options)
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
        path = os.path.join(self.childfs, 'parent', 'client.crt')
        self.assertTrue(os.path.exists(path))

    @patch('pulp_node.handlers.strategies.Bundle.cn', return_value=PULP_ID)
    def test_handler_unit_errors(self, *unused):
        """
        Test end-to-end functionality using the additive strategy with unit download errors.
        """
        _report = []
        conn = PulpConnection(None, server_wrapper=self)
        binding = Bindings(conn)
        @patch('pulp_node.handlers.strategies.ChildEntity.binding', binding)
        @patch('pulp_node.handlers.strategies.ParentEntity.binding', binding)
        @patch('pulp_node.importers.download.DownloadRequest', BadDownloadRequest)
        @patch('pulp_node.handlers.handler.find_strategy', return_value=MirrorTestStrategy(self))
        def test_handler(*unused):
            # publish
            self.populate(constants.ADDITIVE_STRATEGY)
            pulp_conf.set('server', 'storage_dir', self.parentfs)
            dist = NodesHttpDistributor()
            repo = Repository(self.REPO_ID)
            conduit = RepoPublishConduit(self.REPO_ID, constants.HTTP_DISTRIBUTOR)
            dist.publish_repo(repo, conduit, self.dist_conf())
            units = []
            options = dict(strategy=constants.MIRROR_STRATEGY)
            handler = NodeHandler(self)
            pulp_conf.set('server', 'storage_dir', self.childfs)
            os.makedirs(os.path.join(self.childfs, 'content'))
            report = handler.update(Conduit(), units, options)
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

    @patch('pulp_node.handlers.strategies.Bundle.cn', return_value=PULP_ID)
    def test_handler_nothing_updated(self, *unused):
        """
        Test end-to-end functionality using the additive strategy with nothing updated.
        """
        _report = []
        conn = PulpConnection(None, server_wrapper=self)
        binding = Bindings(conn)
        @patch('pulp_node.handlers.strategies.ChildEntity.binding', binding)
        @patch('pulp_node.handlers.strategies.ParentEntity.binding', binding)
        @patch('pulp_node.importers.download.DownloadRequest', BadDownloadRequest)
        def test_handler(*unused):
            # publish
            self.populate(constants.ADDITIVE_STRATEGY)
            pulp_conf.set('server', 'storage_dir', self.parentfs)
            dist = NodesHttpDistributor()
            repo = Repository(self.REPO_ID)
            conduit = RepoPublishConduit(self.REPO_ID, constants.HTTP_DISTRIBUTOR)
            dist.publish_repo(repo, conduit, self.dist_conf())
            units = []
            options = dict(strategy=constants.MIRROR_STRATEGY)
            handler = NodeHandler(self)
            pulp_conf.set('server', 'storage_dir', self.childfs)
            os.makedirs(os.path.join(self.childfs, 'content'))
            report = handler.update(Conduit(), units, options)
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

    @patch('pulp_node.handlers.strategies.Bundle.cn', return_value=PULP_ID)
    @patch('pulp_node.importers.strategies.Mirror._add_units', side_effect=Exception())
    def test_importer_exception(self, *unused):
        """
        Test end-to-end functionality using the mirror strategy with an importer exception
        """
        _report = []
        conn = PulpConnection(None, server_wrapper=self)
        binding = Bindings(conn)
        @patch('pulp_node.handlers.strategies.ChildEntity.binding', binding)
        @patch('pulp_node.handlers.strategies.ParentEntity.binding', binding)
        @patch('pulp_node.handlers.handler.find_strategy', return_value=MirrorTestStrategy(self))
        def test_handler(*unused):
            # publish
            self.populate(constants.MIRROR_STRATEGY)
            pulp_conf.set('server', 'storage_dir', self.parentfs)
            dist = NodesHttpDistributor()
            repo = Repository(self.REPO_ID)
            cfg = {
                'protocol':'file',
                'http':{'alias':self.alias},
                'https':{'alias':self.alias},
                'file':{'alias':self.alias},
            }
            conduit = RepoPublishConduit(self.REPO_ID, constants.HTTP_DISTRIBUTOR)
            dist.publish_repo(repo, conduit, cfg)
            units = []
            options = dict(strategy=constants.MIRROR_STRATEGY)
            handler = NodeHandler(self)
            pulp_conf.set('server', 'storage_dir', self.childfs)
            os.makedirs(os.path.join(self.childfs, 'content'))
            report = handler.update(Conduit(), units, options)
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

    @patch('pulp_node.handlers.strategies.Bundle.cn', return_value=PULP_ID)
    def test_missing_plugins(self, *unused):
        """
        Test end-to-end functionality using the mirror strategy with missing distributor plugins.
        """
        _report = []
        conn = PulpConnection(None, server_wrapper=self)
        binding = Bindings(conn)
        @patch('pulp_node.handlers.strategies.ChildEntity.binding', binding)
        @patch('pulp_node.handlers.strategies.ParentEntity.binding', binding)
        @patch('pulp_node.handlers.handler.find_strategy', return_value=MirrorTestStrategy(self, plugins=True))
        def test_handler(*unused):
            # publish
            self.populate(constants.MIRROR_STRATEGY)
            pulp_conf.set('server', 'storage_dir', self.parentfs)
            dist = NodesHttpDistributor()
            repo = Repository(self.REPO_ID)
            conduit = RepoPublishConduit(self.REPO_ID, constants.HTTP_DISTRIBUTOR)
            dist.publish_repo(repo, conduit, self.dist_conf())
            options = dict(strategy=constants.MIRROR_STRATEGY)
            units = [{'type_id':'node', 'unit_key':None}]
            pulp_conf.set('server', 'storage_dir', self.childfs)
            container = Container(self.parentfs)
            dispatcher = Dispatcher(container)
            container.handlers[CONTENT]['node'] = NodeHandler(self)
            container.handlers[CONTENT]['repository'] = RepositoryHandler(self)
            report = dispatcher.update(Conduit(), units, options)
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

    @patch('pulp_node.handlers.strategies.Bundle.cn', return_value=PULP_ID)
    def test_repository_handler(self, *unused):
        """
        Test end-to-end functionality using the mirror strategy. We add extra repositories on the
        child that are not on the parent and expect them to be preserved.
        """
        _report = []
        conn = PulpConnection(None, server_wrapper=self)
        binding = Bindings(conn)
        @patch('pulp_node.handlers.strategies.ChildEntity.binding', binding)
        @patch('pulp_node.handlers.strategies.ParentEntity.binding', binding)
        @patch('pulp_node.handlers.handler.find_strategy', return_value=MirrorTestStrategy(self))
        def test_handler(*unused):
            # publish
            self.populate(constants.ADDITIVE_STRATEGY)
            pulp_conf.set('server', 'storage_dir', self.parentfs)
            dist = NodesHttpDistributor()
            repo = Repository(self.REPO_ID)
            conduit = RepoPublishConduit(self.REPO_ID, constants.HTTP_DISTRIBUTOR)
            dist.publish_repo(repo, conduit, self.dist_conf())
            options = dict(strategy=constants.ADDITIVE_STRATEGY)
            units = [{'type_id':'repository', 'unit_key':dict(repo_id=self.REPO_ID)}]
            pulp_conf.set('server', 'storage_dir', self.childfs)
            container = Container(self.parentfs)
            dispatcher = Dispatcher(container)
            container.handlers[CONTENT]['node'] = NodeHandler(self)
            container.handlers[CONTENT]['repository'] = RepositoryHandler(self)
            report = dispatcher.update(Conduit(), units, options)
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
