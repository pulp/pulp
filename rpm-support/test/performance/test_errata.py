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

from rpm_support_base import PulpRPMTests
from rpm_errata_profiler.profiler import RPMErrataProfiler
from pulp.server.managers import factory as managers
from pulp.server.db.model.consumer import Consumer
from pulp.server.db.model.repository import Repo, RepoContentUnit
from pulp.server.db.model.criteria import Criteria
from pulp.plugins.types import database, parser
from pulp.plugins.types.model import TypeDescriptor
from pulp.plugins.loader import api as plugins


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
    'version': '1,0',
    'release': '1.fc16',
    'arch': 'noarch',
    'epoch': 0,
    'vendor': 'Test',
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
    'pkglist' : [PROFILE_TEMPLATE,],
    'rights' : '',
    'severity' : '',
    'solution' : '',
}

class TestErrataApplicability(PulpRPMTests):

    TYPE_ID = 'rpm'
    ERRATA_TYPE_ID = 'erratum'
    TYPES_PATH = '../../plugins/types/rpm_support.json'
    REPO_ID = 'repo_A'
    CONSUMER_ID = 'consumer_A'
    FILTER = {'id':{'$in':[CONSUMER_ID]}}
    SORT = [{'id':1}]
    CRITERIA = Criteria(filters=FILTER, sort=SORT)

    def setUp(self):
        PulpRPMTests.setUp(self)
        Consumer.get_collection().remove()
        Repo.get_collection().remove()
        self.init_types()
        plugins.initialize()
        plugins._MANAGER.profilers.add_plugin(
            'EP',
            RPMErrataProfiler,
            {},
            (self.ERRATA_TYPE_ID,))

    def tearDown(self):
        PulpRPMTests.tearDown(self)
        Consumer.get_collection().remove()
        Repo.get_collection().remove()
        database.clean()
        plugins.finalize()

    def init_types(self):
        database.clean()
        fp = open(self.TYPES_PATH)
        td = TypeDescriptor(os.path.basename(self.TYPES_PATH), fp.read())
        fp.close()
        definitions = parser.parse([td])
        database.update_database(definitions)

    def populate(self):
        manager = managers.repo_manager()
        manager.create_repo(self.REPO_ID)
        manager = managers.consumer_manager()
        manager.register(self.CONSUMER_ID)
        self.populate_profile()
        self.populate_units()
        self.associate_units()

    def populate_units(self):
        # RPMs
        collection = database.type_units_collection(self.TYPE_ID)
        for i in range(0, 10):
            unit = UNIT_TEMPLATE.copy()
            unit['name'] = 'unit_%d' % i
            collection.save(unit, safe=True)
        # ERRATA
        collection = database.type_units_collection(self.ERRATA_TYPE_ID)
        collection.save(ERRATA_TEMPLATE, safe=True)
        print 'populated'

    def populate_profile(self):
        manager = managers.consumer_profile_manager()
        profile = []
        for i in range(0, 10):
            p = PROFILE_TEMPLATE.copy()
            p['name'] = 'unit_%d' % i
            profile.append(p)
        manager.create(self.CONSUMER_ID, self.TYPE_ID, profile)

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
        collection = database.type_units_collection(self.TYPE_ID)
        for unit in collection.find():
            manager.associate_unit_by_id(
                self.REPO_ID,
                self.ERRATA_TYPE_ID,
                unit['_id'],
                RepoContentUnit.OWNER_TYPE_IMPORTER,
                'stuffed',
                False
            )

    def test_1(self):
        self.populate()
        manager = managers.consumer_applicability_manager()
        unit = {'type_id':'erratum', 'unit_key':{'id':'erratum_1'}}
        units = [unit,]
        manager.units_applicable(self.CRITERIA, units)