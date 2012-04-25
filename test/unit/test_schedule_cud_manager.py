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

from pulp.server.dispatch import factory as dispatch_factory
from pulp.server.managers.schedule.cud import ScheduleManager

# schedule tests base class ----------------------------------------------------

class ScheduleTests(testutil.PulpCoordinatorTest):

    def setUp(self):
        super(ScheduleTests, self).setUp()
        self.schedule_manager = ScheduleManager()

    def tearDown(self):
        super(ScheduleTests, self).tearDown()
        self.schedule_manager = None

# sync schedule tests ----------------------------------------------------------

class ScheduledSyncTests(ScheduleTests):
    pass

