#!/usr/bin/python
#
# Pulp Registration and subscription module
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

import sys
import os.path
from pulptools.core.basecore import BaseCore, systemExit
from pulptools.connection import RepoConnection, ConsumerConnection, RestlibException
from pulptools.connection import ConsumerGroupConnection
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
        usage = "package [OPTIONS]"
        shortdesc = "package specific actions to pulp server."
        desc = ""
        self.name = "package"
        self.actions = {"info"          : "lookup information for a package", 
                        "install"       : "Schedule a package Install", }
        BaseCore.__init__(self, "package", usage, shortdesc, desc)
        self.pconn = None
        self.cconn = None
        
    def load_server(self):
        self.pconn = RepoConnection(host=CFG.server.host or "localhost", 
                                    port=8811,  username=self.username, 
                                    password=self.password)
        self.cconn = ConsumerConnection(host=CFG.server.host or "localhost", 
                                        port=8811, username=self.username, 
                                        password=self.password)
        self.cgconn = ConsumerGroupConnection(host=CFG.server.host or "localhost", 
                                              port=8811, username=self.username, 
                                              password=self.password)

    def generate_options(self):
        self.action = self._get_action()
        if self.action == "info":
            usage = "package info [OPTIONS]"
            self.setup_option_parser(usage, "", True)
            self.parser.add_option("-n", "--name", dest="name",
                           help="package name to lookup")
            self.parser.add_option("--repoid", dest="repoid",
                           help="Repository Label") 
        if self.action == "install":
            usage = "package install [OPTIONS]"
            self.setup_option_parser(usage, "", True)
            self.parser.add_option("-n", "--name", action="append", dest="pnames",
                           help="Packages to be installed. \
                           To specify multiple packages use multiple -p")
            self.parser.add_option("--consumerid", dest="consumerid",
                           help="Consumer Id")
            self.parser.add_option("--consumergroupid", dest="consumergroupid",
                           help="Consumer Group Id")

    def _do_core(self):
        if self.action == "info":
            self._info()
        if self.action == "install":
            self._install()

    def _info(self):
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
        if not self.options.consumerid and not self.options.consumergroupid:
            print("Please specify a consumer or a consumer group to install the package")
            sys.exit(0)
        if not self.options.pnames:
            print("Nothing to Upload.")
            sys.exit(0)
        try:
            if self.options.consumergroupid:
                print self.cgconn.installpackages(self.options.consumergroupid, self.options.pnames)
            else:     
                print self.cconn.installpackages(self.options.consumerid, self.options.pnames)
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise    
        