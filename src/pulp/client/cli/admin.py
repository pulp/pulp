# -*- coding: utf-8 -*-

# Copyright © 2010 Red Hat, Inc.
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

from pulp.client.cli.base import PulpCLI
from pulp.client.credentials import Login


class AdminCLI(PulpCLI):

    def setup_credentials(self):
        super(AdminCLI, self).setup_credentials()
        login = Login()
        certfile = login.crtpath()
        keyfile = login.keypath()
        if not os.access(certfile, os.R_OK) or not os.access(keyfile, os.R_OK):
            return
        self._server.set_ssl_credentials(certfile, keyfile)
