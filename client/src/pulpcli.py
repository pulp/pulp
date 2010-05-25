#
# Pulp client utility
# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: Pradeep Kilambi <pkilambi@redhat.com>
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
import connection
from optparse import OptionParser
from logutil import getLogger
import gettext
_ = gettext.gettext

log = getLogger(__name__)

class BaseCore(object):
    """ Base class for all sub-calls. """
    def __init__(self, name="cli", usage=None, shortdesc=None,
            description=None):
        self.shortdesc = shortdesc
        if shortdesc is not None and description is None:
            description = shortdesc
        self.debug = 0
        self.parser = OptionParser(usage=usage, description=description)
        self._add_common_options()
        self.name = name

    def _add_common_options(self):
        """ Common options to all modules. """
        pass

    def _do_core(self):
        pass

    def main(self):
        (self.options, self.args) = self.parser.parse_args()
        self.args = self.args[1:]
        self._do_core()

class RepoCore(BaseCore):
    def __init__(self):
        usage = "usage: %prog repository [OPTIONS]"
        shortdesc = "Create a repository on your pulp server."
        desc = "register"

        BaseCore.__init__(self, "repository", usage, shortdesc, desc)

        self.username = None
        self.password = None
        self.cp = connection.PulpConnection(host="localhost", port=8811)
        self.parser.add_option("--create", dest="create",
                               help="Create a Repository")

    def _validate_options(self):
        pass

    def _do_core(self):
        """
        Executes the core.
        """
        self._validate_options()
        pass

class CLI:
    """
     This is the main cli class that does command parsing like rho and matches
     the the right commands
    """
    def __init__(self):
        self.cli_cores = {}
        for clazz in [ RepoCore]:
            cmd = clazz()
            # ignore the base class
            if cmd.name != "cli":
                self.cli_cores[cmd.name] = cmd 


    def _add_core(self, cmd):
        self.cli_cores[cmd.name] = cmd

    def _usage(self):
        print "\nUsage: %s [options] MODULENAME --help\n" % os.path.basename(sys.argv[0])
        print "Supported modules:\n"

        # want the output sorted
        items = self.cli_cores.items()
        items.sort()
        for (name, cmd) in items:
            print("\t%-14s %-25s" % (name, cmd.shortdesc))
            #print(" %-25s" % cmd.parser.print_help())
        print("")

    def _find_best_match(self, args):
        possiblecmd = []
        for arg in args[1:]:
            if not arg.startswith("-"):
                possiblecmd.append(arg)

        if not possiblecmd:
            return None

        cmd = None
        key = " ".join(possiblecmd)
        if self.cli_cores.has_key(" ".join(possiblecmd)):
            cmd = self.cli_cores[key]

        i = -1
        while cmd == None:
            key = " ".join(possiblecmd[:i])
            if key is None or key == "":
                break

            if self.cli_cores.has_key(key):
                cmd = self.cli_cores[key]
            i -= 1

        return cmd

    def main(self):
        if len(sys.argv) < 2 or not self._find_best_match(sys.argv):
            self._usage()
            sys.exit(0)

        cmd = self._find_best_match(sys.argv)
        if not cmd:
            self._usage()
            sys.exit(0)

        cmd.main()

def systemExit(code, msgs=None):
    "Exit with a code and optional message(s). Saved a few lines of code."

    if msgs:
        if type(msgs) not in [type([]), type(())]:
            msgs = (msgs, )
        for msg in msgs:
            sys.stderr.write(unicode(msg).encode("utf-8") + '\n')
    sys.exit(code)

if __name__ == "__main__":
    CLI().main()
