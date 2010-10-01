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

from pulp.client import auth_utils
from pulp.client.config import Config
from pulp.client.connection import RestlibException
from pulp.client.logutil import getLogger


_cfg = Config()
_log = getLogger(__name__)

# output formatting -----------------------------------------------------------

_header_width = 45
_header_border = '+------------------------------------------+'

def print_header(*lines):
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

    name = None
    description = None
    _default_actions = ()

    def __init__(self, actions=None, action_state={}):
        self.actions = actions if actions is not None else self._default_actions
        self.action_state = action_state
        # options and arguments
        self.parser = OptionParser()
        self.parser.disable_interspersed_args()
        # credentials
        self.username = None
        self.password = None
        self.cert_file = None
        self.key_file = None

    # attributes

    def usage(self):
        lines = ['Usage: ... %s <action> <options>' % self.name,
                 'Supported Actions:']
        for name in self.actions:
            action = getattr(self, name, None)
            description = 'no description' if action is None else action.description
            lines.append('\t%-14s %-25s' % (name, description))
        return '\n'.join(lines)

    def setup_credentials(self, username=None, password=None,
                          cert_file=None, key_file=None):
        self.username = username
        self.password = password
        # passed in username and password override on-disk credentials
        if username and password:
            return
        files = auth_utils.admin_cert_paths()
        self.cert_file = cert_file or files[0]
        self.key_file = key_file or files[1]

    # main

    def get_action(self, name):
        if name not in self.actions or not hasattr(self, name):
            return None
        return getattr(self, name)

    def setup_action_connections(self, action):
        connections = action.connections()
        cert_file = self.cert_file
        key_file = self.key_file
        if cert_file is not None and not os.access(cert_file, os.F_OK | os.R_OK):
            system_exit(os.EX_CONFIG, _('cannot read cert file: %s') % cert_file)
        if key_file is not None and not os.access(key_file, os.F_OK | os.R_OK):
            system_exit(os.EX_CONFIG, _('cannot read key file: %s') % cert_file)
        for name, cls in connections.items():
            connection = cls(host=_cfg.server.host or 'localhost',
                             port=_cfg.server.port or 443,
                             username=self.username,
                             password=self.password,
                             cert_file=cert_file,
                             key_file=key_file)
            setattr(action, name, connection)

    def main(self, args):
        self.parser.set_usage(self.usage())
        if not args:
            self.parser.error(_('no action given: please see --help'))
        self.parser.parse_args(args)
        action = self.get_action(args[0])
        if action is None:
            self.parser.error(_('invalid action: please see --help'))
        if self.action_state:
            action.set_state(**self.action_state)
        action.main(args[1:], self.setup_action_connections)

# base action class -----------------------------------------------------------

class Action(object):

    name = None
    description = None

    def __init__(self):
        self.parser = OptionParser(usage=self.usage())
        self.opts = None
        self.args = None

    def set_state(self, **kwargs):
        self.__dict__.update(kwargs)

    def usage(self):
        return 'Usage: ... %s <options>' % self.name

    def get_required_option(self, opt, arg=None):
        arg = arg or '--' + opt
        value = getattr(self.opts, opt, None)
        if value is None:
            self.parser.error(_('option %s is required; please see --help') % arg)
        return value

    def connections(self):
        return {}

    def setup_parser(self):
        pass

    def parse_args(self, args):
        return self.parser.parse_args(args)

    def run(self):
        raise NotImplementedError('Base class method called')

    def main(self, args, setup_connections):
        self.setup_parser()
        self.opts, self.args = self.parse_args(args)
        try:
            setup_connections(self)
            self.run()
        except RestlibException, re:
            _log.error("error: %s" % re)
            system_exit(re.code, _('error: operation failed: ') + re.msg)
        except Exception, e:
            _log.error("error: %s" % e)
            raise
