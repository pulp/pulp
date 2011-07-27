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
from gettext import gettext as _
from optparse import OptionGroup, SUPPRESS_HELP
from pulp.client.lib.cli import PulpCLI
from pulp.client.admin.credentials import Login
from pulp.client.admin.loader import AdminPluginLoader
from pulp.client.lib.utils import system_exit
from pulp.client.admin.config import AdminConfig

class AdminCLI(PulpCLI):
    """
    Pulp admin command line interface class.
    @cvar CONFIG: Config class for this cli.
    @type CONFIG: class
    @cvar PLUGIN_LOADER: Plugin loader class for this cli.
    @type PLUGIN_LOADER: class
    """

    CONFIG = AdminConfig
    PLUGIN_LOADER = AdminPluginLoader

    def setup_credentials(self):
        """
        Use the super-class credentials, then fall back to auth login
        credentials if present.
        """
        super(AdminCLI, self).setup_credentials()
        if self._server.has_credentials_set():
            return
        login = Login()
        certfile = login.crtpath()
        if os.access(certfile, os.R_OK):
            self._server.set_ssl_credentials(certfile)
        elif None not in (self.opts.username, self.opts.password):
            self._server.set_basic_auth_credentials(self.opts.username, self.opts.password)
            
            
    def setup_parser(self):
        """
        Add options to the command line parser.
        @note: this method may be overridden to define new options
        """
        PulpCLI.setup_parser(self)

        server = OptionGroup(self.parser, _('Pulp Server Information'))
        host = self.cfg.server.host or 'localhost.localdomain'
        server.add_option('--host', dest='host', default=host,
                          help=_('pulp server host name (default: %s)') % host)
        port = self.cfg.server.port or '443'
        server.add_option('--port', dest='port', default=port,
                          help=SUPPRESS_HELP)
        scheme = self.cfg.server.scheme or 'https'
        server.add_option('--scheme', dest='scheme', default=scheme,
                          help=SUPPRESS_HELP)
        path = self.cfg.server.path or '/pulp/api'
        server.add_option('--path', dest='path', default=path,
                          help=SUPPRESS_HELP)
        self.parser.add_option_group(server)
