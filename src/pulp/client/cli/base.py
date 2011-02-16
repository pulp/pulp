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
import sys
from gettext import gettext as _
from optparse import OptionGroup, OptionParser, SUPPRESS_HELP

from pulp.client.config import Config
from pulp.client import server


_cfg = Config()


class PulpCLI(object):
    """
    Pulp command line tool class.
    """

    def __init__(self):
        self.name = os.path.basename(sys.argv[0])
        self.parser = OptionParser()
        self.parser.disable_interspersed_args()
        self.opts = None
        self._server = None
        self._commands = {}

    @property
    def usage(self):
        """
        Usage string.
        @rtype: str
        @return: command's usage string
        """
        lines = ['Usage: %s <options> <command>' % self.name,
                 'Supported Commands:']
        for name, command in sorted(self._commands.items()):
            lines.append('\t%-14s %-25s' % (name, command.description))
        return '\n'.join(lines)

    def add_command(self, name, command):
        """
        Add a command to this command line tool
        @type name: str
        @param name: name to associate with the command
        @type command: L{pulp.client.core.base.Command} instance
        @param command: command to add
        """
        command.cli = self
        command.name = name
        self._commands[name] = command

    def setup_parser(self):
        """
        Add options to the command line parser.
        @note: this method may be overridden to define new options
        """
        credentials = OptionGroup(self.parser, _('Pulp User Account Credentials'))
        credentials.add_option('-u', '--username', dest='username',
                               default=None, help=_('account username'))
        credentials.add_option('-p', '--password', dest='password',
                               default=None, help=_('account password'))
        credentials.add_option('--cert-file', dest='certfile',
                               default=None, help=SUPPRESS_HELP)
        credentials.add_option('--key-file', dest='keyfile',
                               default=None, help=SUPPRESS_HELP)
        self.parser.add_option_group(credentials)

        server = OptionGroup(self.parser, _('Pulp Server Information'))
        host = _cfg.server.host or 'localhost.localdomain'
        server.add_option('--host', dest='host', default=host,
                          help=_('pulp server host name (default: %s)') % host)
        port = _cfg.server.port or '443'
        server.add_option('--port', dest='port', default=port,
                          help=SUPPRESS_HELP)
        protocol = _cfg.server.scheme or 'https'
        server.add_option('--protocol', dest='protocol', default=protocol,
                          help=SUPPRESS_HELP)
        path = _cfg.server.path or '/pulp/api'
        server.add_option('--path', dest='path', default=path,
                          help=SUPPRESS_HELP)
        self.parser.add_option_group(server)

    def setup_server(self):
        host = self.opts.host
        port = self.opts.port
        protocol = self.opts.protocol
        path = self.opts.path
        #print >> sys.stderr, 'server information: %s, %s, %s, %s' % \
        #        (host, port, protocol, path)
        self._server = server.PulpServer(host, int(port), protocol, path)
        server.set_active_server(self._server)

    def setup_credentials(self):
        if None not in (self.opts.username, self.opts.password):
            self._server.set_basic_auth_credentials(self.opts.username,
                                                    self.opts.password)
        elif None not in (self.opts.certfile, self.opts.keyfile):
            self._server.set_ssl_credentials(self.opts.certfile,
                                             self.opts.keyfile)

    def main(self, args=sys.argv[1:]):
        """
        Run this command.
        @type args: list of str's
        @param args: command line arguments
        """
        self.parser.set_usage(self.usage)
        self.setup_parser()
        self.opts, args = self.parser.parse_args(args)
        if not args:
            self.parser.error(_('No command given; please see --help'))
        command = self._commands.get(args[0], None)
        if command is None:
            self.parser.error(_('Invalid command; please see --help'))
        self.setup_server()
        self.setup_credentials()
        command.main(args[1:])
