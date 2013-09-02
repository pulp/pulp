# -*- coding: utf-8 -*-
#
# Copyright © 2012-2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License
# (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied, including the
# implied warranties of MERCHANTABILITY, NON-INFRINGEMENT, or FITNESS FOR A
# PARTICULAR PURPOSE.
# You should have received a copy of GPLv2 along with this software; if not,
# see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

from pulp.server.db.model.dispatch import ArchivedCall
from pulp.server.dispatch import call, history

import base


class ArchivedCallTests(base.PulpServerTests):

    def setUp(self):
        super(ArchivedCallTests, self).setUp()
        self.archived_call_collection = ArchivedCall.get_collection()
        self.archived_call_collection.remove(safe=True) # cleanup others' messes

    def tearDown(self):
        super(ArchivedCallTests, self).tearDown()
        self.archived_call_collection.remove(safe=True)

    def _generate_request_and_report(self):

        def test_function():
            pass

        call_request = call.CallRequest(test_function)
        call_report = call.CallReport.from_call_request(call_request)
        return call_request, call_report


class ArchivedCallCreateTests(ArchivedCallTests):

    def test_create_archived_call(self):
        call_request, call_report = self._generate_request_and_report()
        history.archive_call(call_request, call_report)
        self.assertEqual(self.archived_call_collection.find().count(), 1)

    def test_find_missing_archived_call(self):
        archived_calls = history.find_archived_calls()
        self.assertEqual(archived_calls.count(), 0)

    def test_find_archived_call_by_task_id(self):
        call_request, call_report = self._generate_request_and_report()
        history.archive_call(call_request, call_report)
        archived_calls = history.find_archived_calls(call_request_id=call_report.call_request_id)
        self.assertEqual(archived_calls.count(), 1)

    def test_find_archived_call_by_task_group_id(self):
        call_request, call_report = self._generate_request_and_report()
        call_request.group_id = call_report.call_request_group_id = '123'
        history.archive_call(call_request, call_report)
        archived_calls = history.find_archived_calls(call_request_group_id='123')
        self.assertEqual(archived_calls.count(), 1)

