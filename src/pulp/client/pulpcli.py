#
# Pulp client utility
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
import logging
import sys
import pkgutil
import pulp.client.utils as utils
from pulp.client.logutil import getLogger

import pulp.client.core as core

import gettext
_ = gettext.gettext
log = getLogger(__name__)

class PulpCore:
    """
     A top level class to load modules dynamically from pulp.client.cores package
    """
    def __init__(self):
        self.cli_cores = {}
        self.args = utils.findSysvArgs(sys.argv)
        if len(self.args) > 1:
            cls = self._load_core(self.args[1])
            if cls not in self._load_all_cores():
                print ("Invalid Command. Please see --help for valid modules")
                sys.exit(0)
            self.cli_cores[self.args[1]] = cls()
        else:
            for cls in self._load_all_cores():
                cmd = cls()
                if cmd.name != "cli":
                    self.cli_cores[cmd.name] = cmd


    def _add_core(self, cmd):
        self.cli_cores[cmd.name] = cmd

    def _load_core(self, core):
        #name = "core_" + core
        name = core
        mod = __import__('pulp.client.core.', globals(), locals(), [name])
        try:
            submod = getattr(mod, name)
        except AttributeError:
            return None
        return getattr(submod, core)

    def _load_all_cores(self):
        pkgpth = os.path.dirname(core.__file__)
        modules = [name for _, name, _ in pkgutil.iter_modules([pkgpth])
                   if not name.startswith("_")]
                   #if name.startswith("core_")]
        cls = []
        for name in modules:
            mod = __import__('pulp.client.core.', globals(), locals(), [name])
            submod = getattr(mod, name)
            #cls.append(getattr(submod, name.split("_")[-1]))
            cls.append(getattr(submod, name))
        return cls

    def _usage(self):
        print "\nUsage: %s -u <username> -p <password> MODULENAME --help\n" % os.path.basename(sys.argv[0])
        print "Supported modules:\n"
        items = self.cli_cores.items()
        for (name, cmd) in items:
            print("\t%-14s %-25s" % (name, cmd.shortdesc))
        print("")

    def _find_best_match(self, args):
        possiblecmd = utils.findSysvArgs(args)
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

        cmd = self._find_best_match(sys.argv[1:])
        if not cmd:
            self._usage()
            sys.exit(0)

        cmd.main()

if __name__ == "__main__":
    # TODO: Make logging configurable
    logging.root.addHandler(logging.StreamHandler())
    logging.root.setLevel(logging.ERROR)
    PulpCore().main()
