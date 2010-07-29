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
from pulptools.connection import ConsumerConnection, RepoConnection, RestlibException
import pulptools.constants as constants
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
        usage = "packagegroup [OPTIONS]"
        shortdesc = "packagegroup specific actions to pulp server."
        desc = ""

        BaseCore.__init__(self, "packagegroup", usage, shortdesc, desc)
        self.actions = {
                        "list"          : "list available packagegroups",
                        "info"          : "lookup information for a packagegroup",
                        "create"        : "create a packagegroup",
                        "delete"        : "delete a packagegroup",
                        "add_package"   : "add package to an existing packagegroup",
                        "delete_package": "delete package from an existing packagegroup",
                        "install"       : "Schedule a packagegroup install",
                        }
        self.name = "packagegroup"
        self.pconn = None
        self.load_server()
        self.generate_options()

    def load_server(self):
        self.pconn = RepoConnection(host=CFG.server.host or "localhost", port=8811)
        self.cconn = ConsumerConnection(host=CFG.server.host or "localhost", port=8811)

    def generate_options(self):
        self.action = self._get_action()
        if self.action == "info":
            usage = "packagegroup info [OPTIONS]"
            BaseCore.__init__(self, "packagegroup info", usage, "", "")
            self.parser.add_option("--id", dest="groupid",
                           help="package name to lookup")
            self.parser.add_option("--repoid", dest="repoid",
                           help="Repository Label")
        if self.action == "install":
            usage = "packagegroup install [OPTIONS]"
            BaseCore.__init__(self, "packagegroup install", usage, "", "")
            self.parser.add_option("-p", "--pkggroupid", action="append", dest="pkggroupid",
                           help="PackageGroup to install on a given consumer. \
                           To specify multiple package groups use multiple -p")
            self.parser.add_option("--consumerid", dest="consumerid",
                           help="Consumer Id")
        if self.action == "list":
            usage = "packagegroup list [OPTIONS]"
            BaseCore.__init__(self, "packagegroup list", usage, "", "")
            self.parser.add_option("--repoid", dest="repoid",
                           help="Repository Label")
        if self.action == "create":
            usage = "packagegroup create [OPTIONS]"
            BaseCore.__init__(self, "packagegroup create", usage, "", "")
            self.parser.add_option("--repoid", dest="repoid",
                           help="Repository Label")
            self.parser.add_option("--id", dest="groupid",
                            help="Group id")
            self.parser.add_option("--name", dest="groupname",
                            help="Group name")
            self.parser.add_option("--description", dest="description",
                            help="Group description, default is ''", default="")
        if self.action == "delete":
            usage = "packagegroup delete [OPTIONS]"
            BaseCore.__init__(self, "packagegroup delete", usage, "", "")
            self.parser.add_option("--repoid", dest="repoid",
                           help="Repository Label")
            self.parser.add_option("--id", dest="groupid",
                            help="Group id")
        if self.action == "add_package":
            usage = "packagegroup add_package [OPTIONS]"
            BaseCore.__init__(self, "packagegroup add_package", usage, "", "")
            self.parser.add_option("--repoid", dest="repoid",
                            help="Repository Label")
            self.parser.add_option("--id", dest="groupid",
                            help="Group id")
            self.parser.add_option("--pkgname", dest="pkgname",
                            help="Package name")
            self.parser.add_option("--type", dest="grouptype",
                            help="Type of list to add package to, example 'mandatory', 'optional', 'default'",
                            default="default")
        if self.action == "delete_package":
            usage = "packagegroup delete_package [OPTIONS]"
            BaseCore.__init__(self, "packagegroup delete_package", usage, "", "")
            self.parser.add_option("--repoid", dest="repoid",
                            help="Repository Label")
            self.parser.add_option("--id", dest="groupid",
                            help="Group id")
            self.parser.add_option("--pkgname", dest="pkgname",
                            help="Package name")
            self.parser.add_option("--type", dest="grouptype",
                            help="Type of list to delete package from, example 'mandatory', 'optional', 'default'",
                            default="default")

    def _do_core(self):
        if self.action == "info":
            self._info()
        if self.action == "install":
            self._install()
        if self.action == "list":
            self._list()
        if self.action == "create":
            self._create()
        if self.action == "delete":
            self._delete()
        if self.action == "add_package":
            self._add_package()
        if self.action == "delete_package":
            self._delete_package()

    def _list(self):
        if not self.options.repoid:
            print("Please specify the repo")
            sys.exit(0)
        try:
            groups = self.pconn.packagegroups(self.options.repoid)
            if not groups:
                print("PackageGroups not found in repo [%s]" % (self.options.repoid))
                sys.exit(-1)
            print "+-------------------------------------------+"
            print "Repository: %s" % (self.options.repoid)
            print "Package Group Information "
            print "+-------------------------------------------+"
            keys = groups.keys()
            keys.sort()
            for key in keys:
                print "\t %s" % (key)
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise

    def _info(self):
        if not self.options.groupid:
            print("Please specify the package group id to lookup")
            sys.exit(0)
        if not self.options.repoid:
            print("Please specify the repo")
            sys.exit(0)
        try:
            groups = self.pconn.packagegroups(self.options.repoid)
            if self.options.groupid not in groups:
                print("PackageGroup [%s] not found in repo [%s]" % (self.options.groupid, self.options.repoid))
                sys.exit(-1)
            print "+-------------------------------------------+"
            print "Package Group Information"
            print "+-------------------------------------------+"
            info = groups[self.options.groupid]
            print constants.PACKAGE_GROUP_INFO % (info["name"], info["id"],
                    info["mandatory_package_names"], info["default_package_names"],
                    info["optional_package_names"], info["conditional_package_names"])
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise

    def _install(self):
        if not self.options.consumerid:
            print("Please specify a consumer to install the package group")
            sys.exit(0)
        if not self.options.pkggroupid:
            print("Please specify a package group id")
            sys.exit(0)
        try:
            print self.cconn.installpackagegroups(self.options.consumerid, 
                                             self.options.pkggroupid)
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise

    def _create(self):
        if not self.options.repoid:
            print("Please specify the repo")
            sys.exit(0)
        if not self.options.groupid:
            print ("Please specify the group id")
            sys.exit(0)
        if not self.options.groupname:
            print ("Please specify the group name")
            sys.exit(0)
        try:
            self.pconn.create_packagegroup(self.options.repoid, 
                    self.options.groupid, self.options.groupname, 
                    self.options.description)
            print "+-------------------------------------------+"
            print "Package Group [%s] created in repository [%s]" % \
                    (self.options.groupid, self.options.repoid)
            print "+-------------------------------------------+"
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise
    
    def _delete(self):
        if not self.options.repoid:
            print("Please specify the repo")
            sys.exit(0)
        if not self.options.groupid:
            print("Please specify the package group id")
            sys.exit(0)
        try:
            self.pconn.delete_packagegroup(self.options.repoid, self.options.groupid)
            print "PackageGroup [%s] deleted from repository [%s]" % \
                    (self.options.groupid, self.options.repoid)
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise
    
    def _add_package(self):
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
            self.pconn.add_package_to_group(self.options.repoid, 
                    self.options.groupid, self.options.pkgname, 
                    self.options.grouptype)
            print "Package [%s] added to group [%s] in repository [%s]" % \
                    (self.options.pkgname, self.options.groupid, 
                            self.options.repoid)
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise

    def _delete_package(self):
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
            self.pconn.delete_package_from_group(self.options.repoid, 
                    self.options.groupid, self.options.pkgname, 
                    self.options.grouptype)
            print "Package [%s] deleted from group [%s] in repository [%s]" % \
                    (self.options.pkgname, self.options.groupid, 
                            self.options.repoid)
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise

