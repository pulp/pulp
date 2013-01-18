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

import os

from pulp.server.compat import ObjectId

from base_db_upgrade import BaseDbUpgradeTests
from pulp.server.upgrade.db import units
from pulp.server.upgrade.model import UpgradeStepReport
from pulp.server.upgrade.utils import PrestoParser

DATA_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data')
V1_TEST_FILESYSTEM=os.path.join(DATA_DIR, 'filesystem/v1')
V1_REPOS_DIR = os.path.join(V1_TEST_FILESYSTEM, "var/lib/pulp/repos")


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

            total_index_count = len(type_def['search_indexes']) + 1 # 1 for unit key
            self.assertEqual(len(indexes), total_index_count)

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
        units._initialize_association_collection(self.tmp_test_db.database)

    def test_rpms(self):
        # Test
        report = UpgradeStepReport()
        result = units._rpms(self.v1_test_db.database, self.tmp_test_db.database, report)

        # Verify
        self.assertTrue(result)

        v1_rpms = self.v1_test_db.database.packages.find({'arch' : {'$ne' : 'src'}}).sort('filename')
        self._assert_upgrade(v1_rpms)
        self._assert_associations(self.tmp_test_db.database.units_rpm, 'rpm', {'arch' : {'$ne' : 'src'}})

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

        self._assert_associations(self.tmp_test_db.database.units_rpm, 'rpm', {'arch' : {'$ne' : 'src'}})

    def test_srpms(self):
        # Test
        report = UpgradeStepReport()
        result = units._srpms(self.v1_test_db.database, self.tmp_test_db.database, report)

        # Verify
        self.assertTrue(result)

        v1_srpms = self.v1_test_db.database.packages.find({'arch' : 'src'}).sort('filename')
        self._assert_upgrade(v1_srpms)
        self._assert_associations(self.tmp_test_db.database.units_srpm, 'srpm', {'arch' : 'src'})

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

        self._assert_associations(self.tmp_test_db.database.units_srpm, 'srpm', {'arch' : 'src'})

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

    def _assert_associations(self, v2_package_coll, package_type_id, v1_query_addition):

        v1_package_coll = self.v1_test_db.database.packages
        v2_ass_coll = self.tmp_test_db.database.repo_content_units

        v1_repos = self.v1_test_db.database.repos.find()
        for v1_repo in v1_repos:
            repo_id = v1_repo['id']
            repo_package_ids = v1_repo['packages']
            query = {'_id' : {'$in' : repo_package_ids}}
            if v1_query_addition:
                query.update(v1_query_addition)
            v1_packages = v1_package_coll.find(query)

            # Load up the IDs of all packages in v2 that should be referenced
            v2_package_ids = []
            for v1_package in v1_packages:
                unit_key_fields = ('name', 'epoch', 'version', 'release', 'arch',)
                query = dict([ (k, v1_package[k]) for k in unit_key_fields ])
                query['checksumtype'] = v1_package['checksum'].keys()[0]
                query['checksum'] = v1_package['checksum'].values()[0]
                v2_package = v2_package_coll.find_one(query, {'_id' : 1})
                self.assertTrue(v2_package is not None)
                v2_package_ids.append(v2_package['_id'])

            # Make sure there are associations for each
            query = {
                'repo_id' : repo_id,
                'unit_id' : {'$in' : v2_package_ids},
                'unit_type_id' : package_type_id,
            }
            associations = v2_ass_coll.find(query)

            # Sanity check that the right number were found
            self.assertEqual(v1_packages.count(), associations.count())

            for ass in associations:
                self.assertTrue(isinstance(ass['_id'], ObjectId))
                self.assertEqual(ass['repo_id'], repo_id)
                self.assertTrue(ass['unit_id'] in v2_package_ids)
                self.assertEqual(ass['unit_type_id'], package_type_id)
                self.assertEqual(ass['owner_type'], units.DEFAULT_OWNER_TYPE)
                self.assertEqual(ass['owner_id'], units.DEFAULT_OWNER_ID)
                self.assertEqual(ass['created'], units.DEFAULT_CREATED)
                self.assertEqual(ass['updated'], units.DEFAULT_UPDATED)

class DRPMUpgradeTests(BaseDbUpgradeTests):

    def setUp(self):
        super(DRPMUpgradeTests, self).setUp()
        new_repo = {
                'id' : 'test_drpm_repo',
                'content_types' : 'yum',
                'repomd_xml_path' : os.path.join(V1_REPOS_DIR,
                    'repos/pulp/pulp/demo_repos/test_drpm_repo/repodata/repomd.xml'),
                'relative_path' : 'repos/pulp/pulp/demo_repos/test_drpm_repo/',
            }
        if self.v1_test_db.database.repos.find_one({'id' : 'test_drpm_repo'}):
            self.v1_test_db.database.repos.remove({'id' : 'test_drpm_repo'})
        self.v1_test_db.database.repos.insert(new_repo, safe=True)

        # The unique keys need to be set for these tests
        units._initialize_content_types(self.tmp_test_db.database)

    def test_drpms(self):
        # Test
        report = UpgradeStepReport()
        result = units._drpms(self.v1_test_db.database, self.tmp_test_db.database, report)

        # Verify
        self.assertTrue(result)
        v1_drpms = []
        deltarpms = PrestoParser.get_deltas(self.v1_test_db.database.repos.find_one({'id' : 'test_drpm_repo'}))
        for nevra, dpkg in deltarpms.items():
            for drpm in dpkg.deltas.values():
                v1_drpms.append(drpm)
        self._assert_upgrade(v1_drpms)
        self._assert_associations()

    def _assert_upgrade(self, v1_drpms):
        v2_drpms = self.tmp_test_db.database.units_drpm.find().sort('filename')
        self.assertEqual(len(v1_drpms), v2_drpms.count())
        for drpm in v1_drpms:
            v2_drpm = self.tmp_test_db.database.units_drpm.find_one({'filename' : drpm.filename})
            self.assertEqual(v2_drpm["checksumtype"],  drpm.checksum_type)
            self.assertEqual(v2_drpm["sequence"], drpm.sequence)
            self.assertEqual(v2_drpm["checksum"], drpm.checksum)
            self.assertEqual(v2_drpm["filename"], drpm.filename)
            self.assertEqual(v2_drpm["epoch"], drpm.epoch)
            self.assertEqual(v2_drpm["version"], drpm.version)
            self.assertEqual(v2_drpm["release"], drpm.release)
            self.assertEqual(v2_drpm["size"], drpm.size)

    def _assert_associations(self):
        v2_ass_coll = self.tmp_test_db.database.repo_content_units
        v2_drpm_ids = [drpm['_id'] for drpm in self.tmp_test_db.database.units_drpm.find({},{'_id' : 1})]
        # Make sure there are associations for each
        query = {
            'repo_id' : 'test_drpm_repo',
            'unit_id' : {'$in' : v2_drpm_ids},
            'unit_type_id' : 'drpm',
        }
        associations = v2_ass_coll.find(query)
        # Sanity check that the right number were found
        self.assertEqual(len(v2_drpm_ids), associations.count())
        for ass in associations:
            self.assertTrue(isinstance(ass['_id'], ObjectId))
            self.assertEqual(ass['repo_id'], 'test_drpm_repo')
            self.assertTrue(ass['unit_id'] in v2_drpm_ids)
            self.assertEqual(ass['unit_type_id'],'drpm')
            self.assertEqual(ass['owner_type'], units.DEFAULT_OWNER_TYPE)
            self.assertEqual(ass['owner_id'], units.DEFAULT_OWNER_ID)
            self.assertEqual(ass['created'], units.DEFAULT_CREATED)
            self.assertEqual(ass['updated'], units.DEFAULT_UPDATED)


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

        #   Units
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

        #   Associations
        v1_distros = self.v1_test_db.database.distribution.find()
        for v1_distro in v1_distros:
            expected_repo_ids = v1_distro['repoids']
            v2_distro = self.tmp_test_db.database.units_distribution.find_one({'id' : v1_distro['id']}, {'_id' : 1})
            ass_query = {'unit_id' : v2_distro['_id'], 'repo_id' : {'$in' : expected_repo_ids}}
            associations = self.tmp_test_db.database.repo_content_units.find(ass_query)
            self.assertEqual(len(expected_repo_ids), associations.count())

            for association in associations:
                self.assertTrue(isinstance(association['_id'], ObjectId))
                self.assertTrue(association['repo_id'] in expected_repo_ids)
                self.assertEqual(association['unit_id'], v2_distro['_id'])
                self.assertEqual(association['unit_type_id'], 'distribution')
                self.assertEqual(association['owner_type'], units.DEFAULT_OWNER_TYPE)
                self.assertEqual(association['owner_id'], units.DEFAULT_OWNER_ID)
                self.assertEqual(association['created'], units.DEFAULT_CREATED)
                self.assertEqual(association['updated'], units.DEFAULT_UPDATED)

    def test_upgrade_idempotency(self):
        # Test
        report = UpgradeStepReport()
        units._distributions(self.v1_test_db.database, self.tmp_test_db.database, report)
        result = units._distributions(self.v1_test_db.database, self.tmp_test_db.database, report)

        # Verify - Simple Count Check
        self.assertTrue(result)

        #   Units
        v1_distros = self.v1_test_db.database.distribution.find()
        v2_distros = self.tmp_test_db.database.units_distribution.find()
        self.assertEqual(v1_distros.count(), v2_distros.count())

        #   Associations
        v1_distros = self.v1_test_db.database.distribution.find()
        for v1_distro in v1_distros:
            expected_repo_ids = v1_distro['repoids']
            v2_distro = self.tmp_test_db.database.units_distribution.find_one({'id' : v1_distro['id']}, {'_id' : 1})
            ass_query = {'unit_id' : v2_distro['_id'], 'repo_id' : {'$in' : expected_repo_ids}}
            associations = self.tmp_test_db.database.repo_content_units.find(ass_query)
            self.assertEqual(len(expected_repo_ids), associations.count())


class ErrataUpgradeTests(BaseDbUpgradeTests):

    def test_errata(self):
        # Test
        report = UpgradeStepReport()
        result = units._errata(self.v1_test_db.database, self.tmp_test_db.database, report)

        # Verify
        self.assertTrue(result)

        #   Units
        v1_errata = self.v1_test_db.database.errata.find().sort('id')
        v2_errata = self.tmp_test_db.database.units_erratum.find().sort('id')
        self.assertEqual(v1_errata.count(), v2_errata.count())

        for v1_erratum, v2_erratum in zip(v1_errata, v2_errata):
            self.assertTrue(isinstance(v2_erratum['_id'], ObjectId))
            self.assertEqual(v2_erratum['_storage_path'], None)

            for k in ('description', 'from_str', 'id', 'issued', 'pushcount',
                      'reboot_suggested', 'references', 'release', 'rights',
                      'severity', 'solution', 'status', 'summary', 'title',
                      'type', 'updated', 'version'):
                self.assertEqual(v2_erratum[k], v1_erratum[k], msg='Unequal key: %s' % k)

        #   Associations
        v1_errata = self.v1_test_db.database.errata.find().sort('id')
        for v1_erratum in v1_errata:
            expected_repo_ids = v1_erratum['repoids']
            v2_erratum = self.tmp_test_db.database.units_erratum.find_one({'id' : v1_erratum['id']}, {'_id' : 1})
            ass_query = {'unit_id' : v2_erratum['_id'], 'repo_id' : {'$in' : expected_repo_ids}}
            associations = self.tmp_test_db.database.repo_content_units.find(ass_query)
            self.assertEqual(len(expected_repo_ids), associations.count())

            for association in associations:
                self.assertTrue(isinstance(association['_id'], ObjectId))
                self.assertTrue(association['repo_id'] in expected_repo_ids)
                self.assertEqual(association['unit_id'], v2_erratum['_id'])
                self.assertEqual(association['unit_type_id'], 'erratum')
                self.assertEqual(association['owner_type'], units.DEFAULT_OWNER_TYPE)
                self.assertEqual(association['owner_id'], units.DEFAULT_OWNER_ID)
                self.assertEqual(association['created'], units.DEFAULT_CREATED)
                self.assertEqual(association['updated'], units.DEFAULT_UPDATED)

    def test_errata_idempotency(self):
        # Test
        report = UpgradeStepReport()
        units._errata(self.v1_test_db.database, self.tmp_test_db.database, report)
        result = units._errata(self.v1_test_db.database, self.tmp_test_db.database, report)

        # Verify - Simple Count Tests
        self.assertTrue(result)

        #   Units
        v1_errata = self.v1_test_db.database.errata.find()
        v2_errata = self.tmp_test_db.database.units_erratum.find()
        self.assertEqual(v1_errata.count(), v2_errata.count())

        #   Associations
        for v1_erratum in v1_errata:
            expected_repo_ids = v1_erratum['repoids']
            v2_erratum = self.tmp_test_db.database.units_erratum.find_one({'id' : v1_erratum['id']}, {'_id' : 1})
            ass_query = {'unit_id' : v2_erratum['_id'], 'repo_id' : {'$in' : expected_repo_ids}}
            associations = self.tmp_test_db.database.repo_content_units.find(ass_query)
            self.assertEqual(len(expected_repo_ids), associations.count())



class PackageGroupUpgradeTests(BaseDbUpgradeTests):

    def setUp(self):
        super(PackageGroupUpgradeTests, self).setUp()

        units._initialize_association_collection(self.tmp_test_db.database)

    def test_groups(self):
        # Test
        report = UpgradeStepReport()
        result = units._package_groups(self.v1_test_db.database, self.tmp_test_db.database, report)

        # Verify
        self.assertTrue(result)

        v1_repo_group_tuples = []
        for v1_repo in self.v1_test_db.database.repos.find({}, {'id' : 1, 'packagegroups' : 1}):
            for group_id in v1_repo['packagegroups'].keys():
                v1_repo_group_tuples.append( (v1_repo['id'], group_id) )

        v2_repo_group_tuples = [ (x['repo_id'], x['id']) for x in
                                 self.tmp_test_db.database.units_package_group.find({}, {'repo_id': 1, 'id' : 1}) ]

        v1_repo_group_tuples.sort()
        v2_repo_group_tuples.sort()
        self.assertEqual(v1_repo_group_tuples, v2_repo_group_tuples)

        for v1_repo in self.v1_test_db.database.repos.find({}, {'id' : 1, 'packagegroups' : 1}):
            for group_id in v1_repo.get('packagegroups', {}).keys():
                # Verify the group itself
                v1_group = v1_repo['packagegroups'][group_id]
                v2_group = self.tmp_test_db.database.units_package_group.find_one({'repo_id' : v1_repo['id'], 'id' : group_id})
                self.assertTrue(v2_group is not None)

                self.assertTrue(isinstance(v2_group['_id'], ObjectId))
                self.assertEqual(v2_group['_storage_path'], None)
                self.assertEqual(v2_group['_content_type_id'], 'package_group')

                for k in ('conditional_package_names', 'default', 'default_package_names',
                    'description', 'display_order', 'id', 'langonly', 'mandatory_package_names',
                    'name', 'optional_package_names', 'translated_description',
                    'translated_name', 'user_visible'):
                    self.assertEqual(v1_group[k], v2_group[k], msg='Incorrect key: %s' % k)

                # Make sure an association exists
                ass_query = {'repo_id' : v1_repo['id'],
                             'unit_id' : v2_group['_id'],
                             'unit_type_id' : 'package_group'}
                association = self.tmp_test_db.database.repo_content_units.find_one(ass_query)
                self.assertTrue(association is not None)
                self.assertEqual(association['owner_type'], units.DEFAULT_OWNER_TYPE)
                self.assertEqual(association['owner_id'], units.DEFAULT_OWNER_ID)
                self.assertEqual(association['created'], units.DEFAULT_CREATED)
                self.assertEqual(association['updated'], units.DEFAULT_UPDATED)

    def test_groups_idempotency(self):
        # Test
        report = UpgradeStepReport()
        units._package_groups(self.v1_test_db.database, self.tmp_test_db.database, report)

        result = units._package_groups(self.v1_test_db.database, self.tmp_test_db.database, report)

        # Verify - Simple Count Tests
        self.assertTrue(result)

        # Make sure the groups weren't duplicated
        v1_count = 0
        for v1_repo in self.v1_test_db.database.repos.find({}, {'id' : 1, 'packagegroups' : 1}):
            v1_count += len(v1_repo['packagegroups'].keys())

        v2_count = self.tmp_test_db.database.units_package_group.find().count()

        self.assertEqual(v1_count, v2_count)

        # Make sure the associations weren't duplicated
        for v1_repo in self.v1_test_db.database.repos.find({}, {'id' : 1, 'packagegroups' : 1}):
            expected_group_count = len(v1_repo['packagegroups'])
            associations = self.tmp_test_db.database.repo_content_units.find({'repo_id' : v1_repo['id']})
            self.assertEqual(expected_group_count, associations.count())


class PackageCategoryUpgradeTests(BaseDbUpgradeTests):

    def setUp(self):
        super(PackageCategoryUpgradeTests, self).setUp()

        units._initialize_association_collection(self.tmp_test_db.database)

    def test_categories(self):
        # Test
        report = UpgradeStepReport()
        result = units._package_group_categories(self.v1_test_db.database, self.tmp_test_db.database, report)

        # Verify
        self.assertTrue(result)

        v1_repo_category_tuples = []
        for v1_repo in self.v1_test_db.database.repos.find({}, {'id' : 1, 'packagegroupcategories' : 1}):
            for categoryid in v1_repo['packagegroupcategories'].keys():
                v1_repo_category_tuples.append( (v1_repo['id'], categoryid) )

        v2_repo_category_tuples = [ (x['repo_id'], x['id']) for x in
                                 self.tmp_test_db.database.units_package_category.find({}, {'repo_id': 1, 'id' : 1}) ]

        v1_repo_category_tuples.sort()
        v2_repo_category_tuples.sort()
        self.assertEqual(v1_repo_category_tuples, v2_repo_category_tuples)

        for v1_repo in self.v1_test_db.database.repos.find({}, {'id' : 1, 'packagegroupcategories' : 1}):
            for category_id in v1_repo.get('packagegroupcategories', {}).keys():
                # Verify the categories themselves
                v1_category = v1_repo['packagegroupcategories'][category_id]
                v2_category = self.tmp_test_db.database.units_package_category.find_one({'repo_id' : v1_repo['id'], 'id' : category_id})
                self.assertTrue(v2_category is not None)

                self.assertTrue(isinstance(v2_category['_id'], ObjectId))
                self.assertEqual(v2_category['_storage_path'], None)
                self.assertEqual(v2_category['_content_type_id'], 'package_category')

                for k in ('description', 'display_order', 'id', 'name',
                          'packagegroupids', 'translated_description',
                          'translated_name'):
                    self.assertEqual(v2_category[k], v1_category[k])

                # Make sure an association exists
                ass_query = {'repo_id' : v1_repo['id'],
                             'unit_id' : v2_category['_id'],
                             'unit_type_id' : 'package_category'}
                association = self.tmp_test_db.database.repo_content_units.find_one(ass_query)
                self.assertTrue(association is not None)
                self.assertEqual(association['owner_type'], units.DEFAULT_OWNER_TYPE)
                self.assertEqual(association['owner_id'], units.DEFAULT_OWNER_ID)
                self.assertEqual(association['created'], units.DEFAULT_CREATED)
                self.assertEqual(association['updated'], units.DEFAULT_UPDATED)

    def test_categories_idempotency(self):
        # Test
        report = UpgradeStepReport()
        units._package_group_categories(self.v1_test_db.database, self.tmp_test_db.database, report)
        result = units._package_group_categories(self.v1_test_db.database, self.tmp_test_db.database, report)

        # Verify - Simple Count Tests
        self.assertTrue(result)

        # Make sure the categories weren't duplicated
        v1_count = 0
        for v1_repo in self.v1_test_db.database.repos.find({}, {'id' : 1, 'packagegroupcategories' : 1}):
            v1_count += len(v1_repo['packagegroupcategories'].keys())

        v2_count = self.tmp_test_db.database.units_package_category.find().count()

        self.assertEqual(v1_count, v2_count)

        # Make sure the associations weren't duplicated
        for v1_repo in self.v1_test_db.database.repos.find({}, {'id' : 1, 'packagegroupcategories' : 1}):
            expected_group_count = len(v1_repo['packagegroupcategories'])
            associations = self.tmp_test_db.database.repo_content_units.find({'repo_id' : v1_repo['id']})
            self.assertEqual(expected_group_count, associations.count())


class ISOUpgradeTests(BaseDbUpgradeTests):

    def test_iso(self):
        # Test
        report = UpgradeStepReport()
        success = units._isos(self.v1_test_db.database, self.tmp_test_db.database, report)

        # Verify
        self.assertTrue(success)

        # Verify - Units
        v1_files_coll = self.v1_test_db.database.file
        v2_iso_coll = self.tmp_test_db.database.units_iso

        v1_files = v1_files_coll.find()
        for v1_file in v1_files:
            v2_query = {'name' : v1_file['filename']}
            v2_iso = v2_iso_coll.find_one(v2_query)
            self.assertTrue(v2_iso is not None)

            self.assertEqual(v2_iso['name'], v1_file['filename'])
            self.assertEqual(v2_iso['checksum'], v1_file['checksum'].values()[0])
            self.assertEqual(v2_iso['size'], v1_file['size'])

        # Verify - Associations
        v1_repo_coll = self.v1_test_db.database.repos
        v1_file_coll = self.v1_test_db.database.file
        v2_ass_coll = self.tmp_test_db.database.repo_content_units

        v1_repos = v1_repo_coll.find({'content_types' : 'iso'})
        for v1_repo in v1_repos:
            for v1_file_id in v1_repo['files']:
                v1_file = v1_file_coll.find_one({'_id' : v1_file_id})
                v2_iso = v2_iso_coll.find_one({'name' : v1_file['filename']})

                spec = {'unit_id' : v2_iso['_id'],
                        'unit_type_id' : 'iso',
                        'repo_id' : v1_repo['id']}
                association = v2_ass_coll.find_one(spec)
                self.assertTrue(association is not None)

    def test_iso_idempotency(self):
        # Setup
        report = UpgradeStepReport()
        units._initialize_content_types(self.tmp_test_db.database)
        units._isos(self.v1_test_db.database, self.tmp_test_db.database, report)

        # Test
        success = units._isos(self.v1_test_db.database, self.tmp_test_db.database, report)

        # Verify
        self.assertTrue(success)

        v1_count = self.v1_test_db.database.file.find().count()
        v2_count = self.tmp_test_db.database.units_iso.find().count()

        self.assertEqual(v1_count, v2_count)
