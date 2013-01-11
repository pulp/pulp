# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
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
import re
from mock import Mock, patch
from base import WebTest

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/mocks")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../../platform/src/")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../plugins/importers/citrus_importer")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../plugins/distributors/citrus_distributor")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../handlers")

from distributor import CitrusDistributor
from importer import CitrusImporter
from citrus import RepositoryHandler

from pulp.plugins.loader import api as plugin_api
from pulp.plugins.types import database as unit_db
from pulp.server.db.model.repository import Repo, RepoDistributor, RepoImporter
from pulp.server.db.model.repository import RepoContentUnit
from pulp.server.db.model.consumer import Consumer, Bind
from pulp.plugins.conduits.repo_publish import RepoPublishConduit
from pulp.plugins.conduits.repo_sync import RepoSyncConduit
from pulp.server.managers import factory
from pulp.bindings.bindings import Bindings
from pulp.bindings.server import PulpConnection
from pulp.server.config import config as pulp_conf
from pulp.agent.lib.conduit import Conduit

CITRUS_IMPORTER = 'citrus_importer'
CITRUS_DISTRUBUTOR = 'citrus_distributor'

class Repository(object):

    def __init__(self, id):
        self.id = id


class TestPlugins(WebTest):

    REPO_ID = 'test-repo'
    UNIT_TYPE_ID = 'rpm'
    UNIT_ID = 'test_unit'
    UNIT_METADATA = {'A':'a','B':'b'}
    TYPEDEF_ID = UNIT_TYPE_ID

    @classmethod
    def tmpdir(cls, role):
        dir = tempfile.mkdtemp(dir=cls.TMP_ROOT, prefix=role)
        return dir

    def setUp(self):
        WebTest.setUp(self)
        self.upfs = self.tmpdir('upstream-')
        self.downfs = self.tmpdir('downstream-')
        Consumer.get_collection().remove()
        Bind.get_collection().remove()
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        RepoImporter.get_collection().remove()
        RepoContentUnit.get_collection().remove()
        unit_db.clean()
        plugin_api._create_manager()
        plugin_api._MANAGER.importers.add_plugin(CITRUS_IMPORTER, CitrusImporter, {})
        plugin_api._MANAGER.distributors.add_plugin(CITRUS_DISTRUBUTOR, CitrusDistributor, {})
        unit_db.type_definition = \
            Mock(return_value=dict(id=self.TYPEDEF_ID, unit_key=self.UNIT_METADATA))
        unit_db.type_units_unit_key = \
            Mock(return_value=['A', 'B'])

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
        manager = factory.repo_manager()
        manager.create_repo(self.REPO_ID)
        manager = factory.repo_distributor_manager()
        # add distrubutor
        manager.add_distributor(
            self.REPO_ID,
            CITRUS_DISTRUBUTOR,
            {},
            False,
            distributor_id=CITRUS_DISTRUBUTOR)
        manager = factory.content_manager()
        unit = dict(self.UNIT_METADATA)
        # add unit file
        storage_dir = pulp_conf.get('server', 'storage_dir')
        storage_path = \
            os.path.join(storage_dir, 'content',
                '.'.join((self.UNIT_ID, self.UNIT_TYPE_ID)))
        unit['_storage_path'] = storage_path
        fp = open(storage_path, 'w+')
        fp.write(self.UNIT_ID)
        fp.close()
        # add unit
        manager.add_content_unit(
            self.UNIT_TYPE_ID,
            self.UNIT_ID,
            unit)
        manager = factory.repo_unit_association_manager()
        # associate unit
        manager.associate_unit_by_id(
            self.REPO_ID,
            self.UNIT_TYPE_ID,
            self.UNIT_ID,
            RepoContentUnit.OWNER_TYPE_IMPORTER,
            CITRUS_IMPORTER)


class TestDistributor(TestPlugins):

    def test_payload(self):
        # Setup
        self.populate()
        pulp_conf.set('server', 'storage_dir', self.upfs)
        # Test
        dist = CitrusDistributor()
        repo = Repository(self.REPO_ID)
        payload = dist.create_consumer_payload(repo, {})
        # Verify
        print payload

    def test_publish(self):
        # Setup
        self.populate()
        pulp_conf.set('server', 'storage_dir', self.upfs)
        # Test
        dist = CitrusDistributor()
        repo = Repository(self.REPO_ID)
        cfg = dict(virtual_host=(self.upfs, self.upfs))
        conduit = RepoPublishConduit(self.REPO_ID, CITRUS_DISTRUBUTOR)
        dist.publish_repo(repo, conduit, cfg)
        # Verify
        # TODO: verify published


class ImporterTest(TestPlugins):

    def test_import(self):
        # Setup
        self.populate()
        pulp_conf.set('server', 'storage_dir', self.upfs)
        dist = CitrusDistributor()
        repo = Repository(self.REPO_ID)
        cfg = dict(virtual_host=(self.upfs, self.upfs))
        conduit = RepoPublishConduit(self.REPO_ID, CITRUS_DISTRUBUTOR)
        dist.publish_repo(repo, conduit, cfg)
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        RepoContentUnit.get_collection().remove()
        unit_db.clean()
        # Test
        importer = CitrusImporter()
        cfg = dict(
            base_url='file://',
            manifest_url=dist.publisher(repo, cfg).manifest_path())
        conduit = RepoSyncConduit(
            self.REPO_ID,
            CITRUS_IMPORTER,
            RepoContentUnit.OWNER_TYPE_IMPORTER,
            CITRUS_IMPORTER)
        importer.sync_repo(repo, conduit, cfg)
        # Verify
        units = conduit.get_units()
        self.assertEquals(len(units), 1)


class TestHandler(RepositoryHandler):

    def __init__(self, tester, cfg={}):
        self.tester = tester
        RepositoryHandler.__init__(self, cfg)

    def synchronize(self, progress, binds):
        self.tester.clean()
        return RepositoryHandler.synchronize(self, progress, binds)


class TestAgentPlugin(TestPlugins):

    PULP_ID = 'downstream'

    def populate(self):
        TestPlugins.populate(self)
        self.virtual_host = (self.upfs, self.upfs)
        # register downstream
        manager = factory.consumer_manager()
        manager.register(self.PULP_ID)
        manager = factory.repo_importer_manager()
        # add importer
        cfg = dict(manifest_url='http://apple.com')
        manager.set_importer(self.REPO_ID, CITRUS_IMPORTER, cfg)
        # add distrubutor
        manager = factory.repo_distributor_manager()
        cfg = dict(base_url='file:///', virtual_host=self.virtual_host)
        manager.add_distributor(
            self.REPO_ID,
            CITRUS_DISTRUBUTOR,
            cfg,
            False,
            CITRUS_DISTRUBUTOR)
        # bind
        manager = factory.consumer_bind_manager()
        manager.bind(self.PULP_ID, self.REPO_ID, CITRUS_DISTRUBUTOR)

    def clean(self):
        Bind.get_collection().remove()
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        RepoImporter.get_collection().remove()
        RepoContentUnit.get_collection().remove()
        unit_db.clean()

    @patch('citrus.Bundle.cn', return_value=PULP_ID)
    def test_handler(self, unused):
        """
        Test the end-to-end collaboration of:
          distributor(publish)->handler(update)->importer(sync)
        This produces a file structure of:
          storage    - The upstream unit storage.
          upstream   - The upstream publishing location
          downstream - The downstream unit storage
        For example:

            citrus/
            ├── downstream-2BUtUa
            │   ├── content
            │   │   └── test_unit.rpm
            │   └── working
            │       └── repos
            │           └── test-repo
            │               ├── distributors
            │               │   └── citrus_distributor
            │               └── importers
            │                   └── citrus_importer
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
                            │   └── citrus_distributor
                            └── importers
                                └── citrus_importer

        @param unused:
        @return:
        """
        conn = PulpConnection(None, server_wrapper=self)
        binding = Bindings(conn)
        @patch('citrus.Local.binding', binding)
        @patch('citrus.Remote.binding', binding)
        def test_handler(*unused):
            # publish
            self.populate()
            pulp_conf.set('server', 'storage_dir', self.upfs)
            dist = CitrusDistributor()
            repo = Repository(self.REPO_ID)
            cfg = dict(base_url='file://', virtual_host=self.virtual_host)
            conduit = RepoPublishConduit(self.REPO_ID, CITRUS_DISTRUBUTOR)
            dist.publish_repo(repo, conduit, cfg)
            units = []
            options = dict(all=True)
            handler = TestHandler(self)
            pulp_conf.set('server', 'storage_dir', self.downfs)
            handler.update(Conduit(), units, options)
        test_handler()
        time.sleep(2)
        # Validate
        upstream_files = os.listdir(os.path.join(self.upfs, 'content'))
        self.assertEqual(1, len(upstream_files))
        for file in upstream_files:
            path = os.path.join(os.path.join(self.downfs, 'content', file))
            self.assertTrue(os.path.exists(path))

    def clean_units(self):
        Bind.get_collection().remove()
        RepoContentUnit.get_collection().remove()

    @patch('citrus.Bundle.cn', return_value=PULP_ID)
    def test_handler_merge(self, unused):
        """
        Test the end-to-end collaboration of:
          distributor(publish)->handler(update)->importer(sync)
        This test does NOT clean so citrus will merge.
        @see: test_handler for directory tree details.
        @param unused:
        @return:
        """
        self.clean = self.clean_units
        conn = PulpConnection(None, server_wrapper=self)
        binding = Bindings(conn)
        @patch('citrus.Local.binding', binding)
        @patch('citrus.Remote.binding', binding)
        def test_handler(*unused):
            # publish
            self.populate()
            pulp_conf.set('server', 'storage_dir', self.upfs)
            dist = CitrusDistributor()
            repo = Repository(self.REPO_ID)
            cfg = dict(base_url='file://', virtual_host=self.virtual_host)
            conduit = RepoPublishConduit(self.REPO_ID, CITRUS_DISTRUBUTOR)
            dist.publish_repo(repo, conduit, cfg)
            units = []
            options = dict(all=True)
            handler = TestHandler(self)
            pulp_conf.set('server', 'storage_dir', self.downfs)
            handler.update(Conduit(), units, options)
        test_handler()
        time.sleep(2)
        # Validate
        upstream_files = os.listdir(os.path.join(self.upfs, 'content'))
        self.assertEqual(1, len(upstream_files))
        for file in upstream_files:
            path = os.path.join(os.path.join(self.downfs, 'content', file))
            self.assertTrue(os.path.exists(path))