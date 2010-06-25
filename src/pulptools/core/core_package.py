#!/usr/bin/python
#
# Pulp Registration and subscription module
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

import sys
import os.path
from pulptools.core.basecore import BaseCore, systemExit
from pulptools.connection import RepoConnection, ConsumerConnection, RestlibException
from pulptools.logutil import getLogger
from pulptools.config import Config
log = getLogger(__name__)
CFG = Config()
#TODO: move this to config
CONSUMERID = "/etc/pulp/consumer"
import gettext
_ = gettext.gettext

class package(BaseCore):
    def __init__(self):
        usage = "usage: %prog package [OPTIONS]"
        shortdesc = "package specific actions to pulp server."
        desc = ""

        BaseCore.__init__(self, "package", usage, shortdesc, desc)
        self.actions = {"info"          : "lookup information for a package", 
                        "install"       : "Schedule a package Install", }
        self.name = "package"
        self.username = None
        self.password = None
        self.pconn = None
        self.cconn = None
        self.load_server()
        self.generate_options()
        
    def load_server(self):
        self.pconn = RepoConnection(host=CFG.server.host or "localhost", port=8811)
        self.cconn = ConsumerConnection(host=CFG.server.host or "localhost", port=8811)

    def generate_options(self):
        possiblecmd = []

        for arg in sys.argv[1:]:
            if not arg.startswith("-"):
                possiblecmd.append(arg)
        self.action = None
        if len(possiblecmd) > 1:
            self.action = possiblecmd[1]
        elif len(possiblecmd) == 1 and possiblecmd[0] == self.name:
            self._usage()
            sys.exit(0)
        else:
            return
        if self.action not in self.actions.keys():
            self._usage()
            sys.exit(0)
        if self.action == "info":
            usage = "usage: %prog package info [OPTIONS]"
            BaseCore.__init__(self, "package info", usage, "", "")
            self.parser.add_option("-p", "--pkgname", dest="name",
                           help="Repository Label")
            self.parser.add_option("--repoid", dest="repoid",
                           help="Repository Label")
        if self.action == "install":
            usage = "usage: %prog package install [OPTIONS]"
            BaseCore.__init__(self, "package install", usage, "", "")
            self.parser.add_option("-p", "--pkgname", action="append", dest="pnames",
                           help="Packages to install on a given consumer. \
                           To specify multiple packages use multiple -p")
            self.parser.add_option("--consumerid", dest="consumerid",
                           help="Consumer Id")

    def _validate_options(self):
        pass

    def _usage(self):
        print "\nUsage: %s MODULENAME ACTION [options] --help\n" % os.path.basename(sys.argv[0])
        print "Supported Actions:\n"
        items = self.actions.items()
        #items.sort()
        for (name, cmd) in items:
            print("\t%-14s %-25s" % (name, cmd))
        print("")

    def _do_core(self):
        self._validate_options()
        if self.action == "info":
            self._info()
        if self.action == "install":
            self._install()

    def _info(self):
        (self.options, self.args) = self.parser.parse_args()
        if not self.options.name:
            print("Please specify the pkg name to lookup")
            sys.exit(0)
        if not self.options.repoid:
            print("Please specify the repo")
            sys.exit(0)
        try:
            pkg = self.pconn.get_package(self.options.repoid, self.options.name)
            if not pkg:
                print("Package [%s] not found in repo [%s]" % (self.options.name, self.options.repoid))
                sys.exit(-1)
            print """+-------------------------------------------+\n    Package Information \n+-------------------------------------------+"""
            for key, value in pkg.items():
                print """%s:                \t%-25s""" % (key, value)
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise
    
    def _install(self):
        (self.options, self.args) = self.parser.parse_args()
        if not self.options.consumerid:
            print("Please specify a consumer to install the package")
            sys.exit(0)
        if not self.options.pnames:
            print("Nothing to Upload.")
            sys.exit(0)
        try:
            print self.cconn.installpackages(self.options.consumerid, self.options.pnames)
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise    
        
def _sub_dict(datadict, subkeys, default=None) :
    return dict([ (k, datadict.get(k, default) ) for k in subkeys ] )
