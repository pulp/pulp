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

from gettext import gettext as _
from optparse import OptionParser

from pulp.client.config import Config
from pulp.client.connection import RestlibException
from pulp.client.logutil import getLogger


_cfg = Config()
_log = getLogger(__name__)

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
        action.main(args[1:])

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

    def setup_parser(self):
        """
        Add custom options to the parser
        @note: this method should be overridden to add per-action options
        """
        pass

    def setup_connections(self):
        """
        Setup the connections required by this action
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
        self.setup_parser()
        self.opts, self.args = self.parser.parse_args(args)
        try:
            self.setup_connections()
            self.run()
        except RestlibException, re:
            _log.error("error: %s" % re)
            system_exit(re.code, _('error: operation failed: ') + re.msg)
        except Exception, e:
            _log.error("error: %s" % e)
            raise
        finally:
            print ''
