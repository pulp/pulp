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

        # If only one argument, display the help for just that module:
        if len(argv) == 2:
            self.help(module_name)

        (parser, module) = self.__generate_module_option_parser(module_name)

        (options, args) = parser.parse_args(argv[2:])
        module.run(options)

    def __generate_module_option_parser(self, module_name):
        """ 
        Generate an OptionParser for the given module. 

        Does not actually call the parse_args method.

        Return a tuple of option parser and CLI module.
        """
        usage = "usage: %prog " + module_name + " [options]"
        if not MODULES.has_key(module_name):
            print "ERROR: Unknown module: %s\n" % module_name
            self.help()

        parser = OptionParser()
        module = MODULES[module_name]
        module.add_options(parser)
        return (parser, module)


    def help(self, module_name=None):
        """ 
        Display help info to the user. 

        Constructs an OptionParser for each module and calls it's print_help
        method.
        """
        modules_to_print = MODULES.keys()
        if module_name != None:
            modules_to_print = [module_name]

        for module_name in modules_to_print:
            parser = self.__generate_module_option_parser(module_name)[0]
            parser.print_help()
            if len(modules_to_print) > 1:
                print "\n\n"
        sys.exit(1)
