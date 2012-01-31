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
import sys
from gettext import gettext as _

from pulp.client.api import server
from pulp.client.consumer.config import ConsumerConfig
from pulp.client.consumer.credentials import Consumer
from pulp.client.consumer.loader import ConsumerPluginLoader
from pulp.client.lib.cli import PulpCLI
from pulp.client.lib.utils import system_exit


class ConsumerCLI(PulpCLI):
    """
    Pulp consumer command line interface class.
    @cvar CONFIG: Config class for this cli.
    @type CONFIG: class
    @cvar PLUGIN_LOADER: Plugin loader class for this cli.
    @type PLUGIN_LOADER: class
    """

    CONFIG = ConsumerConfig
    PLUGIN_LOADER = ConsumerPluginLoader

    def setup_credentials(self):
        """
        User the super-class credentials then fallback to the consumer
        credentials if present.
        """
        super(ConsumerCLI, self).setup_credentials()
        if self._server.has_credentials_set():
            return
        consumer = Consumer()
        certfile = consumer.crtpath()
        if os.access(certfile, os.R_OK):
            self._server.set_ssl_credentials(certfile)
        elif None not in (self.opts.username, self.opts.password):
            self._server.set_basic_auth_credentials(self.opts.username, self.opts.password)
            
    def setup_server(self):
        """
        Setup the active server connection.
        """
        host = self.cfg.server.host or 'localhost.localdomain'
        port = self.cfg.server.port or '443'
        scheme = self.cfg.server.scheme or 'https'
        path = self.cfg.server.path or '/pulp/api'
        #print >> sys.stderr, 'server information: %s, %s, %s, %s' % \
        #        (host, port, scheme, path)
        self._server = server.PulpServer(host, int(port), scheme, path)
        server.set_active_server(self._server)

    def setup(self, args):
        """
        Overridden method setup method that issues a warning to run consumer
        create if not already done.
        """
        command = super(ConsumerCLI, self).setup(args)

        if (len(args) > 1 and
            not (command.name == "consumer" and args[1] == "register")):

            bundle = Consumer()
            if not bundle.getid():
                print >> sys.stderr, _("warning: this client is not known "
                    "to the pulp server; run 'pulp-consumer consumer register' "
                    "to register it")

        return command
