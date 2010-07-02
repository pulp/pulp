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

class packagegroup(BaseCore):
    def __init__(self):
        usage = "usage: %prog packagegroup [OPTIONS]"
        shortdesc = "packagegroup specific actions to pulp server."
        desc = ""

        BaseCore.__init__(self, "packagegroup", usage, shortdesc, desc)
        self.actions = {"add"           : "add package(s) to an existing packagegroup",
                        "create"        : "create a packagroup",
                        "info"          : "lookup information for a packagegroup",
                        "install"       : "Schedule a packagegroup Install",
                        "list"          : "list available packagegroups",
                        "remove"        : "remove package(s) from an existing packagegroup"
                        }
        self.name = "packagegroup"
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
            usage = "usage: %prog packagegroup info [OPTIONS]"
            BaseCore.__init__(self, "packagegroup info", usage, "", "")
            self.parser.add_option("--groupid", dest="groupid",
                           help="package name to lookup")
            self.parser.add_option("--repoid", dest="repoid",
                           help="Repository Label")
        if self.action == "install":
            usage = "usage: %prog packagegroup install [OPTIONS]"
            BaseCore.__init__(self, "packagegroup install", usage, "", "")
            self.parser.add_option("-p", "--pkgname", action="append", dest="pnames",
                           help="Packages to install on a given consumer. \
                           To specify multiple packages use multiple -p")
            self.parser.add_option("--consumerid", dest="consumerid",
                           help="Consumer Id")
        if self.action == "list":
            usage = "usage: %prog packagegroup list [OPTIONS]"
            BaseCore.__init__(self, "packagegroup list", usage, "", "")
            self.parser.add_option("--repoid", dest="repoid",
                           help="Repository Label")
        if self.action == "add":
            usage = "usage: %prog packagegroup add [OPTIONS]"
            BaseCore.__init__(self, "packagegroup add", usage, "", "")
            self.parser.add_option("--repoid", dest="repoid",
                            help="Repository Label")
            self.parser.add_option("--groupid", dest="groupid",
                            help="Group id")
            self.parser.add_option("--name", dest="pkgname",
                            help="Package name (or list of names")
            self.parser.add_option("--type", dest="grouptype",
                            help="Type of list to add package to, example 'mandatory', 'optional', 'default'",
                            default="default")
        if self.action == "create":
            usage = "usage: %prog packagegroup create [OPTIONS]"
            BaseCore.__init__(self, "packagegroup create", usage, "", "")
            self.parser.add_option("--repoid", dest="repoid",
                           help="Repository Label")
            self.parser.add_option("--groupid", dest="groupid",
                            help="Group id")
        if self.action == "remove":
            usage = "usage: %prog packagegroup remove [OPTIONS]"
            BaseCore.__init__(self, "packagegroup remove", usage, "", "")
            self.parser.add_option("--repoid", dest="repoid",
                            help="Repository Label")
            self.parser.add_option("--groupid", dest="groupid",
                            help="Group id")
            self.parser.add_option("--name", dest="pkgname",
                            help="Package name (or list of names")
            self.parser.add_option("--type", dest="grouptype",
                            help="Type of list to remove package from, example 'mandatory', 'optional', 'default'",
                            default="default")

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
        if self.action == "list":
            self._list()
        if self.action == "add":
            self._add()
        if self.action == "create":
            self._create()
        if self.action == "remove":
            self._remove()

    def _list(self):
        (self.options, self.args) = self.parser.parse_args()
        if not self.options.repoid:
            print("Please specify the repo")
            sys.exit(0)
        try:
            groups = self.pconn.get_packagegroups(self.options.repoid)
            if not groups:
                print("PackageGroups not found in repo [%s]" % (self.options.repoid))
                sys.exit(-1)
            print "+-------------------------------------------+"
            print "Package Group Information "
            print "+-------------------------------------------+"
            print "Repository: %s" % (self.options.repoid)
            #print """+-------------------------------------------+\n    Package Group Information \n+-------------------------------------------+"""
            for key, value in groups.items():
                print "\t %s" % (key)
                #print """%s:                \t%-25s""" % (key, value)
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise

    def _info(self):
        (self.options, self.args) = self.parser.parse_args()
        if not self.options.groupid:
            print("Please specify the package group id to lookup")
            sys.exit(0)
        if not self.options.repoid:
            print("Please specify the repo")
            sys.exit(0)
        try:
            groups = self.pconn.get_packagegroups(self.options.repoid)
            if self.options.groupid not in groups:
                print("PackageGroup [%s] not found in repo [%s]" % (self.options.groupid, self.options.repoid))
                sys.exit(-1)
            print "+-------------------------------------------+"
            print "Package Group Information"
            print "+-------------------------------------------+"
            info = groups[self.options.groupid]
            for key, value in info.items():
                if key in ["display_order", "user_visible", "translated_name",
                        "translated_description", "langonly", "_id"]:
                    continue
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
            raise Exception("Not Implemented")
            print self.cconn.installpackages(self.options.consumerid, self.options.pnames)
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise

    def _add(self):
        (self.options, self.args) = self.parser.parse_args()
        if not self.options.repoid:
            print("Please specify the repo")
            sys.exit(0)
        if not self.options.pkgname:
            print("Please specify the package name to add to the group")
            sys.exit(0)
        if not self.options.groupid:
            print("Please specify the package group id")
            sys.exit(0)
        try:
            status = self.pconn.add_packagegroup(self.options.repoid, self.options.groupid,
                    self.options.pkgname, self.options.grouptype)
            print "Package [%s] added to group [%s] in repository [%s]" % (self.options.pkgname,
                    self.options.groupid, self.options.repoid)
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise

    def _create(self):
        (self.options, self.args) = self.parser.parse_args()
        if not self.options.repoid:
            print("Please specify the repo")
            sys.exit(0)
        try:
            status = self.pconn.CREATE_PKG_GROUP(self.options.repoid, self.options.groupid)
            if not status:
                print("PackageGroup [%s] could not be created in repo [%s]" % (self.options.groupid, self.options.repoid))
                sys.exit(-1)
            print "+-------------------------------------------+"
            print "Package Group [%s] created in repository [%s]" % (self.options.groupid, self.options.repoid)
            print "+-------------------------------------------+"
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise

    def _remove(self):
        (self.options, self.args) = self.parser.parse_args()
        if not self.options.repoid:
            print("Please specify the repo")
            sys.exit(0)
        if not self.options.pkgname:
            print("Please specify the package name to add to the group")
            sys.exit(0)
        if not self.options.groupid:
            print("Please specify the package group id")
            sys.exit(0)
        try:
            status = self.pconn.remove_package_from_group(self.options.repoid, self.options.groupid,
                    self.options.pkgname, self.options.grouptype)
            print "Package [%s] removed from group [%s] in repository [%s]" % (self.options.pkgname,
                    self.options.groupid, self.options.repoid)
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise

def _sub_dict(datadict, subkeys, default=None) :
    return dict([ (k, datadict.get(k, default) ) for k in subkeys ] )
