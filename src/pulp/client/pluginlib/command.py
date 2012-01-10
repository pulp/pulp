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
import time
from gettext import gettext as _
from optparse import OptionParser
from M2Crypto import SSL

from pulp.client.lib.config import Config
from pulp.client.lib.utils import system_exit
from pulp.client.lib.logutil import getLogger
from pulp.client.api.server import ServerRequestError, NoCredentialsError


_log = getLogger(__name__)

# base command class ----------------------------------------------------------

class Command(object):
    """
    Command class representing a pulp cli command
    @cvar name: Command name
    @type name: str
    @cvar description: Command description
    @type description: str
    @cvar actions: List of Action classes that this command provides
    @type actions: list
    @ivar parser: optparse.OptionParser instance
    @ivar username: username credential
    @ivar password: password credential
    @ivar cert_file: certificate file credential
    @ivar key_file: private key file credential
    """

    name = "name"
    description = "description"
    actions = []

    def __init__(self, cfg):
        """
        @type actions: None or tuple/list of str's
        @param actoins: list of actions to expose, uses _default_actions if None
        """
        self.cfg = cfg
        self.cli = None
        self.parser = OptionParser()
        self.parser.disable_interspersed_args()
        self._actions = {}
        self._action_order = []
        self.register_actions()

    def __getattr__(self, attr):
        """
        Expose the commands actions as attributes on the instance.
        """
        return self._actions[attr]

    @property
    def usage(self):
        """
        Return a string showing the command's usage
        """
        lines = ['%s <options> %s <action> <options>' %
                 (self.cli.name, self.name),
                 'Supported Actions:']
        for name in self._action_order:
            action = self._actions[name]
            lines.append('\t%-14s %-25s' % (name, action.description))
        return '\n'.join(lines)

    @property
    def description(self):
        """
        Return a string showing the command's description
        """
        return _('no description available')

    def add_action(self, name, action):
        """
        Add an action to this command
        @note: actions are displayed in the order they are added
        @type name: str
        @param name: name to associate with the action
        @type action: L{Action} instance
        @param action: action to add
        """
        action.cmd = self
        action.name = name
        self._action_order.append(name)
        self._actions[name] = action

    def register_actions(self):
        """
        Register the actions for this command by instantiating each action and
        adding it to the exposed actions on this command.
        """
        for action in self.actions:
            self.add_action(action.name, action(self.cfg))

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
        self.parser.set_usage(self.usage)
        if not args:
            self.parser.error(_('no action given: please see --help'))
        self.parser.parse_args(args)
        action = self._actions.get(args[0], None)
        if action is None:
            self.parser.error(_('invalid action: please see --help'))
        action.main(args[1:])

# base action class -----------------------------------------------------------

class Action(object):
    """
    Action class representing a single action for a cli command
    @ivar name: action's name
    @ivar parser: optparse.OptionParser instance
    @ivar opts: options returned from parsing command line
    @ivar args: arguments returned from parsing command line
    """

    name = "name"
    description = "description"

    def __init__(self, cfg):
        self.cfg = cfg
        self.cmd = None
        self.parser = OptionParser()
        self.opts = None
        self.args = None

    @property
    def usage(self):
        """
        Return a string for this action's usage
        """
        return 'Usage: %s <options> %s %s <options>' % \
                (self.cmd.cli.name, self.cmd.name, self.name)

    @property
    def description(self):
        """
        Return a string for this action's description
        """
        return _('no description available')

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
            self.parser.error(_('Option %s is required; please see --help') % flag)
        if value is "":
            self.parser.error(_('%s option requires an argument') % flag)
        if isinstance(value, (list, tuple)) and not value:
            self.parser.error(_('At least one %s option is required; please see --help') % flag)
        return value

    def setup_parser(self):
        """
        Add custom options to the parser
        @note: this method should be overridden to add per-action options
        """
        pass

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
        self.parser.set_usage(self.usage)
        self.setup_parser()
        self.opts, self.args = self.parser.parse_args(args)
        try:
            self.run()
        except SSL.Checker.WrongHost, wh:
            print _("ERROR: The server hostname you have configured in %s "
                "does not match the" % self.cfg.FILE_PATH)
            print _("hostname returned from the Pulp server you are connecting to.  ")
            print ""
            print _("You have: [%s] configured but got: [%s] from the server.") % (wh.expectedHost, wh.actualHost)
            print ""
            print _("Please correct the host in the %s file" %
                self.cfg.FILE_PATH)
            sys.exit(1)
        except NoCredentialsError, nce:
            _log.error("error: %s" % nce)
            system_exit(nce.args[0], _('operation failed: ') + nce.args[1])
        except ServerRequestError, re:
            _log.error("error: %s" % re)
            system_exit(re.args[0], _('operation failed: ') + re.args[1])
        except KeyboardInterrupt:
            system_exit(os.EX_NOUSER)
        except Exception, e:
            _log.error("error: %s" % e)
            raise
        print ''
