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

import gettext
import sys

import pulp.client.constants as constants
from pulp.client.config import Config
from pulp.client.connection import ConsumerConnection, RepoConnection, RestlibException
from pulp.client.core.basecore import print_header, BaseCore, systemExit
from pulp.client.logutil import getLogger


log = getLogger(__name__)
CFG = Config()
#TODO: move this to config
CONSUMERID = "/etc/pulp/consumer"
_ = gettext.gettext


class packagegroup(BaseCore):
    def __init__(self):
        usage = "packagegroup [OPTIONS]"
        shortdesc = "packagegroup specific actions to pulp server."
        desc = ""
        self.name = "packagegroup"
        self.actions = {
                        "list"          : "list available packagegroups",
                        "info"          : "lookup information for a packagegroup",
                        "create"        : "create a packagegroup",
                        "delete"        : "delete a packagegroup",
                        "add_package"   : "add package to an existing packagegroup",
                        "delete_package": "delete package from an existing packagegroup",
                        "install"       : "Schedule a packagegroup install",
                        }
        BaseCore.__init__(self, "packagegroup", usage, shortdesc, desc)
        self.pconn = None

    def load_server(self):
        self.pconn = RepoConnection(host=CFG.server.host or "localhost",
                                    port=443, username=self.username,
                                    password=self.password,
                                    cert_file=self.cert_filename,
                                    key_file=self.key_filename)
        self.cconn = ConsumerConnection(host=CFG.server.host or "localhost",
                                        port=443, username=self.username,
                                        password=self.password,
                                        cert_file=self.cert_filename,
                                        key_file=self.key_filename)

    def generate_options(self):
        self.action = self._get_action()
        if self.action == "info":
            usage = "packagegroup info [OPTIONS]"
            self.setup_option_parser(usage, "", True)
            self.parser.add_option("--id", dest="groupid",
                           help="Packagegroup id to lookup")
            self.parser.add_option("--repoid", dest="repoid",
                           help="Repository Label")
        if self.action == "install":
            usage = "packagegroup install [OPTIONS]"
            self.setup_option_parser(usage, "", True)
            self.parser.add_option("-g", "--pkggroupid", action="append", dest="pkggroupid",
                           help="PackageGroup to install on a given consumer. \
                           To specify multiple package groups use multiple -g")
            self.parser.add_option("--consumerid", dest="consumerid",
                           help="Consumer Id")
        if self.action == "list":
            usage = "packagegroup list [OPTIONS]"
            self.setup_option_parser(usage, "", True)
            self.parser.add_option("--repoid", dest="repoid",
                           help="Repository Label")
        if self.action == "create":
            usage = "packagegroup create [OPTIONS]"
            self.setup_option_parser(usage, "", True)
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
            self.setup_option_parser(usage, "", True)
            self.parser.add_option("--repoid", dest="repoid",
                           help="Repository Label")
            self.parser.add_option("--id", dest="groupid",
                            help="Group id")
        if self.action == "add_package":
            usage = "packagegroup add_package [OPTIONS]"
            self.setup_option_parser(usage, "", True)
            self.parser.add_option("--repoid", dest="repoid",
                            help="Repository Label")
            self.parser.add_option("--id", dest="groupid",
                            help="Group id")
            self.parser.add_option("-n", "--name", action="append", dest="pnames",
                            help="Packages to be added. \
                                To specify multiple packages use multiple -n")
            self.parser.add_option("--type", dest="grouptype",
                            help="Type of list to add package to, example 'mandatory', 'optional', 'default'",
                            default="default")
        if self.action == "delete_package":
            usage = "packagegroup delete_package [OPTIONS]"
            self.setup_option_parser(usage, "", True)
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
            print _("Repo id required. Try --help")
            sys.exit(0)
        try:
            groups = self.pconn.packagegroups(self.options.repoid)
            if not groups:
                print _("PackageGroups not found in repo [%s]") % (self.options.repoid)
                sys.exit(-1)
            print_header("Repository: %s" % (self.options.repoid),
                         "Package Group Information")
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
            print _("package group id required. Try --help")
            sys.exit(0)
        if not self.options.repoid:
            print _("Repo id required. Try --help")
            sys.exit(0)
        try:
            groups = self.pconn.packagegroups(self.options.repoid)
            if self.options.groupid not in groups:
                print _("PackageGroup [%s] not found in repo [%s]") % \
                    (self.options.groupid, self.options.repoid)
                sys.exit(-1)
            print_header("Package Group Information")
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
            print _("consumer id required. Try --help")
            sys.exit(0)
        if not self.options.pkggroupid:
            print _("package group id required. Try --help")
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
            print _("Repo id required. Try --help")
            sys.exit(0)
        if not self.options.groupid:
            print _("package group id required. Try --help")
            sys.exit(0)
        if not self.options.groupname:
            print _("package group name required. Try --help")
            sys.exit(0)
        try:
            self.pconn.create_packagegroup(self.options.repoid,
                    self.options.groupid, self.options.groupname,
                    self.options.description)
            print_header("Package Group [%s] created in repository [%s]" %
                         (self.options.groupid, self.options.repoid))
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise

    def _delete(self):
        if not self.options.repoid:
            print _("Repo id required. Try --help")
            sys.exit(0)
        if not self.options.groupid:
            print _("package group id required. Try --help")
            sys.exit(0)
        try:
            self.pconn.delete_packagegroup(self.options.repoid, self.options.groupid)
            print _("PackageGroup [%s] deleted from repository [%s]") % \
                (self.options.groupid, self.options.repoid)
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise

    def _add_package(self):
        if not self.options.repoid:
            print _("Repo id required. Try --help")
            sys.exit(0)
        if not self.options.pnames:
            print _("package name required. Try --help")
            sys.exit(0)
        if not self.options.groupid:
            print _("package group id required. Try --help")
            sys.exit(0)
        try:
            self.pconn.add_packages_to_group(self.options.repoid,
                    self.options.groupid, self.options.pnames,
                    self.options.grouptype)
            print _("Following packages added to group [%s] in repository [%s]: \n %s") % \
                (self.options.groupid, self.options.repoid, self.options.pnames)
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise

    def _delete_package(self):
        if not self.options.repoid:
            print _("Repo id required. Try --help")
            sys.exit(0)
        if not self.options.pkgname:
            print _("package name required. Try --help")
            sys.exit(0)
        if not self.options.groupid:
            print _("package group id required. Try --help")
            sys.exit(0)
        try:
            self.pconn.delete_package_from_group(self.options.repoid,
                    self.options.groupid, self.options.pkgname,
                    self.options.grouptype)
            print _("Package [%s] deleted from group [%s] in repository [%s]") % \
                (self.options.pkgname, self.options.groupid, self.options.repoid)
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise

