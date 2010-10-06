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
from optparse import OptionParser

from pulp.client import credentials
from pulp.client.config import Config
from pulp.client.connection import RestlibException
from pulp.client.logutil import getLogger


_cfg = Config()
_log = getLogger(__name__)

# output formatting -----------------------------------------------------------

_header_width = 45
_header_border = '+------------------------------------------+'

def print_header(*lines):
    """
    Print a fancy header to stdout.
    @type lines: list str's
    @param lines: headers, passed in as positional arguments, to be displayed
    """
    padding = 0
    print _header_border
    for line in lines:
        if len(line) < _header_width:
            padding = ((_header_width - len(line)) / 2) - 1
        print ' ' * padding, line
    print _header_border

# system exit -----------------------------------------------------------------

def system_exit(code, msgs=None):
    """
    Exit with a code and optional message(s). Saves a few lines of code.
    @type code: int
    @param code: code to return
    @type msgs: str or list or tuple of str's
    @param msgs: messages to display
    """
    assert msgs is None or isinstance(msgs, (basestring, list, tuple))
    if msgs:
        if isinstance(msgs, basestring):
            msgs = (msgs,)
        out = sys.stdout if code == os.EX_OK else sys.stderr
        for msg in msgs:
            print >> out, msg
    sys.exit(code)

systemExit = system_exit

# base command class ----------------------------------------------------------

class Command(object):
    """
    Command class representing a pulp cli command
    @cvar name: command's name
    @cvar description: command's description
    @cvar _default_actions: tuple of action names to expose by default
    @ivar actions: list of actions to expose
    @ivar parse: optparse.OptionParser instance
    @ivar username: username credential
    @ivar password: password credential
    @ivar cert_file: certificate file credential
    @ivar key_file: private key file credential
    """

    name = None
    description = None
    _default_actions = ()

    def __init__(self, actions=None):
        """
        @type actions: None or tuple/list of str's
        @param actoins: list of actions to expose, uses _default_actions if None
        """
        self.actions = actions if actions is not None else self._default_actions
        self.parser = OptionParser()
        self.parser.disable_interspersed_args()

    # attributes

    def usage(self):
        """
        Return a string showing the command's usage
        """
        lines = ['Usage: ... %s <action> <options>' % self.name,
                 'Supported Actions:']
        for name in self.actions:
            action = getattr(self, name, None)
            description = 'no description' if action is None else action.description
            lines.append('\t%-14s %-25s' % (name, description))
        return '\n'.join(lines)

    # main

    def get_action(self, name):
        """
        Get an action class instance, given the name
        @type name: str
        @param name: action name
        @rtype: L{Action} instance or None
        @return: L{Action} instance corresponding to the action name on success,
                 None on failure
        """
        if name not in self.actions or not hasattr(self, name):
            return None
        return getattr(self, name)

    def main(self, args):
        """
        Main execution of a pulp cli command
        This method parses options sent to the command itself,
        looks up the corresponding action,
        and calls that action's main()
        @warning: this method should only be overridden with care
        @type args: list of str's
        @param args: command line arguments to parse
        """
        self.parser.set_usage(self.usage())
        if not args:
            self.parser.error(_('no action given: please see --help'))
        self.parser.parse_args(args)
        action = self.get_action(args[0])
        if action is None:
            self.parser.error(_('invalid action: please see --help'))
        action.main(args[1:], self.setup_action_connections)

# base action class -----------------------------------------------------------

class Action(object):
    """
    Action class representing a single action for a cli command
    @cvar name: action's name
    @cvar description: action's description
    @ivar parser: optparse.OptionParser instance
    @ivar opts: options returned from parsing command line
    @ivar args: arguments returned from parsing command line
    """

    name = None
    description = None

    def __init__(self):
        self.parser = OptionParser(usage=self.usage())
        self.opts = None
        self.args = None

    def usage(self):
        """
        Return a string for this action's usage
        """
        return 'Usage: ... %s <options>' % self.name

    def get_required_option(self, opt, flag=None):
        """
        Get an option from opts that is required, else exit in a consistent way
        @type opt: str
        @param opt: name of option to get
        @type flag: None or str
        @param flag: option flag as it appears on the command, defaults to
                     '--' + opt is set to None
        @return: value of the option on success
        """
        flag = flag or '--' + opt
        value = getattr(self.opts, opt, None)
        if value is None:
            self.parser.error(_('option %s is required; please see --help') % flag)
        return value

    def connections(self):
        """
        Get the connection classes required by this action, keyed by attribute
        @rtype: dict of str: Connection class
        @return: dictionary of Connection classes, keyed by the name of the
                 attribute they will be set to
        """
        return {}

    def setup_parser(self):
        """
        Add custom options to the parser
        @note: this method should be overridden to add per-action options
        """
        pass

    def _get_credentials(self):
        """
        Get and verify pulp credentials
        @rtype: tuple of None(s) and str's
        @return: username, password, cert file path, key file path
        """
        # a provided username and password will override cert and key files
        username, password = credentials.get_username_password()
        cert_file = key_file = None
        if None in (username, password):
            username = password = None
            if None in credentials.get_cert_key_files():
                credentials.set_local_cert_key_files()
            cert_file, key_file = credentials.get_cert_key_files()
        # make sure there is one valid set of credentials
        if None in (username, password) and None in (cert_file, key_file):
            system_exit(os.EX_USAGE, _('no pulp credentials found'))
        # check to see if we can access the cert and key files
        if cert_file is not None and not os.access(cert_file, os.F_OK | os.R_OK):
            system_exit(os.EX_CONFIG, _('cannot read cert file: %s') % cert_file)
        if key_file is not None and not os.access(key_file, os.F_OK | os.R_OK):
            system_exit(os.EX_CONFIG, _('cannot read key file: %s') % cert_file)
        return (username, password, cert_file, key_file)

    def _setup_connections(self):
        """
        Setup connections for the action
        @warning: this method should only be overridden with care
        """
        username, password, cert_file, key_file = self._get_credentials()
        connections = self.connections()
        for name, cls in connections.items():
            connection = cls(host=_cfg.server.host or 'localhost',
                             port=_cfg.server.port or 443,
                             username=username,
                             password=password,
                             cert_file=cert_file,
                             key_file=key_file)
            setattr(self, name, connection)

    def run(self):
        """
        Action's functionality
        @note: override this method to implement the actoin's functionality
        @raise NotImplementedError: if this method is not overridden
        """
        raise NotImplementedError('Base class method called')

    def main(self, args):
        """
        Main execution of the action
        This method setups up the parser, parses the arguments, and calls run()
        in a try/except block, handling RestlibExceptions and general errors
        @warning: this method should only be overridden with care
        """
        self.setup_parser()
        self.opts, self.args = self.parser.parse_args(args)
        try:
            self._setup_connections()
            self.run()
        except RestlibException, re:
            _log.error("error: %s" % re)
            system_exit(re.code, _('error: operation failed: ') + re.msg)
        except Exception, e:
            _log.error("error: %s" % e)
            raise
        finally:
            print ''
