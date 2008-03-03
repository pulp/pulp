"""
Pulp Command Line Interface

Copyright 2008, Red Hat, Inc
Devan Goodwin <dgoodwin@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import sys
from pulp.cli.modules import *

from optparse import OptionParser

MODULES = {
    "repo": RepoModule()
}

class PulpCommandLine:
    """
    Main entry point for the Pulp command line interface.
    """

    def main(self, argv):
        """ Main CLI entry point """

        # We expect at least one argument representing the module name.
        # Otherwise display help info.
        if len(argv) < 2:
            self.help()

        module_name = argv[1]
        print "Module: %s" % module_name
        if not MODULES.has_key(module_name):
            print "ERROR: Unknown module: %s" % module_name
            self.help()

        parser = OptionParser()
        module = MODULES[module_name]
        module.add_options(parser)

        (options, args) = parser.parse_args(argv[2:])
        module.run(options)

    def help(self):
        """ Display help info to the user. """
        # TODO
        print "Help!"
        sys.exit(1)
