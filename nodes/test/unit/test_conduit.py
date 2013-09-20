# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from mock import Mock
from base import ServerTests
from operator import itemgetter

from pulp.plugins.loader import api as plugin_api
from pulp.server.managers import factory as managers
from pulp.plugins.types import database as unit_db
from pulp.server.db.model.repository import Repo
from pulp.server.db.model.repository import RepoContentUnit
from pulp.server.db.model.content import ContentType

from pulp_node import constants
from pulp_node.importers.http.importer import NodesHttpImporter
from pulp_node.conduit import NodesConduit


# --- constants ---------------------------------------------------------------


REPO_ID = 'repo_a'

TYPE_A = 'A'
TYPE_B = 'B'
TYPE_C = 'C'
TYPE_D = 'D'

ALL_TYPES = (TYPE_A, TYPE_B, TYPE_C, TYPE_D)

UNIT_METADATA = {'A': 0, 'B': 1, 'C': 2, 'N': 0}


# --- utils -------------------------------------------------------------------


def create_unit_id(type_id, n):
    return '%s_%.4d' % (type_id, n)


def create_storage_path(unit_id):
    return 'content/%s.unit' % unit_id


def add_units(num_units=10):
    units = []
    n = 0
    for type_id in ALL_TYPES:
        for x in range(0, num_units):
            unit_id = create_unit_id(type_id, n)
            unit = dict(UNIT_METADATA)
            unit['N'] = n
            unit['_storage_path'] = create_storage_path(unit_id)
            manager = managers.content_manager()
            manager.add_content_unit(type_id, unit_id, unit)
            manager = managers.repo_unit_association_manager()
            # associate unit
            manager.associate_unit_by_id(
                REPO_ID,
                type_id,
                unit_id,
                RepoContentUnit.OWNER_TYPE_IMPORTER,
                constants.HTTP_IMPORTER)
            units.append(unit)
            n += 1
    return units


def populate(num_units):
    manager = managers.repo_manager()
    manager.create_repo(REPO_ID)
    return add_units(num_units)


# --- test cases --------------------------------------------------------------


class QueryTests(ServerTests):

    def setUp(self):
        super(QueryTests, self).setUp()
        Repo.get_collection().remove()
        RepoContentUnit.get_collection().remove()
        unit_db.clean()
        self.define_plugins()
        plugin_api._create_manager()
        plugin_api._MANAGER.importers.add_plugin(constants.HTTP_IMPORTER, NodesHttpImporter, {})

    def tearDown(self):
        super(QueryTests, self).tearDown()
        Repo.get_collection().remove()
        RepoContentUnit.get_collection().remove()
        unit_db.clean()

    def define_plugins(self):
        collection = ContentType.get_collection()
        for type_id in ALL_TYPES:
            collection.save(dict(id=type_id, unit_key=UNIT_METADATA.keys()), safe=True)

    def test_query(self):
        num_units = 5
        units_created = populate(num_units)
        conduit = NodesConduit()
        units = conduit.get_units(REPO_ID)
        self.assertEqual(len(units), len(units_created))
        unit_list = list(units)
        n = 0
        for u in sorted(unit_list, key=itemgetter('unit_id')):
            unit_id = u['unit_id']
            type_id = u['type_id']
            self.assertTrue(type_id in ALL_TYPES)
            self.assertEqual(create_unit_id(type_id, n), unit_id)
            unit_key = u['unit_key']
            self.assertEqual(unit_key['N'], n)
            self.assertEqual(u['storage_path'], create_storage_path(unit_id))
            n += 1