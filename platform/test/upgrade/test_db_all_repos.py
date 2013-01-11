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

import datetime

import mock

from pulp.common import dateutils
from pulp.server.compat import ObjectId
from pulp.server.dispatch.call import CallRequest
from pulp.server.itineraries.repo import sync_with_auto_publish_itinerary
from pulp.server.managers.auth.principal import PrincipalManager
from pulp.server.managers.auth.user.system import SystemUser
from pulp.server.upgrade.model import UpgradeStepReport
from pulp.server.upgrade.db import all_repos, yum_repos

from base_db_upgrade import BaseDbUpgradeTests


class RepoUpgradeGroupsTests(BaseDbUpgradeTests):

    def setUp(self):
        super(RepoUpgradeGroupsTests, self).setUp()

        # Unfortunately the test database doesn't have any repo groups, so only
        # for these tests we'll munge the DB for interesting data.

        self.num_repos = 10
        self.num_groups = 3

        new_repos = []
        self.repo_ids_by_group_id = {}
        for i in range(0, self.num_repos):
            repo_id = 'repo-%s' % i
            group_id = 'group-%s' % (i % self.num_groups)
            new_repo = {
                'id' : repo_id,
                'groupid' : [group_id],
                'relative_path' : 'path-%s' % i,
                'content_types' : 'yum'
            }
            self.repo_ids_by_group_id.setdefault(group_id, []).append(repo_id)

            if i % 2 == 0:
                new_repo['groupid'].append('group-x')
                self.repo_ids_by_group_id.setdefault('group-x', []).append(repo_id)

            new_repos.append(new_repo)

        self.v1_test_db.database.repos.insert(new_repos, safe=True)

    def test_repo_groups(self):
        # Test
        report = UpgradeStepReport()
        result = all_repos._repo_groups(self.v1_test_db.database, self.tmp_test_db.database, report)

        # Verify
        self.assertEqual(result, True)

        v2_coll = self.tmp_test_db.database.repo_groups
        all_groups = list(v2_coll.find())
        self.assertEqual(self.num_groups + 1, len(all_groups))

        for group_id, repo_ids in self.repo_ids_by_group_id.items():
            group = self.tmp_test_db.database.repo_groups.find_one({'id' : group_id})
            self.assertTrue(isinstance(group['_id'], ObjectId))
            self.assertEqual(group['id'], group_id)
            self.assertEqual(group['display_name'], None)
            self.assertEqual(group['description'], None)
            self.assertEqual(group['notes'], {})
            self.assertEqual(group['repo_ids'], repo_ids)


class RepoScheduledSyncUpgradeTests(BaseDbUpgradeTests):

    def setUp(self):
        super(self.__class__, self).setUp()

        self.v1_repo_1_id = 'errata-repo'
        self.v1_repo_1_schedule = 'PT30M'

        self.v1_repo_2_id = 'pulp-v1-17-64'
        self.v1_repo_2_schedule = 'R6/2012-01-01T00:00:00Z/P21DT'

        repositories = (self.v1_repo_1_id, self.v1_repo_2_id)
        schedules = (self.v1_repo_1_schedule, self.v1_repo_2_schedule)
        for repo, schedule in zip(repositories, schedules):
            self._insert_scheduled_v1_repo(repo, schedule)

        # The v2 repository's importer needs to exist in the database otherwise
        # the schedule sanity check will fail
        self.tmp_test_db.database.repo_importers.insert({'repo_id' : self.v1_repo_1_id})
        self.tmp_test_db.database.repo_importers.insert({'repo_id' : self.v1_repo_2_id})

    def _insert_scheduled_v1_repo(self, repo_id, schedule):
        doc = {'sync_schedule': schedule,
               'sync_options': None,
               'last_sync': None}
        self.v1_test_db.database.repos.update({'_id': repo_id}, {'$set': doc}, safe=True)

    def _insert_scheduled_v2_repo(self, repo_id, schedule):
        importer_id = ObjectId()
        schedule_id = ObjectId()

        importer_doc = {'repo_id': repo_id,
                        'importer_id': importer_id,
                        'importer_type_id': yum_repos.YUM_IMPORTER_TYPE_ID,
                        'scheduled_syncs': [str(schedule_id)]}
        self.tmp_test_db.database.repo_importers.insert(importer_doc, safe=True)

        call_request = CallRequest(sync_with_auto_publish_itinerary, [repo_id], {'overrides': {}})
        interval, start, recurrences = dateutils.parse_iso8601_interval(schedule)
        scheduled_call_doc = {'_id': schedule_id,
                              'id': str(schedule_id),
                              'serialized_call_request': call_request.serialize(),
                              'schedule': schedule,
                              'failure_threshold': None,
                              'consecutive_failures': 0,
                              'first_run': start or datetime.datetime.utcnow(),
                              'next_run': None,
                              'last_run': None,
                              'remaining_runs': recurrences,
                              'enabled': True}
        scheduled_call_doc['next_run'] = all_repos._calculate_next_run(scheduled_call_doc)
        self.tmp_test_db.database.scheduled_calls.insert(scheduled_call_doc, safe=True)

    @mock.patch('pulp.server.managers.auth.principal.PrincipalManager.get_principal', SystemUser)
    @mock.patch('pulp.server.managers.factory.principal_manager', PrincipalManager)
    def test_schedule_upgrade(self):
        report = all_repos.upgrade(self.v1_test_db.database, self.tmp_test_db.database)
        self.assertTrue(report.success)

    @mock.patch('pulp.server.managers.auth.principal.PrincipalManager.get_principal', SystemUser)
    @mock.patch('pulp.server.managers.factory.principal_manager', PrincipalManager)
    def test_schedule_upgrade_idempotency(self):
        self._insert_scheduled_v2_repo(self.v1_repo_1_id, self.v1_repo_1_schedule)
        report = all_repos.upgrade(self.v1_test_db.database, self.tmp_test_db.database)
        self.assertTrue(report.success)
