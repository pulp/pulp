#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

import os
import sys
import unittest

srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src/"
sys.path.insert(0, srcdir)
commondir = os.path.abspath(os.path.dirname(__file__)) + '/../common/'
sys.path.insert(0, commondir)

import testutil

testutil.load_test_config()

from pulp.server.api import scheduled_sync


class ScheduleValidationTester(unittest.TestCase):

    def test_valid__interval_only(self):
        for unit in ('weeks', 'days', 'hours', 'minutes'):
            schedule = {'interval': {unit: 1}}
        self.assertTrue(scheduled_sync._validate_schedule(schedule) is None)

    def test_valid__with_start_time(self):
        schedule = {'interval': {'hours': 2},
                    'start_time': {'year': 1999,
                                   'month': 12,
                                   'day': 31,
                                   'hour': 23,
                                   'minute': 59}}
        self.assertTrue(scheduled_sync._validate_schedule(schedule) is None)

    def test_valid_with_runs(self):
        schedule = {'interval': {'minutes': 1}, 'runs': 2}
        self.assertTrue(scheduled_sync._validate_schedule(schedule) is None)

    def test_valid_start_time_and_runs(self):
        schedule = {'interval': {'hours': 2},
                    'start_time': {'year': 1999,
                                   'month': 12,
                                   'day': 31,
                                   'hour': 23,
                                   'minute': 59},
                    'runs': 25}
        self.assertTrue(scheduled_sync._validate_schedule(schedule) is None)

    def test_invalid_no_interval(self):
        schedule = {}
        self.assertRaises(scheduled_sync.InvalidScheduleError,
                          scheduled_sync._validate_schedule,
                          schedule)

    def test_invalid_interval_wrong_units(self):
        schedule = {'interval': {'years': 5}}
        self.assertRaises(scheduled_sync.InvalidScheduleError,
                          scheduled_sync._validate_schedule,
                          schedule)

    def test_invalid_interval_wrong_value(self):
        schedule = {'interval': {'weeks': 5.1}}
        self.assertRaises(scheduled_sync.InvalidScheduleError,
                          scheduled_sync._validate_schedule,
                          schedule)

    def test_invalid_start_time_missing_key(self):
        schedule = {'interval': {'hours': 2}}
        start_time_keys = ('year', 'month', 'day', 'hour', 'minute')
        for key in start_time_keys:
            schedule['start_time'] = dict([(k, 1)
                                           for k in start_time_keys
                                           if k is not key])
            self.assertRaises(scheduled_sync.InvalidScheduleError,
                              scheduled_sync._validate_schedule,
                              schedule)

    def test_invalid_start_time_extra_key(self):
        schedule = {'interval': {'hours': 2},
                    'start_time': {'year': 1999,
                                   'month': 12,
                                   'day': 31,
                                   'hour': 23,
                                   'minute': 59,
                                   'extra': 0}}
        self.assertRaises(scheduled_sync.InvalidScheduleError,
                          scheduled_sync._validate_schedule,
                          schedule)

    def test_invalid_start_time_wrong_value(self):
        schedule = {'interval': {'hours': 2},
                    'start_time': {'year': 1999,
                                   'month': 12,
                                   'day': 'foo',
                                   'hour': 23,
                                   'minute': 59}}
        self.assertRaises(scheduled_sync.InvalidScheduleError,
                          scheduled_sync._validate_schedule,
                          schedule)

    def test_invalid_runs_wrong_value(self):
        schedule = {'interval': {'hours': 2},
                    'start_time': {'year': 1999,
                                   'month': 12,
                                   'day': 31,
                                   'hour': 23,
                                   'minute': 59},
                    'runs': 2.5}
        self.assertRaises(scheduled_sync.InvalidScheduleError,
                          scheduled_sync._validate_schedule,
                          schedule)

# -----------------------------------------------------------------------------

if __name__ == '__main__':
    unittest.main()
