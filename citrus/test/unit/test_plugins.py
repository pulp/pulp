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
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../plugins/importers/citrus_http_importer")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../plugins/distributors/citrus_http_distributor")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../handlers")

from distributor import CitrusHttpDistributor
from importer import CitrusHttpImporter
from citrus import NodeHandler, RepositoryHandler

from pulp.plugins.loader import api as plugin_api
from pulp.plugins.types import database as unit_db
from pulp.server.db.model.repository import Repo, RepoDistributor, RepoImporter
from pulp.server.db.model.repository import RepoContentUnit
from pulp.server.db.model.consumer import Consumer, Bind
from pulp.plugins.conduits.repo_publish import RepoPublishConduit
from pulp.plugins.conduits.repo_sync import RepoSyncConduit
from pulp.server.managers import factory as managers
from pulp.bindings.bindings import Bindings
from pulp.bindings.server import PulpConnection
from pulp.server.config import config as pulp_conf
from pulp.agent.lib.conduit import Conduit
from pulp.agent.lib.container import CONTENT, Container
from pulp.agent.lib.dispatcher import Dispatcher
from pulp_citrus.manifest import Manifest
from pulp_citrus.handler.strategies import Mirror
from pulp_citrus.importer.download import Batch
from pulp.common.download import factory
from pulp.common.download.config import DownloaderConfig

CITRUS_IMPORTER = 'citrus_http_importer'
CITRUS_DISTRUBUTOR = 'citrus_http_distributor'

class Repository(object):

    def __init__(self, id):
        self.id = id


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
        self.upfs = self.tmpdir('upstream-')
        self.downfs = self.tmpdir('downstream-')
        self.alias = (self.upfs, self.upfs)
        Consumer.get_collection().remove()
        Bind.get_collection().remove()
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        RepoImporter.get_collection().remove()
        RepoContentUnit.get_collection().remove()
        unit_db.clean()
        plugin_api._create_manager()
        plugin_api._MANAGER.importers.add_plugin(CITRUS_IMPORTER, CitrusHttpImporter, {})
        plugin_api._MANAGER.distributors.add_plugin(CITRUS_DISTRUBUTOR, CitrusHttpDistributor, {})
        unit_db.type_definition = \
            Mock(return_value=dict(id=self.TYPEDEF_ID, unit_key=self.UNIT_METADATA))
        unit_db.type_units_unit_key = \
            Mock(return_value=['A', 'B', 'N'])

    def tearDown(self):
        WebTest.tearDown(self)
        shutil.rmtree(self.upfs)
        shutil.rmtree(self.downfs)
        Consumer.get_collection().remove()
        Bind.get_collection().remove()
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        RepoImporter.get_collection().remove()
        RepoContentUnit.get_collection().remove()
        unit_db.clean()

    def populate(self):
        # make content/ dir.
        os.makedirs(os.path.join(self.upfs, 'content'))
        pulp_conf.set('server', 'storage_dir', self.upfs)
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
                CITRUS_IMPORTER)
            units.append(unit)
        # CA
        self.units = units
        path = os.path.join(self.upfs, 'ca.crt')
        fp = open(path, 'w+')
        fp.write(self.CA_CERT)
        fp.close()
        # client cert
        path = os.path.join(self.upfs, 'local.crt')
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
                'local':os.path.join(self.upfs, 'local.crt'),
                'child':os.path.join(self.downfs, 'parent', 'client.crt')
            }
        }
        d = self.dist_conf()
        d['file']['ssl'] = ssl
        return d


class TestDistributor(PluginTestBase):

    def test_payload(self):
        # Setup
        self.populate()
        pulp_conf.set('server', 'storage_dir', self.upfs)
        # Test
        dist = CitrusHttpDistributor()
        repo = Repository(self.REPO_ID)
        payload = dist.create_consumer_payload(repo, self.dist_conf())
        # Verify
        # TODO: NEEDED

    def test_payload_with_ssl(self):
        # Setup
        self.populate()
        pulp_conf.set('server', 'storage_dir', self.upfs)
        # Test
        dist = CitrusHttpDistributor()
        repo = Repository(self.REPO_ID)
        payload = dist.create_consumer_payload(repo, self.dist_conf_with_ssl())
        # Verify
        # TODO: NEEDED

    def test_publish(self):
        # Setup
        self.populate()
        pulp_conf.set('server', 'storage_dir', self.upfs)
        # Test
        dist = CitrusHttpDistributor()
        repo = Repository(self.REPO_ID)
        conduit = RepoPublishConduit(self.REPO_ID, CITRUS_DISTRUBUTOR)
        dist.publish_repo(repo, conduit, self.dist_conf())
        # Verify
        conf = DownloaderConfig('http')
        downloader = factory.get_downloader(conf)
        manifest = Manifest()
        pub = dist.publisher(repo, self.dist_conf())
        url = '/'.join((pub.base_url, pub.manifest_path()))
        units = manifest.read(url, downloader)
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
        pulp_conf.set('server', 'storage_dir', self.upfs)
        dist = CitrusHttpDistributor()
        repo = Repository(self.REPO_ID)
        cfg = {
            'protocol':'file',
            'http':{'alias':self.alias},
            'https':{'alias':self.alias},
            'file':{'alias':self.alias},
        }
        conduit = RepoPublishConduit(self.REPO_ID, CITRUS_DISTRUBUTOR)
        dist.publish_repo(repo, conduit, cfg)
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        RepoContentUnit.get_collection().remove()
        unit_db.clean()
        # Test
        importer = CitrusHttpImporter()
        publisher = dist.publisher(repo, cfg)
        manifest_url = 'file://' + publisher.manifest_path()
        cfg = dict(manifest_url=manifest_url, strategy='mirror')
        conduit = RepoSyncConduit(
            self.REPO_ID,
            CITRUS_IMPORTER,
            RepoContentUnit.OWNER_TYPE_IMPORTER,
            CITRUS_IMPORTER)
        importer.sync_repo(repo, conduit, cfg)
        # Verify
        units = conduit.get_units()
        self.assertEquals(len(units), self.NUM_UNITS)


class TestStrategy:

    def __init__(self, tester):
        self.tester = tester

    def __call__(self, progress):
        self.tester.clean()
        return Mirror(progress)


class BadBatch(Batch):

    def add(self, url, unit):
        n = random.random()
        Batch.add(self, 'http:/NOWHERE/FAIL_ME_%d' % n, unit)


class TestAgentPlugin(PluginTestBase):

    PULP_ID = 'downstream'

    def populate(self, ssl=False):
        PluginTestBase.populate(self)
        # register downstream
        manager = managers.consumer_manager()
        manager.register(self.PULP_ID)
        manager = managers.repo_importer_manager()
        # add importer
        cfg = dict(manifest_url='http://apple.com', protocol='file')
        manager.set_importer(self.REPO_ID, CITRUS_IMPORTER, cfg)
        # add distributor
        if ssl:
            dist_conf = self.dist_conf_with_ssl()
        else:
            dist_conf = self.dist_conf()

        manager = managers.repo_distributor_manager()
        manager.add_distributor(
            self.REPO_ID,
            CITRUS_DISTRUBUTOR,
            dist_conf,
            False,
            CITRUS_DISTRUBUTOR)
        # bind
        manager = managers.consumer_bind_manager()
        manager.bind(self.PULP_ID, self.REPO_ID, CITRUS_DISTRUBUTOR)

    def clean(self):
        Bind.get_collection().remove()
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        RepoImporter.get_collection().remove()
        RepoContentUnit.get_collection().remove()
        unit_db.clean()

    def verify(self, num_units=PluginTestBase.NUM_UNITS):
        # repository
        manager = managers.repo_query_manager()
        manager.get_repository(self.REPO_ID)
        # importer
        manager = managers.repo_importer_manager()
        importer = manager.get_importer(self.REPO_ID)
        manifest_url = importer['config']['manifest_url']
        self.assertTrue(manifest_url.endswith('%s/units.json.gz' % self.REPO_ID))
        # distributor
        manager = managers.repo_distributor_manager()
        distributor = manager.get_distributor(self.REPO_ID, CITRUS_DISTRUBUTOR)
        protocol = distributor['config']['protocol']
        self.assertEqual(protocol, 'file')
        alias = distributor['config'][protocol]['alias']
        self.assertEqual(alias[0], self.upfs)
        self.assertEqual(alias[1], self.upfs)
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
            self.assertEqual(unit['owner_id'], CITRUS_IMPORTER)
            file = '.'.join((unit_id, self.UNIT_TYPE_ID))
            self.assertEqual(storage_path, os.path.join(self.downfs, 'content', file))
            self.assertTrue(os.path.exists(storage_path))
            fp = open(storage_path)
            content = fp.read()
            fp.close()
            self.assertEqual(content, unit_id)

    @patch('pulp_citrus.handler.strategies.Bundle.cn', return_value=PULP_ID)
    def test_handler_mirror(self, *unused):
        """
        Test the end-to-end collaboration of:
          distributor(publish)->handler(update)->importer(sync)

        File system tree (example):

            citrus/
            ├── downstream-2BUtUa
            │   ├── content
            │   │   └── test_unit.rpm
            │   └── working
            │       └── repos
            │           └── test-repo
            │               ├── distributors
            │               │   └── citrus_http_distributor
            │               └── importers
            │                   └── citrus_http_importer
            ├── storage
            └── upstream-SgASM7
                ├── content
                │   └── test_unit.rpm
                ├── test-repo
                │   ├── content
                │   │   └── 3ae69ea97c -> /tmp/pulp/citrus/upstream-SgASM7/content/test_unit.rpm
                │   └── units.json
                └── working
                    └── repos
                        └── test-repo
                            ├── distributors
                            │   └── citrus_http_distributor
                            └── importers
                                └── citrus_http_importer

        """
        _report = []
        conn = PulpConnection(None, server_wrapper=self)
        binding = Bindings(conn)
        @patch('pulp_citrus.handler.strategies.Local.binding', binding)
        @patch('pulp_citrus.handler.strategies.Remote.binding', binding)
        @patch('citrus.find_strategy', return_value=TestStrategy(self))
        def test_handler(*unused):
            # publish
            self.populate()
            pulp_conf.set('server', 'storage_dir', self.upfs)
            dist = CitrusHttpDistributor()
            repo = Repository(self.REPO_ID)
            conduit = RepoPublishConduit(self.REPO_ID, CITRUS_DISTRUBUTOR)
            dist.publish_repo(repo, conduit, self.dist_conf())
            options = dict(all=True)
            units = [{'type_id':'node', 'unit_key':None}]
            pulp_conf.set('server', 'storage_dir', self.downfs)
            container = Container(self.upfs)
            dispatcher = Dispatcher(container)
            container.handlers[CONTENT]['node'] = NodeHandler(self)
            container.handlers[CONTENT]['repository'] = RepositoryHandler(self)
            report = dispatcher.update(Conduit(), units, options)
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

    @patch('pulp_citrus.handler.strategies.Bundle.cn', return_value=PULP_ID)
    def test_handler_additive(self, *unused):
        """
        Test the end-to-end collaboration of:
          distributor(publish)->handler(update)->importer(sync)
        """
        _report = []
        conn = PulpConnection(None, server_wrapper=self)
        binding = Bindings(conn)
        @patch('pulp_citrus.handler.strategies.Local.binding', binding)
        @patch('pulp_citrus.handler.strategies.Remote.binding', binding)
        @patch('citrus.find_strategy', return_value=TestStrategy(self))
        def test_handler(*unused):
            # publish
            self.populate()
            pulp_conf.set('server', 'storage_dir', self.upfs)
            dist = CitrusHttpDistributor()
            repo = Repository(self.REPO_ID)
            conduit = RepoPublishConduit(self.REPO_ID, CITRUS_DISTRUBUTOR)
            dist.publish_repo(repo, conduit, self.dist_conf())
            options = dict(strategy='additive')
            units = [{'type_id':'node', 'unit_key':None}]
            pulp_conf.set('server', 'storage_dir', self.downfs)
            container = Container(self.upfs)
            dispatcher = Dispatcher(container)
            container.handlers[CONTENT]['node'] = NodeHandler(self)
            container.handlers[CONTENT]['repository'] = RepositoryHandler(self)
            report = dispatcher.update(Conduit(), units, options)
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

    def clean_units(self):
        RepoContentUnit.get_collection().remove()
        unit_db.clean()

    @patch('pulp_citrus.handler.strategies.Bundle.cn', return_value=PULP_ID)
    def test_handler_merge(self, unused):
        """
        Test the end-to-end collaboration of:
          distributor(publish)->handler(update)->importer(sync)
        This test does NOT clean so citrus will merge.
        :see: test_handler for directory tree details.
        """
        _report = []
        self.clean = self.clean_units
        conn = PulpConnection(None, server_wrapper=self)
        binding = Bindings(conn)
        @patch('pulp_citrus.handler.strategies.Local.binding', binding)
        @patch('pulp_citrus.handler.strategies.Remote.binding', binding)
        @patch('citrus.find_strategy', return_value=TestStrategy(self))
        def test_handler(*unused):
            # publish
            self.populate(ssl=True)
            pulp_conf.set('server', 'storage_dir', self.upfs)
            dist = CitrusHttpDistributor()
            repo = Repository(self.REPO_ID)
            conduit = RepoPublishConduit(self.REPO_ID, CITRUS_DISTRUBUTOR)
            dist.publish_repo(repo, conduit, self.dist_conf())
            units = []
            options = {}
            handler = NodeHandler(self)
            pulp_conf.set('server', 'storage_dir', self.downfs)
            report = handler.update(Conduit(), units, options)
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
        path = os.path.join(self.downfs, 'parent', 'client.crt')
        self.assertTrue(os.path.exists(path))

    @patch('pulp_citrus.handler.strategies.Bundle.cn', return_value=PULP_ID)
    def test_handler_unit_errors(self, *unused):
        """
        Test the end-to-end collaboration of:
          distributor(publish)->handler(update)->importer(sync)
        :see: test_handler for directory tree details.
        """
        _report = []
        conn = PulpConnection(None, server_wrapper=self)
        binding = Bindings(conn)
        @patch('pulp_citrus.handler.strategies.Local.binding', binding)
        @patch('pulp_citrus.handler.strategies.Remote.binding', binding)
        @patch('pulp_citrus.importer.strategies.Batch', BadBatch)
        @patch('citrus.find_strategy', return_value=TestStrategy(self))
        def test_handler(*unused):
            # publish
            self.populate()
            pulp_conf.set('server', 'storage_dir', self.upfs)
            dist = CitrusHttpDistributor()
            repo = Repository(self.REPO_ID)
            conduit = RepoPublishConduit(self.REPO_ID, CITRUS_DISTRUBUTOR)
            dist.publish_repo(repo, conduit, self.dist_conf())
            units = []
            options = {}
            handler = NodeHandler(self)
            pulp_conf.set('server', 'storage_dir', self.downfs)
            os.makedirs(os.path.join(self.downfs, 'content'))
            report = handler.update(Conduit(), units, options)
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

    @patch('pulp_citrus.handler.strategies.Bundle.cn', return_value=PULP_ID)
    @patch('pulp_citrus.importer.strategies.Mirror._add_units', side_effect=Exception())
    def test_importer_exception(self, *unused):
        """
        Test the end-to-end collaboration of:
          distributor(publish)->handler(update)->importer(sync)
        :see: test_handler for directory tree details.
        """
        _report = []
        conn = PulpConnection(None, server_wrapper=self)
        binding = Bindings(conn)
        @patch('pulp_citrus.handler.strategies.Local.binding', binding)
        @patch('pulp_citrus.handler.strategies.Remote.binding', binding)
        @patch('citrus.find_strategy', return_value=TestStrategy(self))
        def test_handler(*unused):
            # publish
            self.populate()
            pulp_conf.set('server', 'storage_dir', self.upfs)
            dist = CitrusHttpDistributor()
            repo = Repository(self.REPO_ID)
            cfg = {
                'protocol':'file',
                'http':{'alias':self.alias},
                'https':{'alias':self.alias},
                'file':{'alias':self.alias},
            }
            conduit = RepoPublishConduit(self.REPO_ID, CITRUS_DISTRUBUTOR)
            dist.publish_repo(repo, conduit, cfg)
            units = []
            options = {}
            handler = NodeHandler(self)
            pulp_conf.set('server', 'storage_dir', self.downfs)
            os.makedirs(os.path.join(self.downfs, 'content'))
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
        self.assertEqual(merge_report['added'], [self.REPO_ID])
        self.assertEqual(merge_report['merged'], [])
        self.assertEqual(merge_report['removed'], [])
        importer_report = report.details['importer_reports'].get(self.REPO_ID)
        if importer_report:
            self.assertFalse(importer_report['succeeded'])
            exception = importer_report['exception']
            self.assertTrue(len(exception) > 0)
            self.verify(0)