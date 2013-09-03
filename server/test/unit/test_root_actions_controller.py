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

import base

from pulp.server.managers import factory as manager_factory

class UserCertificateControllerTests(base.PulpWebserviceTests):

    def test_get(self):
        # Setup
        user_query_manager = manager_factory.user_query_manager()
        cert_generation_manager = manager_factory.cert_generation_manager()
        
        user = user_query_manager.find_by_login(login='ws-user')

        # Test
        status, body = self.post('/v2/actions/login/')

        # Verify
        self.assertEqual(200, status)

        certificate = manager_factory.certificate_manager(content=str(body['key']+body['certificate']))
        cn = certificate.subject()['CN']
        username, id = cert_generation_manager.decode_admin_user(cn)

        self.assertEqual(username, user['login'])
        self.assertEqual(id, user['id'])
