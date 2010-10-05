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

from pulp.client.core import load_core_commands


def root_check():
    """
    Simple function to assure execution by root.
    """
    if os.getuid() == 0:
        return
    print >> sys.stderr, _('error: must be root to execute')
    sys.exit(os.EX_NOUSER)


class PulpBase(object):
    """
    Base pulp command line tool class.
    @cvar _commands: list of command modules to load
    """

    _commands = None
    _actions = {}
    _actions_states = {}

    def __init__(self):
        self.commands = load_core_commands(self._commands,
                                           self._actions,
                                           self._actions_states)
        self.parser = OptionParser(usage=self.usage())
        self.parser.disable_interspersed_args()
        self.parser.add_option('--debug', dest='debug', action='store_true',
                               default=False, help=SUPPRESS_HELP)

    def usage(self):
        """
        Usage string.
        @rtype: str
        @return: command's usage string
        """
        lines = ['Usage: %s <options> <command>' % os.path.basename(sys.argv[0]),
                 'Supported Commands:']
        for name, command in sorted(self.commands.items()):
            lines.append('\t%-14s %-25s' % (name, command.description))
        return '\n'.join(lines)

    def setup_parser(self):
        """
        Add options to the command line parser.
        @note: this method may be overridden to define new options
        """
        credentials = OptionGroup(self.parser, _('pulp user account credentials'))
        credentials.add_option('-u', '--username', dest='username',
                               default=None, help=_('account username'))
        credentials.add_option('-p', '--password', dest='password',
                               default=None, help=_('account password'))
        credentials.add_option('--cert-file', dest='cert_file',
                               default=None, help=SUPPRESS_HELP)
        credentials.add_option('--key-file', dest='key_file',
                               default=None, help=SUPPRESS_HELP)
        self.parser.add_option_group(credentials)

    def find_command(self, command):
        """
        Look up a command by name.
        @type command: str
        @rtype: pulp.client.core.base.BaseCore instance or None
        @return: object corresponding to command on success, None on failure
        """
        if command not in self.commands:
            return None
        return self.commands[command]

    def main(self, args=sys.argv[1:]):
        """
        Run this command.
        @type args: list of str's
        @param args: command line arguments
        """
        self.setup_parser()
        opts, args = self.parser.parse_args(args)
        if not args:
            self.parser.error(_('no command given: please see --help'))
        command = self.find_command(args[0])
        if command is None:
            self.parser.error(_('invalid command: please see --help'))
        command.setup_credentials(opts.username, opts.password,
                                  opts.cert_file, opts.key_file)
        command.main(args[1:])

