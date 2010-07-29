#
# Base class inherited by all cores
#
# Copyright (c) 2010 Red Hat, Inc.
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
#

import os
import sys
from optparse import OptionParser

class BaseCore(object):
    """ Base class for all sub-calls. """
    def __init__(self, name="cli", usage=None, shortdesc=None,
            description=None):
        self.shortdesc = shortdesc
        if shortdesc is not None and description is None:
            description = shortdesc
        self.debug = 0
        self.usage = "usage: %prog --auth=<login:password> " + usage
        self.parser = OptionParser(usage=self.usage, description=description)
        self._add_common_options()
        self.name = name
        (self.options, self.args) = self.parser.parse_args()
        if not self.options.auth:
            print("auth required. Try --help")
            sys.exit(1)
        self.args = self.args[1:]

    def _add_common_options(self):
        """ Common options to all modules. """
        help = "<REQUIRED> username:password combination for access to Pulp."  
        help = help + "Default user admin is included with base install."
        self.parser.add_option("--auth", dest="auth",
                       help=help)

    def _get_action(self):
        """ Validate the arguments passed in and determine what action to take """
        action = None
        possiblecmd = []
        for arg in sys.argv[1:]:
            if not arg.startswith("-"):
                possiblecmd.append(arg)
        if len(possiblecmd) > 1:
            action = possiblecmd[1]
        elif len(possiblecmd) == 1 and possiblecmd[0] == self.name:
            self._usage()
            sys.exit(0)
        else:
            return None 
        if action not in self.actions.keys():
            self._usage()
            sys.exit(0)
        
        return action 
    
    def _usage(self):
        print self.usage.replace("%prog", os.path.basename(sys.argv[0]))
        print "Supported Actions:\n"
        items = self.actions.items()
        items.sort()
        for (name, cmd) in items:
            print("\t%-14s %-25s" % (name, cmd))
        print("")

    def _do_core(self):
        pass

    def main(self):
        self._do_core()

def systemExit(code, msgs=None):
    "Exit with a code and optional message(s). Saved a few lines of code."

    if msgs:
        if type(msgs) not in [type([]), type(())]:
            msgs = (msgs, )
        for msg in msgs:
            sys.stderr.write(unicode(msg).encode("utf-8") + '\n')
    sys.exit(code)