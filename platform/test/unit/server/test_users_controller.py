# -*- coding: utf-8 -*-
#
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

import mock

# Import the test base from pulp/platform/test/unit/server/
import base


class UserSearchTests(base.PulpWebserviceTests):
    @mock.patch.object(base.PulpWebserviceTests, 'HEADERS', spec=dict)
    def test_get_auth_required(self, mock_headers):
        """
        Test that when the proper authentication information is missing, the server returns a 401 error
        when UserSearch.GET is called
        """
        call_status, call_body = self.get('/v2/users/search/')
        self.assertEqual(401, call_status)

    @mock.patch.object(base.PulpWebserviceTests, 'HEADERS', spec=dict)
    def test_post_auth_required(self, mock_headers):
        """
        Test that when the proper authentication information is missing, the server returns a 401 error
        when UserSearch.POST is called
        """
        call_status, call_body = self.post('/v2/users/search/')
        self.assertEqual(401, call_status)
