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
from mock import Mock
from base import PluginTests

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/mocks")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../../platform/src/")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../plugins/importers/citrus_importer")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../plugins/distributors/citrus_distributor/")
print sys.path
from distributor import CitrusDistributor
from importer import CitrusImporter

import mock_plugins
from pulp.plugins.loader import api as plugin_api
from pulp.plugins.types import database as unit_db
from pulp.server.db.model.repository import Repo, RepoDistributor
from pulp.server.db.model.repository import RepoContentUnit
from pulp.plugins.conduits.repo_publish import RepoPublishConduit
from pulp.plugins.conduits.repo_sync import RepoSyncConduit
from pulp.server.exceptions import MissingResource
from pulp.server.managers import factory

CITRUS_IMPORTER = 'citrus_importer'
CITRUS_DISTRUBUTOR = 'citrus_distributor'


class Repository(object):
    
    def __init__(self, id):
        self.id = id


class TestPlugins(PluginTests):
    
    REPO_ID = 'test-repo'
    DISTRIBUTOR_ID = 'test-distributor'
    UNIT_TYPE_ID = 'rpm'
    UNIT_ID = 'test_unit'
    UNIT_METADATA = {'A':'a','B':'b'}
    TYPEDEF_ID = UNIT_TYPE_ID
    
    def setUp(self):
        PluginTests.setUp(self)
        self.tmpdir = tempfile.mkdtemp()
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        RepoContentUnit.get_collection().remove()
        unit_db.clean()
        plugin_api._create_manager()
        mock_plugins.install()
        unit_db.type_definition = \
            Mock(return_value=dict(id=self.TYPEDEF_ID, unit_key=['A', 'B']))
        unit_db.type_units_unit_key = \
            Mock(return_value=['A', 'B'])
        
    def shutDown(self):
        PluginTests.shutDown(self)
        shutil.rmtree(self.tmpdir)
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        RepoContentUnit.get_collection().remove()
        unit_db.clean()
    
    def populate(self):
        config = {'key1' : 'value1', 'key2' : None}
        # create repo
        manager = factory.repo_manager()
        repo = manager.create_repo(self.REPO_ID)
        manager = factory.repo_distributor_manager()
        # add distrubutor
        manager.add_distributor(
            self.REPO_ID,
            'mock-distributor',
            config,
            True,
            distributor_id=self.DISTRIBUTOR_ID)
        manager = factory.content_manager()
        unit = dict(self.UNIT_METADATA)
        # add unit file
        storage_path = \
            os.path.join(self.tmpdir, 
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
            self.DISTRIBUTOR_ID)


class TestDistributor(TestPlugins):

    def test_payload(self):
        # Setup
        self.populate()
        # Test
        dist = CitrusDistributor()
        repo = Repository(self.REPO_ID)
        payload = dist.create_consumer_payload(repo, {})
        # Verify
        print payload
        
    def test_publish(self):
        # Setup
        self.populate()
        # Test
        dist = CitrusDistributor()
        repo = Repository(self.REPO_ID)
        cfg = dict(publishdir=self.tmpdir)
        conduit = RepoPublishConduit(self.REPO_ID, CITRUS_DISTRUBUTOR)
        dist.publish_repo(repo, conduit, cfg)
        # Verify
        # TODO: verify published
        
        
class ImporterTest(TestPlugins):
        
    def test_import(self):
        # Setup
        self.populate()
        dist = CitrusDistributor()
        repo = Repository(self.REPO_ID)
        cfg = dict(publishdir=self.tmpdir)
        conduit = RepoPublishConduit(self.REPO_ID, CITRUS_DISTRUBUTOR)
        dist.publish_repo(repo, conduit, cfg)
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        RepoContentUnit.get_collection().remove()
        unit_db.clean()
        # Test
        importer = CitrusImporter()
        cfg = dict(baseurl=self.tmpdir)
        conduit = RepoSyncConduit(
            self.REPO_ID,
            CITRUS_IMPORTER,
            RepoContentUnit.OWNER_TYPE_IMPORTER,
            self.DISTRIBUTOR_ID)
        importer.sync_repo(repo, conduit, cfg)
        # Verify
        units = conduit.get_units()
        self.assertEquals(len(units), 1)