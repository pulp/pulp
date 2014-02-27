# -*- coding: utf-8 -*-
#
# Copyright © 2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import unittest
from datetime import timedelta

import mock

from pulp.common import dateutils
from pulp.server import exceptions
from pulp.server.db.model.dispatch import ScheduledCall
from pulp.server.managers.factory import initialize
from pulp.server.webservices.controllers.schedule import ScheduleResource


initialize()


@mock.patch('pulp.server.managers.schedule.utils.get')
class TestScheduleResource(unittest.TestCase):
    def setUp(self):
        super(TestScheduleResource, self).setUp()
        self.controller = ScheduleResource()

    @mock.patch.object(ScheduleResource, 'ok')
    @mock.patch('pulp.server.webservices.http.uri_path', return_value='http://foo/bar')
    def test_get(self, mock_path, mock_ok, mock_utils_get):
        call = ScheduledCall('PT1M', 'pulp.tasks.frequent')
        mock_utils_get.return_value = [call]

        ret = self.controller._get(call.id)
        schedule = mock_ok.call_args[0][0]

        self.assertEqual(ret, mock_ok.return_value)
        self.assertEqual(len(mock_ok.call_args[0]), 1)

        # spot-check the schedule
        self.assertEqual(schedule['_id'], call.id)
        self.assertEqual(schedule['schedule'], 'PT1M')
        self.assertEqual(schedule['task'], 'pulp.tasks.frequent')
        self.assertEqual(schedule['_href'], mock_path.return_value)

        # next_run is calculated on-demand, and there is a small chance that it
        # will be re-calculated in the call.for_display() call as 1 second later
        # than it was calculated above. Thus we will test that equality here
        # with a tolerance of 1 second
        for_display = call.for_display()
        call_next_run = dateutils.parse_iso8601_datetime(call.next_run)
        display_next_run = dateutils.parse_iso8601_datetime(for_display['next_run'])
        self.assertTrue(display_next_run - call_next_run <= timedelta(seconds=1))

        # now check overall equality with the actual for_display value
        del schedule['_href']
        del schedule['next_run']
        del for_display['next_run']
        self.assertEqual(schedule, for_display)

        # make sure we called the manager layer correctly
        mock_utils_get.assert_called_once_with([call.id])

    def test_missing(self, mock_utils_get):
        call = ScheduledCall('PT1M', 'pulp.tasks.frequent')
        mock_utils_get.return_value = []

        self.assertRaises(exceptions.MissingResource, self.controller._get, call.id)
