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

import logging

from pulp.server.auth import cert_generator, principal

# -- constants ----------------------------------------------------------------

_LOG = logging.getLogger(__name__)

# -- manager ------------------------------------------------------------------

class UserManager(object):
    """
    Handles the create/update/delete of users and the retrieval of a user
    session certificate.
    """

    def generate_user_certificate(self):
        """
        Generates a user certificate for the currently logged in user.

        @return: certificate and private key, combined into a single string,
                 that can be used to identify the current user on subsequent calls
        @rtype:  str
        """

        # Get the currently logged in user
        user = principal.get_principal()
        key, certificate = cert_generator.make_admin_user_cert(user)
        return key + certificate
