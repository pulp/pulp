# -*- coding: utf-8 -*-
# Copyright © 2010-2011 Red Hat, Inc.
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

from pulp.server.api.base import BaseApi
from pulp.server.auditing import audit
from pulp.server.auth import cert_generator, principal


class AuthApi(BaseApi):

    @audit()
    def admin_certificate(self):
        '''
        Generates an admin authentication certificate for the currently logged in
        user.

        @return: tuple of the private key and certificate
        @rtype:  (string, string)
        '''

        # Get the currently logged in user
        user = principal.get_principal()

        private_key, cert = cert_generator.make_admin_user_cert(user)
        return private_key, cert

    def isadmin(self, login):
        """
        Get whether the specified login is the admin user.
        @param login: A login to check.
        @type login: str
        @rtype: bool
        """
        adminlogin = cert_generator.ADMIN_PREFIX[:-1]
        return (login == adminlogin)
