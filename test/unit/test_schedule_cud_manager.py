# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
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

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/../common/'))

import testutil
import mock_plugins

from pulp.server import exceptions as pulp_exceptions
from pulp.server.db.model.gc_repository import Repo, RepoDistributor, RepoImporter
from pulp.server.dispatch import factory as dispatch_factory
from pulp.server.managers import factory as managers_factory
from pulp.server.managers.schedule.cud import ScheduleManager

# schedule tests base class ----------------------------------------------------

class ScheduleTests(testutil.PulpCoordinatorTest):

    def setUp(self):
        super(ScheduleTests, self).setUp()

        mock_plugins.install()
        self._repo_manager = managers_factory.repo_manager()
        self._distributor_manager = managers_factory.repo_distributor_manager()
        self._importer_manager = managers_factory.repo_importer_manager()

        self.repo_id = 'scheduled-repo'
        self.distributor_type_id = 'mock-distributor'
        self.distributor_id = 'scheduled-distributor'
        self.importer_type_id = 'mock-importer'

        self._repo_manager.create_repo(self.repo_id)
        self._distributor_manager.add_distributor(self.repo_id, self.distributor_type_id, {}, False, distributor_id=self.distributor_id)
        self._importer_manager.set_importer(self.repo_id, self.importer_type_id, {})

        self.schedule_manager = ScheduleManager()

    def tearDown(self):
        super(ScheduleTests, self).tearDown()
        mock_plugins.reset()
        self._repo_manager = None
        self._distributor_manager = None
        self._importer_manager = None
        self.schedule_manager = None

    def clean(self):
        super(ScheduleTests, self).clean()
        Repo.get_collection().remove(safe=True)
        RepoDistributor.get_collection().remove(safe=True)
        RepoImporter.get_collection().remove(safe=True)

# schedule manager tests -------------------------------------------------------

class ScheduleManagerTests(testutil.PulpTest):

    def test_instantiation(self):
        schedule_manager = ScheduleManager()

    def test_validate_valid_keys(self):
        valid_keys = ('one', 'two', 'three')
        options = {'one': 1, 'two': 2, 'three': 3}
        schedule_manager = ScheduleManager()
        try:
            schedule_manager._validate_keys(options, valid_keys)
        except Exception, e:
            self.fail(str(e))

    def test_validate_invalid_superfluous_keys(self):
        valid_keys = ('yes', 'ok')
        options = {'ok': 1, 'not': 0}
        schedule_manager = ScheduleManager()
        self.assertRaises(pulp_exceptions.InvalidValue,
                          schedule_manager._validate_keys,
                          options, valid_keys)

    def test_validate_invalid_missing_keys(self):
        valid_keys = ('me', 'me_too')
        options = {'me': 'only'}
        schedule_manager = ScheduleManager()
        self.assertRaises(pulp_exceptions.MissingValue,
                          schedule_manager._validate_keys,
                          options, valid_keys, True)

# sync schedule tests ----------------------------------------------------------

class ScheduledSyncTests(ScheduleTests):

    def test_create_schedule(self):
        pass

    def test_delete_schedule(self):
        pass

    def test_update_schedule(self):
        pass

