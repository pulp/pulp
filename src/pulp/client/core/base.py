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
from optparse import OptionParser, SUPPRESS_USAGE

from pulp.client import auth_utils

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
    Exit with a code and optional message(s). Saved a few lines of code.
    @type code: int
    @param code: code to return
    @type msgs: str or list or tuple of str's
    @param msgs: messages to display
    """
    assert msgs is None or isinstance(msgs, (basestring, list, tuple))
    if msgs:
        if isinstance(msgs, basestring):
            msgs = (msgs,)
        for msg in msgs:
            print >> sys.stderr, msg
    sys.exit(code)

systemExit = system_exit

# core module base class -----------------------------------------------------

class BaseCore(object):

    _default_actions = {}

    def __init__(self, name, actions=_default_actions):
        self.name = name
        self.actions = actions
        # options and arguments
        self.parser = OptionParser(usage=self.usage())
        self.parser.disable_interspersed_args()
        # credentials
        self.username = None
        self.password = None
        self.cert_file = None
        self.key_file = None

    # attributes

    def usage(self):
        lines = ['Usage: %s <action> <options>' % self.name,
                 'Supported Actions:']
        for name, description in sorted(list(self.actions.items())):
            lines.append('\t%-14s %-25s' % (name, description))
        return '\n'.join(lines)

    def short_description(self):
        raise NotImplementedError('Base class method called')

    def long_description(self):
        raise NotImplementedError('Base class method called')

    def setup_credentials(self, username, password, cert_file, key_file):
        self.username = username
        self.password = password
        files = auth_utils.admin_cert_paths()
        cert_file = cert_file or files[0]
        key_file = key_file or files[1]
        if os.access(cert_file, os.F_OK | os.R_OK):
            self.cert_file = cert_file
        else:
            self.parser.error(_('error: cannot read cert file: %s') % cert_file)
        if os.access(key_file, os.F_OK | os.R_OK):
            self.key_file = key_file
        else:
            self.parser.error(_('error: cannot read key file: %s') % key_file)

    # main

    def get_action(self, name):
        if name not in self.actions and not hasattr(self, name):
            return None
        return getattr(self, name)

    def main(self, args):
        if not args:
            self.parser.error(_('no action given: please see --help'))
        self.parser.parse_args(args)
        action = self.get_action(args[0])
        action.set_state(username=self.username, password=self.password,
                         cert_file=self.cert_file, key_file=self.key_file)
        if action is None:
            self.parser.error(_('invalid action: please see --help'))
        action.main(args[1:])

# base action class -------------------------------------------------

class Action(object):

    def __init__(self, name):
        self.name = name
        self.parser = OptionParser(usage=SUPPRESS_USAGE)
        self.opts = None
        self.args = None

    def set_state(self, **kwargs):
        self.__dict__.update(kwargs)

    def setup_parser(self):
        pass

    def parse_args(self):
        return self.parser.parse_args(self.args)

    def setup_server(self):
        raise NotImplementedError('Base class method called')

    def run(self):
        raise NotImplementedError('Base class method called')

    def main(self, args):
        self.setup_parser()
        self.opts, self.args = self.parse_args(args)
        self.setup_server()
        self.run()
