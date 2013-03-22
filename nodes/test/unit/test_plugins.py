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
import time
import random

from mock import Mock, patch
from base import WebTest

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/mocks")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../child")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../parent")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../common")

from pulp_node.distributors.http.distributor import NodesHttpDistributor
from pulp_node.importers.http.importer import NodesHttpImporter
from pulp_node.handlers.handler import NodeHandler, RepositoryHandler

from pulp.plugins.loader import api as plugin_api
from pulp.plugins.types import database as unit_db
from pulp.server.db.model.repository import Repo, RepoDistributor, RepoImporter
from pulp.server.db.model.repository import RepoContentUnit
from pulp.server.db.model.consumer import Consumer, Bind
from pulp.server.exceptions import MissingResource
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
from pulp_node.handlers.strategies import Mirror
from pulp_node.importers.download import Batch
from pulp.common.download.downloaders.curl import HTTPSCurlDownloader
from pulp.common.download.config import DownloaderConfig
from pulp_node import constants


FAKE_DISTRIBUTOR = 'test_distributor'


class Repository(object):

    def __init__(self, id):
        self.id = id


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


class PluginTestBase(WebTest):

    REPO_ID = 'test-repo'
    UNIT_TYPE_ID = 'rpm'
    UNIT_ID = 'test_unit_%d'
    UNIT_METADATA = {'A':'a','B':'b', 'N': 0}
    TYPEDEF_ID = UNIT_TYPE_ID
    NUM_UNITS = 3

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
        units = []
        for n in range(0, self.NUM_UNITS):
            unit_id = self.UNIT_ID % n
            unit = dict(self.UNIT_METADATA)
            unit['N'] = n
            # add unit file
            storage_dir = pulp_conf.get('server', 'storage_dir')
            storage_path = \
                os.path.join(storage_dir, 'content',
                    '.'.join((unit_id, self.UNIT_TYPE_ID)))
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


class TestDistributor(PluginTestBase):

    def test_payload(self):
        # Setup
        self.populate()
        pulp_conf.set('server', 'storage_dir', self.parentfs)
        # Test
        dist = NodesHttpDistributor()
        repo = Repository(self.REPO_ID)
        payload = dist.create_consumer_payload(repo, self.dist_conf(), {})
        # Verify
        # TODO: NEEDED

    def test_payload_with_ssl(self):
        # Setup
        self.populate()
        pulp_conf.set('server', 'storage_dir', self.parentfs)
        # Test
        dist = NodesHttpDistributor()
        repo = Repository(self.REPO_ID)
        payload = dist.create_consumer_payload(repo, self.dist_conf_with_ssl(), {})
        # Verify
        # TODO: NEEDED

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
        units = list(manifest.read(url, downloader))
        self.assertEqual(len(units), self.NUM_UNITS)
        for n in range(0, self.NUM_UNITS):
            unit = units[n]
            created = self.units[n]
            for p, v in unit['metadata'].items():
                if p.startswith('_'):
                    continue
                self.assertEqual(created[p], v)


class ImporterTest(PluginTestBase):

    def test_import(self):
        # Setup
        self.populate()
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
        importer.sync_repo(repo, conduit, cfg)
        # Verify
        units = conduit.get_units()
        self.assertEquals(len(units), self.NUM_UNITS)


class TestStrategy:

    def __init__(self, tester, **cleaning_options):
        self.tester = tester
        self.cleaning_options = cleaning_options

    def __call__(self, progress):
        self.tester.clean(**self.cleaning_options)
        return Mirror(progress)


class BadBatch(Batch):

    def add(self, url, unit):
        n = random.random()
        Batch.add(self, 'http:/NOWHERE/FAIL_ME_%d' % n, unit)


class TestAgentPlugin(PluginTestBase):

    PULP_ID = 'child'

    def populate(self, strategy=constants.DEFAULT_STRATEGY, ssl=False):
        PluginTestBase.populate(self)
        # register child
        manager = managers.consumer_manager()
        manager.register(self.PULP_ID, notes={constants.STRATEGY_NOTE_KEY: strategy})
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

    def clean(self, just_units=False, purge_plugins=False):
        RepoContentUnit.get_collection().remove()
        unit_db.clean()
        if just_units:
            return
        Bind.get_collection().remove()
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        RepoImporter.get_collection().remove()
        if purge_plugins:
            plugin_api._MANAGER.importers.plugins = {}
            plugin_api._MANAGER.distributors.plugins = {}

    def verify(self, num_units=PluginTestBase.NUM_UNITS):
        # repository
        manager = managers.repo_query_manager()
        manager.get_repository(self.REPO_ID)
        # importer
        manager = managers.repo_importer_manager()
        importer = manager.get_importer(self.REPO_ID)
        manifest_url = importer['config'][constants.MANIFEST_URL_KEYWORD]
        self.assertTrue(manifest_url.endswith('%s/manifest.json.gz' % self.REPO_ID))
        # distributor
        manager = managers.repo_distributor_manager()
        manager.get_distributor(self.REPO_ID, FAKE_DISTRIBUTOR)
        self.assertRaises(MissingResource, manager.get_distributor, self.REPO_ID, constants.HTTP_DISTRIBUTOR)
        # check units
        manager = managers.repo_unit_association_query_manager()
        units = manager.get_units(self.REPO_ID)
        units = dict([(u['metadata']['N'], u) for u in units])
        self.assertEqual(len(units), num_units)
        for n in range(0, num_units):
            unit = units[n]
            unit_id = self.UNIT_ID % n
            metadata = unit['metadata']
            storage_path = metadata['_storage_path'].replace('//', '/')
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
        Test the end-to-end collaboration of:
          distributor(publish)->handler(update)->importer(sync)

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
        _report = []
        conn = PulpConnection(None, server_wrapper=self)
        binding = Bindings(conn)
        @patch('pulp_node.handlers.strategies.Child.binding', binding)
        @patch('pulp_node.handlers.strategies.Parent.binding', binding)
        @patch('pulp_node.handlers.handler.find_strategy', return_value=TestStrategy(self))
        def test_handler(*unused):
            # publish
            self.populate(constants.MIRROR_STRATEGY)
            pulp_conf.set('server', 'storage_dir', self.parentfs)
            dist = NodesHttpDistributor()
            repo = Repository(self.REPO_ID)
            conduit = RepoPublishConduit(self.REPO_ID, constants.HTTP_DISTRIBUTOR)
            dist.publish_repo(repo, conduit, self.dist_conf())
            units = [{'type_id':'node', 'unit_key':None}]
            pulp_conf.set('server', 'storage_dir', self.childfs)
            container = Container(self.parentfs)
            dispatcher = Dispatcher(container)
            container.handlers[CONTENT]['node'] = NodeHandler(self)
            container.handlers[CONTENT]['repository'] = RepositoryHandler(self)
            report = dispatcher.update(Conduit(), units, {})
            _report.append(report)
        test_handler()
        time.sleep(2)
        # Verify
        report = _report[0].details['node']
        self.assertTrue(report['succeeded'])
        merge_report = report['details']['merge_report']
        self.assertEqual(merge_report['added'], [self.REPO_ID])
        self.assertEqual(merge_report['merged'], [])
        self.assertEqual(merge_report['removed'], [])
        importer_report = report['details']['importer_reports'][self.REPO_ID]
        self.assertEqual(importer_report['added_count'], self.NUM_UNITS)
        self.assertEqual(importer_report['removed_count'], 0)
        details = importer_report['details']['report']
        self.assertEqual(len(details['add_failed']), 0)
        self.assertEqual(len(details['delete_failed']), 0)
        self.verify()

    @patch('pulp_node.handlers.strategies.Bundle.cn', return_value=PULP_ID)
    def test_handler_additive(self, *unused):
        """
        Test the end-to-end collaboration of:
          distributor(publish)->handler(update)->importer(sync)
        """
        _report = []
        conn = PulpConnection(None, server_wrapper=self)
        binding = Bindings(conn)
        @patch('pulp_node.handlers.strategies.Child.binding', binding)
        @patch('pulp_node.handlers.strategies.Parent.binding', binding)
        @patch('pulp_node.handlers.handler.find_strategy', return_value=TestStrategy(self))
        def test_handler(*unused):
            # publish
            self.populate(constants.ADDITIVE_STRATEGY)
            pulp_conf.set('server', 'storage_dir', self.parentfs)
            dist = NodesHttpDistributor()
            repo = Repository(self.REPO_ID)
            conduit = RepoPublishConduit(self.REPO_ID, constants.HTTP_DISTRIBUTOR)
            dist.publish_repo(repo, conduit, self.dist_conf())
            units = [{'type_id':'node', 'unit_key':None}]
            pulp_conf.set('server', 'storage_dir', self.childfs)
            container = Container(self.parentfs)
            dispatcher = Dispatcher(container)
            container.handlers[CONTENT]['node'] = NodeHandler(self)
            container.handlers[CONTENT]['repository'] = RepositoryHandler(self)
            report = dispatcher.update(Conduit(), units, {})
            _report.append(report)
        test_handler()
        time.sleep(2)
        # Verify
        report = _report[0].details['node']
        self.assertTrue(report['succeeded'])
        merge_report = report['details']['merge_report']
        self.assertEqual(merge_report['added'], [self.REPO_ID])
        self.assertEqual(merge_report['merged'], [])
        self.assertEqual(merge_report['removed'], [])
        importer_report = report['details']['importer_reports'][self.REPO_ID]
        self.assertEqual(importer_report['added_count'], self.NUM_UNITS)
        self.assertEqual(importer_report['removed_count'], 0)
        details = importer_report['details']['report']
        self.assertEqual(len(details['add_failed']), 0)
        self.assertEqual(len(details['delete_failed']), 0)
        self.verify()

    @patch('pulp_node.handlers.strategies.Bundle.cn', return_value=PULP_ID)
    def test_handler_merge(self, unused):
        """
        Test the end-to-end collaboration of:
          distributor(publish)->handler(update)->importer(sync)
        This test does NOT clean so nodes will merge.
        :see: test_handler for directory tree details.
        """
        _report = []
        conn = PulpConnection(None, server_wrapper=self)
        binding = Bindings(conn)
        @patch('pulp_node.handlers.strategies.Child.binding', binding)
        @patch('pulp_node.handlers.strategies.Parent.binding', binding)
        @patch('pulp_node.handlers.handler.find_strategy', return_value=TestStrategy(self, just_units=True))
        def test_handler(*unused):
            # publish
            self.populate(constants.MIRROR_STRATEGY, ssl=True)
            pulp_conf.set('server', 'storage_dir', self.parentfs)
            dist = NodesHttpDistributor()
            repo = Repository(self.REPO_ID)
            conduit = RepoPublishConduit(self.REPO_ID, constants.HTTP_DISTRIBUTOR)
            dist.publish_repo(repo, conduit, self.dist_conf())
            units = []
            handler = NodeHandler(self)
            pulp_conf.set('server', 'storage_dir', self.childfs)
            report = handler.update(Conduit(), units, {})
            _report.append(report)
        test_handler()
        time.sleep(2)
        # Verify
        report = _report[0]
        self.assertTrue(report.succeeded)
        merge_report = report.details['merge_report']
        self.assertEqual(merge_report['added'], [])
        self.assertEqual(merge_report['merged'], [self.REPO_ID])
        self.assertEqual(merge_report['removed'], [])
        importer_report = report.details['importer_reports'][self.REPO_ID]
        self.assertEqual(importer_report['added_count'], self.NUM_UNITS)
        self.assertEqual(importer_report['removed_count'], 0)
        details = importer_report['details']['report']
        self.assertTrue(details['succeeded'])
        self.assertEqual(len(details['add_failed']), 0)
        self.assertEqual(len(details['delete_failed']), 0)
        self.verify()
        path = os.path.join(self.childfs, 'parent', 'client.crt')
        self.assertTrue(os.path.exists(path))

    @patch('pulp_node.handlers.strategies.Bundle.cn', return_value=PULP_ID)
    def test_handler_unit_errors(self, *unused):
        """
        Test the end-to-end collaboration of:
          distributor(publish)->handler(update)->importer(sync)
        :see: test_handler for directory tree details.
        """
        _report = []
        conn = PulpConnection(None, server_wrapper=self)
        binding = Bindings(conn)
        @patch('pulp_node.handlers.strategies.Child.binding', binding)
        @patch('pulp_node.handlers.strategies.Parent.binding', binding)
        @patch('pulp_node.importers.strategies.Batch', BadBatch)
        @patch('pulp_node.handlers.handler.find_strategy', return_value=TestStrategy(self))
        def test_handler(*unused):
            # publish
            self.populate(constants.ADDITIVE_STRATEGY)
            pulp_conf.set('server', 'storage_dir', self.parentfs)
            dist = NodesHttpDistributor()
            repo = Repository(self.REPO_ID)
            conduit = RepoPublishConduit(self.REPO_ID, constants.HTTP_DISTRIBUTOR)
            dist.publish_repo(repo, conduit, self.dist_conf())
            units = []
            handler = NodeHandler(self)
            pulp_conf.set('server', 'storage_dir', self.childfs)
            os.makedirs(os.path.join(self.childfs, 'content'))
            report = handler.update(Conduit(), units, {})
            _report.append(report)
        test_handler()
        time.sleep(2)
        # Verify
        report = _report[0]
        self.assertFalse(report.succeeded)
        merge_report = report.details['merge_report']
        self.assertEqual(merge_report['added'], [self.REPO_ID])
        self.assertEqual(merge_report['merged'], [])
        self.assertEqual(merge_report['removed'], [])
        importer_report = report.details['importer_reports'][self.REPO_ID]
        self.assertEqual(importer_report['added_count'], 0)
        self.assertEqual(importer_report['removed_count'], 0)
        details = importer_report['details']['report']
        self.assertFalse(details['succeeded'])
        self.assertEqual(len(details['add_failed']), 3)
        self.assertEqual(len(details['delete_failed']), 0)
        self.verify(0)


    @patch('pulp_node.handlers.strategies.Bundle.cn', return_value=PULP_ID)
    def test_handler_nothing_updated(self, *unused):
        """
        Test the end-to-end collaboration of:
          distributor(publish)->handler(update)->importer(sync)
        :see: test_handler for directory tree details.
        """
        _report = []
        conn = PulpConnection(None, server_wrapper=self)
        binding = Bindings(conn)
        @patch('pulp_node.handlers.strategies.Child.binding', binding)
        @patch('pulp_node.handlers.strategies.Parent.binding', binding)
        @patch('pulp_node.importers.strategies.Batch', BadBatch)
        def test_handler(*unused):
            # publish
            self.populate(constants.MIRROR_STRATEGY)
            pulp_conf.set('server', 'storage_dir', self.parentfs)
            dist = NodesHttpDistributor()
            repo = Repository(self.REPO_ID)
            conduit = RepoPublishConduit(self.REPO_ID, constants.HTTP_DISTRIBUTOR)
            dist.publish_repo(repo, conduit, self.dist_conf())
            units = []
            handler = NodeHandler(self)
            pulp_conf.set('server', 'storage_dir', self.childfs)
            os.makedirs(os.path.join(self.childfs, 'content'))
            report = handler.update(Conduit(), units, {})
            _report.append(report)
        test_handler()
        time.sleep(2)
        # Verify
        report = _report[0]
        self.assertTrue(report.succeeded)
        merge_report = report.details['merge_report']
        self.assertEqual(merge_report['added'], [])
        self.assertEqual(merge_report['merged'], [self.REPO_ID])
        self.assertEqual(merge_report['removed'], [])
        importer_report = report.details['importer_reports'][self.REPO_ID]
        self.assertEqual(importer_report['added_count'], 0)
        self.assertEqual(importer_report['removed_count'], 0)
        details = importer_report['details']['report']
        self.assertTrue(details['succeeded'])
        self.assertEqual(len(details['add_failed']), 0)
        self.assertEqual(len(details['delete_failed']), 0)


    @patch('pulp_node.handlers.strategies.Bundle.cn', return_value=PULP_ID)
    @patch('pulp_node.importers.strategies.Mirror._add_units', side_effect=Exception())
    def test_importer_exception(self, *unused):
        """
        Test the end-to-end collaboration of:
          distributor(publish)->handler(update)->importer(sync)
        :see: test_handler for directory tree details.
        """
        _report = []
        conn = PulpConnection(None, server_wrapper=self)
        binding = Bindings(conn)
        @patch('pulp_node.handlers.strategies.Child.binding', binding)
        @patch('pulp_node.handlers.strategies.Parent.binding', binding)
        @patch('pulp_node.handlers.handler.find_strategy', return_value=TestStrategy(self))
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
            handler = NodeHandler(self)
            pulp_conf.set('server', 'storage_dir', self.childfs)
            os.makedirs(os.path.join(self.childfs, 'content'))
            report = handler.update(Conduit(), units, {})
            _report.append(report)
        test_handler()
        time.sleep(2)
        # Verify
        report = _report[0]
        self.assertFalse(report.succeeded)
        errors = report.details['errors']
        self.assertEqual(len(errors), 1)
        merge_report = report.details['merge_report']
        self.assertEqual(merge_report['added'], [self.REPO_ID])
        self.assertEqual(merge_report['merged'], [])
        self.assertEqual(merge_report['removed'], [])
        importer_report = report.details['importer_reports'].get(self.REPO_ID)
        if importer_report:
            self.assertFalse(importer_report['succeeded'])
            exception = importer_report['exception']
            self.assertTrue(len(exception) > 0)
            self.verify(0)

    @patch('pulp_node.handlers.strategies.Bundle.cn', return_value=PULP_ID)
    def test_plugins_missing(self, *unused):
        """
        Test the end-to-end collaboration of:
          distributor(publish)->handler(update)->importer(sync)
        :see: test_handler for directory tree details.
        """
        _report = []
        conn = PulpConnection(None, server_wrapper=self)
        binding = Bindings(conn)
        @patch('pulp_node.handlers.strategies.Child.binding', binding)
        @patch('pulp_node.handlers.strategies.Parent.binding', binding)
        @patch('pulp_node.handlers.handler.find_strategy', return_value=TestStrategy(self, purge_plugins=True))
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
        time.sleep(2)
        # Verify
        report = _report[0]
        self.assertFalse(report.succeeded)
        errors = report.details['errors']
        self.assertEqual(len(errors), 1)
        merge_report = report.details['merge_report']
        self.assertEqual(merge_report['added'], [])
        self.assertEqual(merge_report['merged'], [])
        self.assertEqual(merge_report['removed'], [])
        importer_report = report.details['importer_reports'].get(self.REPO_ID)
        if importer_report:
            self.assertFalse(importer_report['succeeded'])
            exception = importer_report['exception']
            self.assertTrue(len(exception) > 0)
            self.verify(0)
