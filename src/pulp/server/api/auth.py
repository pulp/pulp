# -*- coding: utf-8 -*-
# Copyright © 2010-2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from pulp.repo_auth.repo_cert_utils import RepoCertUtils
from pulp.server.api.base import BaseApi
from pulp.server.api.cds import CdsApi
from pulp.server.auditing import audit
from pulp.server.auth import cert_generator, principal
from pulp.common.bundle import Bundle
from pulp.server import config


class AuthApi(BaseApi):

    def __init__(self):
        self.cds_api = CdsApi()

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
        bundle = cert_generator.make_admin_user_cert(user)
        bundle = ''.join(bundle)
        return bundle

    def isadmin(self, login):
        """
        Get whether the specified login is the admin user.
        @param login: A login to check.
        @type login: str
        @rtype: bool
        """
        adminlogin = cert_generator.ADMIN_PREFIX[:-1]
        return login == adminlogin

    def enable_global_repo_auth(self, cert_bundle):
        '''
        Stores the given cert bundle as the credentials for global repo authentication.
        After this call, *all* future consumer requests to repositories will be
        validated against the credentials passed in this call.

        If global repository authentication is already enabled, the credentials will
        be replaced with those passed into this call (no error is thrown).

        If any CDS instances are registered to the Pulp server, they will be sent
        the authentication update as well. This call returns two lists that describe
        the results of which CDS instances were successfully updated. No error is
        thrown regardless of CDS update outcome, however an error is thrown if the
        Pulp server itself cannot be updated.

        @param cert_bundle: contains a consumer certificate bundle; see repo_cert_utils
                            for more information
        @type  cert_bundle: dict {str, str}
        '''
        repo_cert_utils = RepoCertUtils(config.config)
        key = cert_bundle.get('key', '')
        cert = cert_bundle.get('cert', '')
        if key:
            cert = Bundle.join(key, cert)
        del cert_bundle['key']
        repo_cert_utils.validate_cert_bundle(cert_bundle)
        repo_cert_utils.write_global_repo_cert_bundle(cert_bundle)

    def disable_global_repo_auth(self):
        '''
        Removes the global repository authentication credentials, allowing all future
        consumer repo requests to proceed without authentication.

        If global repository authentication is not already enabled, this call has no
        effect.

        If any CDS instances are registered to the Pulp server, they will be sent
        the authentication update as well. This call returns two lists that describe
        the results of which CDS instances were successfully updated. No error is
        thrown regardless of CDS update outcome, however an error is thrown if the
        Pulp server itself cannot be updated.
        '''
        repo_cert_utils = RepoCertUtils(config.config)
        repo_cert_utils.delete_global_cert_bundle()
