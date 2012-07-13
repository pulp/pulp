#!/usr/bin/python
#
# Copyright (c) 2011 Red Hat, Inc.
#
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

# Python
import mock

import mock_plugins
import base

from pulp.server.managers import factory
from pulp.server.db.model.consumer import Consumer, Bind, UnitProfile
from pulp.server.db.model.repository import Repo, RepoDistributor, RepoContentUnit
from pulp.server.managers.repo.unit_association import OWNER_TYPE_IMPORTER
from pulp.server.managers.repo.unit_association_query import Criteria
from pulp.plugins.types import database as typedb
from pulp.plugins.types.model import TypeDefinition
from pulp.plugins import loader as plugin_loader
from pulp.plugins.conduits.profiler import ProfilerConduit, ProfilerConduitException

# -- test cases ---------------------------------------------------------------

class BaseProfilerConduitTests(base.PulpServerTests):

    CONSUMER_ID = 'test-consumer'
    REPO_ID = 'test-repo'
    DISTRIBUTOR_ID = 'test-distributor'
    TYPE_1_DEF = TypeDefinition('type-1', 'Type 1', 'One', ['key-1'], [], [])
    TYPE_2_DEF = TypeDefinition('type-2', 'Type 2', 'Two', ['key-2'], [], [])
    PROFILE = { 'name':'zsh', 'version':'1.0'}
    UNIT_ID = 0

    def setUp(self):
        super(BaseProfilerConduitTests, self).setUp()
        Consumer.get_collection().remove()
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        Bind.get_collection().remove()
        RepoContentUnit.get_collection().remove()
        UnitProfile.get_collection().remove()
        plugin_loader._create_loader()
        typedb.update_database([self.TYPE_1_DEF, self.TYPE_2_DEF])
        mock_plugins.install()

    def tearDown(self):
        super(BaseProfilerConduitTests, self).tearDown()
        Consumer.get_collection().remove()
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        Bind.get_collection().remove()
        RepoContentUnit.get_collection().remove()
        UnitProfile.get_collection().remove()
        typedb.clean()
        factory.reset()

    def populate(self):
        self.populate_consumer()
        self.populate_repository()
        self.populate_bindings()
        self.populate_units('key-1', self.TYPE_1_DEF)
        self.populate_units('key-2', self.TYPE_2_DEF)
        self.populate_profile()

    def populate_consumer(self):
        manager = factory.consumer_manager()
        manager.register(self.CONSUMER_ID)

    def populate_repository(self):
        config = {'key1' : 'value1', 'key2' : None}
        manager = factory.repo_manager()
        repo = manager.create_repo(self.REPO_ID)
        manager = factory.repo_distributor_manager()
        manager.add_distributor(
            self.REPO_ID,
            'mock-distributor',
            config,
            True,
            distributor_id=self.DISTRIBUTOR_ID)

    def populate_bindings(self):
        manager = factory.consumer_bind_manager()
        manager.bind(
            self.CONSUMER_ID,
            self.REPO_ID,
            self.DISTRIBUTOR_ID)

    def populate_units(self, key, typedef):
        for i in range(1,10):
            unit_id = 'unit-%s' % self.UNIT_ID
            md = {key:str(i)}
            manager = factory.content_manager()
            manager.add_content_unit(typedef.id, unit_id, md)
            manager = factory.repo_unit_association_manager()
            manager.associate_unit_by_id(
                self.REPO_ID,
                typedef.id,
                unit_id,
                OWNER_TYPE_IMPORTER,
                'test-importer')
            self.UNIT_ID += 1

    def populate_profile(self):
        manager = factory.consumer_profile_manager()
        manager.update(self.CONSUMER_ID, self.TYPE_1_DEF.id, self.PROFILE)

    def test_get_bindings(self):
        # Setup
        self.populate()
        # Test
        conduit = ProfilerConduit()
        binds = conduit.get_bindings(self.CONSUMER_ID)
        # Verify
        self.assertEquals(1, len(binds))
        self.assertTrue(binds[0], self.REPO_ID)

    def test_get_units(self):
        # Setup
        self.populate()
        # Test
        conduit = ProfilerConduit()
        criteria = Criteria(type_ids=[self.TYPE_1_DEF.id])
        units = conduit.get_units(self.REPO_ID, criteria)
        # Verify
        self.assertEquals(len(units), 9)
