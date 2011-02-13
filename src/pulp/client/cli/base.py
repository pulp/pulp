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

from pulp.client.credentials import Credentials
from pulp.client.config import Config

_cfg = Config()

class PulpCLI(object):
    """
    Pulp command line tool class.
    """

    def __init__(self):
        self.name = os.path.basename(sys.argv[0])
        self.parser = OptionParser()
        self.parser.disable_interspersed_args()
        self._commands = {}
        self._server = None

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

    def set_server(self, server):
        self._server = server
        for command in self._commands.values():
            command.set_server(server)

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
        if self._server is not None:
            command.set_server(self._server)

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
        credentials.add_option('--cert-file', dest='cert_file',
                               default=None, help=SUPPRESS_HELP)
        credentials.add_option('--key-file', dest='key_file',
                               default=None, help=SUPPRESS_HELP)
        self.parser.add_option_group(credentials)

        server = OptionGroup(self.parser, _('Pulp Server Information'))
        server.add_option('-s', '--server', dest='server', default=None,
                          help=_('pulp server host'))
        self.parser.add_option_group(server)

    def main(self, args=sys.argv[1:]):
        """
        Run this command.
        @type args: list of str's
        @param args: command line arguments
        """
        self.parser.set_usage(self.usage)
        self.setup_parser()
        opts, args = self.parser.parse_args(args)
        if not args:
            self.parser.error(_('No command given; please see --help'))
        command = self._commands.get(args[0], None)
        if command is None:
            self.parser.error(_('Invalid command; please see --help'))
        if opts.server is not None:
            Credentials.setserver(opts.server)
        Credentials.setuser(opts.username, opts.password)
        Credentials.setcert(opts.key_file, opts.cert_file)
        command.main(args[1:])
