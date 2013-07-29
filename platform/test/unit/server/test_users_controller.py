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

# Import the test base from pulp/platform/test/unit/server/
import base


class UserSearchTests(base.PulpWebserviceTests):

    def test_get_auth_required(self):
        """
        Test that when the proper authentication information is missing, the server returns a 401 error
        when UserSearch.GET is called
        """
        # Setup. Remove valid authentication information.
        old_auth = base.PulpWebserviceTests.HEADERS
        base.PulpWebserviceTests.HEADERS = {}

        # Test that a call results in a 401 status
        call_status, call_body = self.get('/v2/users/search/')
        self.assertEqual(401, call_status)

        # Clean up
        base.PulpWebserviceTests.HEADERS = old_auth

    def test_post_auth_required(self):
        """
        Test that when the proper authentication information is missing, the server returns a 401 error
        when UserSearch.POST is called
        """
        # Setup. Remove valid authentication information.
        old_auth = base.PulpWebserviceTests.HEADERS
        base.PulpWebserviceTests.HEADERS = {}

        # Test that a call results in a 401 status
        call_status, call_body = self.post('/v2/users/search/')
        self.assertEqual(401, call_status)

        # Clean up
        base.PulpWebserviceTests.HEADERS = old_auth
