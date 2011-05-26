# -*- coding: utf-8 -*-

# Copyright © 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import os

from pulp.client.cli.base import PulpCLI
from pulp.client.credentials import Consumer
from pulp.client.core.utils import system_exit

class ClientCLI(PulpCLI):

    def setup_credentials(self):
        """
        User the super-class credentials then fallback to the consumer
        credentials if present.
        """
        super(ClientCLI, self).setup_credentials()
        if self._server.has_credentials_set():
            return
        consumer = Consumer()
        certfile = consumer.crtpath()
        keyfile = consumer.keypath()
        if os.access(certfile, os.R_OK) and os.access(keyfile, os.R_OK):
            self._server.set_ssl_credentials(certfile, keyfile)
        elif None not in (self.opts.username, self.opts.password):
            self._server.set_basic_auth_credentials(self.opts.username, self.opts.password)