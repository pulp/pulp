# -*- coding: utf-8 -*-
# Copyright (c) 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from pymongo.objectid import ObjectId

from base_db_upgrade import BaseDbUpgradeTests
from pulp.server.upgrade.db import units
from pulp.server.upgrade.model import UpgradeStepReport


class InitializeContentTypesTests(BaseDbUpgradeTests):

    def test_initialize_content_types(self):
        # Test
        result = units._initialize_content_types(self.tmp_test_db.database)

        # Verify
        self.assertTrue(result)

        types_coll = self.tmp_test_db.database.content_types
        migrations_coll = self.tmp_test_db.database.migration_trackers

        # Verify the proper creation of these collections
        types_indexes = types_coll.index_information()
        self.assertTrue('id_-1' in types_indexes)
        self.assertEqual(types_indexes['id_-1']['unique'], True)

        migrations_indexes = migrations_coll.index_information()
        self.assertTrue('name_-1' in migrations_indexes)
        self.assertEqual(migrations_indexes['name_-1']['unique'], True)

        for type_def in units.TYPE_DEFS:
            unit_coll = getattr(self.tmp_test_db.database, units._units_collection_name(type_def['id']))
            indexes = unit_coll.index_information()
            indexes.pop('_id_') # remove the default one, the other is named weird and this is easier
            self.assertEqual(len(indexes), 1) # sanity check, should be the unit_key
            index = indexes[indexes.keys()[0]]

            self.assertEqual(index['unique'], True)

            sorted_index_tuples = sorted(index['key'], key=lambda x : x[0])
            sorted_unit_key_names = sorted(type_def['unit_key'])

            for ituple, key_name in zip(sorted_index_tuples, sorted_unit_key_names):
                self.assertEqual(ituple[0], key_name)
                self.assertEqual(ituple[1], 1)

        # Verify the data itself
        for type_def in units.TYPE_DEFS:
            found_type = types_coll.find_one({'id' : type_def['id']})
            self.assertTrue(found_type is not None)
            self.assertTrue(isinstance(found_type['_id'], ObjectId))
            self.assertEqual(found_type['id'], type_def['id'])
            self.assertEqual(found_type['display_name'], type_def['display_name'])
            self.assertEqual(found_type['description'], type_def['description'])
            self.assertEqual(found_type['unit_key'], type_def['unit_key'])
            self.assertEqual(found_type['search_indexes'], type_def['search_indexes'])
            self.assertEqual(found_type['referenced_types'], type_def['referenced_types'])

            found_tracker = migrations_coll.find_one({'name' : type_def['display_name']})
            self.assertTrue(found_tracker is not None)
            self.assertTrue(isinstance(found_tracker['_id'], ObjectId))
            self.assertEqual(found_tracker['name'], type_def['display_name'])
            self.assertEqual(found_tracker['version'], 0)

    def test_initialize_content_types_idempotency(self):
        # Test
        units._initialize_content_types(self.tmp_test_db.database)
        result = units._initialize_content_types(self.tmp_test_db.database)

        # Verify
        self.assertTrue(result)

        types_coll = self.tmp_test_db.database.content_types
        all_types = types_coll.find()
        self.assertEqual(all_types.count(), len(units.TYPE_DEFS))


class PackagesUpgradeTests(BaseDbUpgradeTests):

    def setUp(self):
        super(PackagesUpgradeTests, self).setUp()

        # The unique keys need to be set for these tests
        units._initialize_content_types(self.tmp_test_db.database)

    def test_rpms(self):
        # Test
        report = UpgradeStepReport()
        result = units._rpms(self.v1_test_db.database, self.tmp_test_db.database, report)

        # Verify
        self.assertTrue(result)

        v1_rpms = self.v1_test_db.database.packages.find({'arch' : {'$ne' : 'src'}}).sort('filename')
        self._assert_upgrade(v1_rpms)

    def test_rpms_idempotency(self):
        # Test
        report = UpgradeStepReport()
        units._rpms(self.v1_test_db.database, self.tmp_test_db.database, report)
        result = units._rpms(self.v1_test_db.database, self.tmp_test_db.database, report)

        # Verify
        self.assertTrue(result)

        v1_rpms = self.v1_test_db.database.packages.find({'arch' : {'$ne' : 'src'}})
        v2_rpms = self.tmp_test_db.database.units_rpm.find()
        self.assertEqual(v1_rpms.count(), v2_rpms.count())

    def test_srpms(self):
        # Test
        report = UpgradeStepReport()
        result = units._srpms(self.v1_test_db.database, self.tmp_test_db.database, report)

        # Verify
        self.assertTrue(result)

        v1_srpms = self.v1_test_db.database.packages.find({'arch' : 'src'}).sort('filename')
        self._assert_upgrade(v1_srpms)

    def test_srpms_idempotency(self):
        # Test
        report = UpgradeStepReport()
        units._srpms(self.v1_test_db.database, self.tmp_test_db.database, report)
        result = units._srpms(self.v1_test_db.database, self.tmp_test_db.database, report)

        # Verify
        self.assertTrue(result)

        v1_rpms = self.v1_test_db.database.packages.find({'arch' : 'src'})
        v2_rpms = self.tmp_test_db.database.units_rpm.find()
        self.assertEqual(v1_rpms.count(), v2_rpms.count())

    def _assert_upgrade(self, v1_packages):

        v2_rpms = self.tmp_test_db.database.units_rpm.find().sort('filename')
        self.assertEqual(v1_packages.count(), v2_rpms.count())

        for v1_rpm, v2_rpm in zip(v1_packages, v2_rpms):
            self.assertTrue(isinstance(v2_rpm['_id'], ObjectId))
            self.assertEqual(v2_rpm['_content_type_id'], 'rpm')
            expected_path = '/var/lib/pulp/content/rpm/%s/%s/%s/%s/%s/%s' % \
                            (v2_rpm['name'], v2_rpm['version'], v2_rpm['release'],
                             v2_rpm['arch'], v2_rpm['checksum'], v2_rpm['filename'])
            self.assertEqual(v2_rpm['_storage_path'], expected_path)

            self.assertEqual(v1_rpm['name'], v2_rpm['name'])
            self.assertEqual(v1_rpm['epoch'], v2_rpm['epoch'])
            self.assertEqual(v1_rpm['version'], v2_rpm['version'])
            self.assertEqual(v1_rpm['release'], v2_rpm['release'])
            self.assertEqual(v1_rpm['arch'], v2_rpm['arch'])
            self.assertEqual(v1_rpm['description'], v2_rpm['description'])
            self.assertEqual(v1_rpm['vendor'], v2_rpm['vendor'])
            self.assertEqual(v1_rpm['filename'], v2_rpm['filename'])
            self.assertEqual(v1_rpm['requires'], v2_rpm['requires'])
            self.assertEqual(v1_rpm['provides'], v2_rpm['provides'])
            self.assertEqual(v1_rpm['buildhost'], v2_rpm['buildhost'])
            self.assertEqual(v1_rpm['license'], v2_rpm['license'])

            self.assertEqual(v1_rpm['checksum'].keys()[0], v2_rpm['checksumtype'])
            self.assertEqual(v1_rpm['checksum'].values()[0], v2_rpm['checksum'])

            self.assertTrue('relativepath' not in v2_rpm) # not set in this script


class DistributionUpgradeTests(BaseDbUpgradeTests):

    def setUp(self):
        super(DistributionUpgradeTests, self).setUp()

        # The unique keys need to be set for these tests
        units._initialize_content_types(self.tmp_test_db.database)

    def test_upgrade(self):
        # Test
        report = UpgradeStepReport()
        result = units._distributions(self.v1_test_db.database, self.tmp_test_db.database, report)

        # Verify
        self.assertTrue(result)

        v1_distros = self.v1_test_db.database.distribution.find().sort('id')
        v2_distros = self.tmp_test_db.database.units_distribution.find().sort('id')
        self.assertEqual(v1_distros.count(), v2_distros.count())

        for v1_distro, v2_distro in zip(v1_distros, v2_distros):
            self.assertTrue(isinstance(v2_distro['_id'], ObjectId))
            self.assertEqual(v2_distro['_content_type_id'], 'distribution')
            expected_path = '/var/lib/pulp/content/distribution/%s' % v2_distro['id']
            self.assertEqual(v2_distro['_storage_path'], expected_path)

            self.assertEqual(v1_distro['id'], v2_distro['id'])
            self.assertEqual(v1_distro['arch'], v2_distro['arch'])
            self.assertEqual(v1_distro['version'], v2_distro['version'])
            self.assertEqual(v1_distro['variant'], v2_distro['variant'])
            self.assertEqual(v1_distro['family'], v2_distro['family'])
            self.assertEqual(v1_distro['files'], v2_distro['files'])

    def test_upgrade_idempotency(self):
        # Test
        report = UpgradeStepReport()
        units._distributions(self.v1_test_db.database, self.tmp_test_db.database, report)
        result = units._distributions(self.v1_test_db.database, self.tmp_test_db.database, report)

        # Verify
        self.assertTrue(result)

        v1_distros = self.v1_test_db.database.distribution.find()
        v2_distros = self.tmp_test_db.database.units_distribution.find()
        self.assertEqual(v1_distros.count(), v2_distros.count())
