# Copyright (c) 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../../platform/src/")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../../rpm_support/src/")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../plugins/profilers/")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../unit/")

from mock import Mock
from rpm_support_base import PulpRPMTests
from rpm_errata_profiler.profiler import RPMErrataProfiler
from pulp.server.managers import factory as managers
from pulp.server.db.model.consumer import Consumer
from pulp.server.db.model.repository import Repo, RepoContentUnit, RepoDistributor
from pulp.server.db.model.criteria import Criteria
from pulp.plugins.types import database, parser
from pulp.plugins.types.model import TypeDescriptor
from pulp.plugins.loader import api as plugins
from gofer.metrics import Timer


UNIT_TEMPLATE = {
    "name": "unit_1",
    "description": "My Description.",
    "version": "1.0",
    "release": "1.fc16",
    "epoch": "0",
    "arch": "noarch",
    "license": "LGPLv2",
    "vendor": "",
    "requires": [],
    "provides": [],
    "checksum": "xxx",
    "filename": "Name-1.0-1.fc16.noarch.rpm",
    "buildhost": "localhost",
    "checksumtype": "sha256",
    "relativepath": "packages/Name-1.0-1.fc16.noarch.rpm",
    "_content_type_id": "rpm",
}

PROFILE_TEMPLATE = {
    'name': 'unit_1',
    'version': '1.0',
    'release': '1.fc16',
    'arch': 'noarch',
    'epoch': 0,
    'vendor': 'Test',
}

ERRATA_PACKAGE = {
    'name': 'unit_1',
    'version': '1.1',
    'release': '1.fc16',
    'arch': 'noarch',
    'epoch': 0,
    }

ERRATA_TEMPLATE = {
    'id' : 'erratum_1',
    'title' : 'Title',
    'summary' : 'Enhances something',
    'description' : 'Description',
    'version' : '1',
    'release' : '1.fc16',
    'type' : 'enhancements',
    'status' : 'final',
    'updated' :'2012-7-25 00:00:00',
    'issued' : '2012-7-25 00:00:00',
    'pushcount' : 1,
    'from_str' : 'pulp-list@redhat.com',
    'reboot_suggested' : False,
    'references' : [],
    'pkglist' : [{'packages' : []}],
    'rights' : '',
    'severity' : '',
    'solution' : '',
}

TEST_UNIT = {'type_id':'erratum', 'unit_key':{'id':'erratum_1'}}


class FakeDistributor(Mock):

    ID = 'FAKE'
    TYPE = ID

    @classmethod
    def metadata(cls):
        return dict(id=cls.ID, display_name='', types=[cls.TYPE])

    def validate_config(self, *unused):
        return True


class TestEnv:

    def __init__(self):
        self.consumers = 10
        self.profile_units = 10
        self.repo_units = 10
        self.errata_packages = 10

    def __str__(self):
        return 'consumers:%d, profile_units:%d, repo_units:%d, errata_pkgs:%d' % \
               (self.consumers,
                self.profile_units,
                self.repo_units,
                self.errata_packages)


class TestErrataApplicability(PulpRPMTests):

    TYPE_ID = 'rpm'
    ERRATA_TYPE_ID = 'erratum'
    TYPES_PATH = '../../plugins/types/rpm_support.json'
    REPO_ID = 'repo_A'


    def setUp(self):
        PulpRPMTests.setUp(self)
        Consumer.get_collection().remove()
        Repo.get_collection().remove()
        RepoContentUnit.get_collection().remove()
        RepoDistributor.get_collection().remove()
        self.init_types()
        plugins.initialize()
        plugins._MANAGER.profilers.add_plugin(
            'ERRATA_PROFILER',
            RPMErrataProfiler,
            {},
            (self.ERRATA_TYPE_ID,))
        plugins._MANAGER.distributors.add_plugin(
            FakeDistributor.ID,
            FakeDistributor,
            {},
            (self.ERRATA_TYPE_ID,))

    def tearDown(self):
        PulpRPMTests.tearDown(self)
        Consumer.get_collection().remove()
        Repo.get_collection().remove()
        RepoContentUnit.get_collection().remove()
        RepoDistributor.get_collection().remove()
        database.clean()
        plugins.finalize()

    def init_types(self):
        database.clean()
        fp = open(self.TYPES_PATH)
        td = TypeDescriptor(os.path.basename(self.TYPES_PATH), fp.read())
        fp.close()
        definitions = parser.parse([td])
        database.update_database(definitions)

    def populate(self, env):
        print 'populating .....'
        manager = managers.repo_manager()
        manager.create_repo(self.REPO_ID)
        manager = managers.repo_distributor_manager()
        manager.add_distributor(
            self.REPO_ID,
            FakeDistributor.TYPE, {},
            False,
            FakeDistributor.ID)
        self.populate_consumers(env)
        self.populate_units(env)
        self.associate_units()
        print 'populated'

    def populate_consumers(self, env):
        for i in range(0, env.consumers):
            id = 'consumer_%d' % i
            manager = managers.consumer_manager()
            manager.register(id)
            manager = managers.consumer_bind_manager()
            manager.bind(id, self.REPO_ID, FakeDistributor.ID)
            self.populate_profile(id, env)

    def populate_profile(self, id, env):
        manager = managers.consumer_profile_manager()
        profile = []
        for i in range(0, env.profile_units):
            p = PROFILE_TEMPLATE.copy()
            p['name'] = 'unit_%d' % i
            profile.append(p)
        manager.create(id, self.TYPE_ID, profile)

    def populate_units(self, env):
        # RPMs
        collection = database.type_units_collection(self.TYPE_ID)
        for i in range(0, env.repo_units):
            unit = UNIT_TEMPLATE.copy()
            unit['name'] = 'unit_%d' % i
            unit['version'] = '1.1'
            collection.save(unit, safe=True)
        # ERRATA
        errata = ERRATA_TEMPLATE.copy()
        packages = []
        for i in range(0, env.errata_packages):
            p = ERRATA_PACKAGE.copy()
            p['name'] = 'unit_%d' % i
            packages.append(p)
        errata['pkglist'][0]['packages'] = packages
        collection = database.type_units_collection(self.ERRATA_TYPE_ID)
        collection.save(errata, safe=True)

    def associate_units(self):
        manager = managers.repo_unit_association_manager()
        # RPMs
        collection = database.type_units_collection(self.TYPE_ID)
        for unit in collection.find():
            manager.associate_unit_by_id(
                self.REPO_ID,
                self.TYPE_ID,
                unit['_id'],
                RepoContentUnit.OWNER_TYPE_IMPORTER,
                'stuffed',
                False
            )
            # ERRATA
        collection = database.type_units_collection(self.ERRATA_TYPE_ID)
        for unit in collection.find():
            manager.associate_unit_by_id(
                self.REPO_ID,
                self.ERRATA_TYPE_ID,
                unit['_id'],
                RepoContentUnit.OWNER_TYPE_IMPORTER,
                'stuffed',
                False
            )

    def criteria(self, n_ids=1):
        ids = []
        for i in range(0, n_ids):
            ids.append('consumer_%d' % i)
        filter = {'id':{'$in':ids}}
        sort = [{'id':1}]
        return Criteria(filters=filter, sort=sort)

    def test_A(self):
        env = TestEnv()
        self.populate(env)
        manager = managers.consumer_applicability_manager()
        units = [TEST_UNIT,]
        criteria = self.criteria()
        print 'Testing applicability ....'
        timer = Timer()
        timer.start()
        applicable = manager.units_applicable(criteria, units)
        timer.stop()
        print 'Finished: [%s] in: %s' % (env, timer)
        for id, report in applicable.items():
            self.assertTrue(report[0].applicable)

    def test_B(self):
        env = TestEnv()
        env.consumers = 2
        env.profile_units = 400
        env.repo_units = 5000
        env.errata_packages = 1
        self.populate(env)
        manager = managers.consumer_applicability_manager()
        units = [TEST_UNIT,]
        criteria = self.criteria()
        print 'Testing applicability ....'
        timer = Timer()
        timer.start()
        applicable = manager.units_applicable(criteria, units)
        timer.stop()
        print 'Finished: [%s] in: %s' % (env, timer)
        for id, report in applicable.items():
            self.assertTrue(report[0].applicable)

    def test_C(self):
        env = TestEnv()
        env.consumers = 200
        env.profile_units = 400
        env.repo_units = 5000
        env.errata_packages = 20
        self.populate(env)
        manager = managers.consumer_applicability_manager()
        units = [TEST_UNIT,]
        criteria = self.criteria()
        print 'Testing applicability ....'
        timer = Timer()
        timer.start()
        applicable = manager.units_applicable(criteria, units)
        timer.stop()
        print 'Finished: [%s] in: %s' % (env, timer)
        for id, report in applicable.items():
            self.assertTrue(report[0].applicable)

    def test_D(self):
        env = TestEnv()
        env.consumers = 2000
        env.profile_units = 400
        env.repo_units = 5000
        env.errata_packages = 20
        self.populate(env)
        manager = managers.consumer_applicability_manager()
        units = [TEST_UNIT,]
        criteria = self.criteria()
        print 'Testing applicability ....'
        timer = Timer()
        timer.start()
        applicable = manager.units_applicable(criteria, units)
        timer.stop()
        print 'Finished: [%s] in: %s' % (env, timer)
        for id, report in applicable.items():
            self.assertTrue(report[0].applicable)
