#!/usr/bin/python
#
# Pulp Repo management module
#
# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: Sayli Karmarkar <skarmark@redhat.com>

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

import pulptools.constants as constants
from pulptools.core.basecore import BaseCore, systemExit
from pulptools.connection import ConsumerGroupConnection, RestlibException
from pulptools.logutil import getLogger
from pulptools.config import Config
CFG = Config()

import gettext
_ = gettext.gettext
log = getLogger(__name__)

class consumergroup(BaseCore):
    def __init__(self):
        usage = "usage: %prog consumergroup [OPTIONS]"
        shortdesc = "consumer group specific actions to pulp server."
        desc = ""

        BaseCore.__init__(self, "consumergroup", usage, shortdesc, desc)
        self.actions = {"create" : "Create a consumer group",
                        "add_consumer" : "Add a consumer to the group",
                        "remove_consumer" : "Remove a consumer from the group",
                        "list"   : "List available consumer groups",
                        "remove" : "Remove a consumer group",}

        self.username = None
        self.password = None
        self.name = "consumergroup"
        self.cgconn = ConsumerGroupConnection(host=CFG.server.host or "localhost", 
                                              port=CFG.server.port or 8811)
        self.generate_options()

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
        if self.action == "create":
            usage = "usage: %prog consumergroup create [OPTIONS]"
            BaseCore.__init__(self, "consumergroup create", usage, "", "")
            self.parser.add_option("--id", dest="id",
                           help="consumer group id"),
            self.parser.add_option("--name", dest="name",
                           help="consumer group name"),
            self.parser.add_option("--description", dest="description",
                           help="description of consumer group")
            self.parser.add_option("--consumerids", dest="consumerids",
                           help="consumer id list to be included in this group")
        if self.action == "remove":
            usage = "usage: %prog consumergroup remove [OPTIONS]"
            BaseCore.__init__(self, "consumergroup remove", usage, "", "")
            self.parser.add_option("--id", dest="id",
                           help="Consumer group id")
        if self.action == "list":
            usage = "usage: %prog consumergroup list [OPTIONS]"
            BaseCore.__init__(self, "consumergroup list", usage, "", "")
        if self.action == "add_consumer":
            usage = "usage: %prog consumergroup add_consumer [OPTIONS]"
            BaseCore.__init__(self, "consumergroup add_consumer", usage, "", "")
            self.parser.add_option("--consumerid", dest="consumerid",
                           help="Consumer Identifier")
            self.parser.add_option("--groupid", dest="groupid",
                           help="Consumer Group Identifier")
        if self.action == "remove_consumer":
            usage = "usage: %prog consumergroup remove_consumer [OPTIONS]"
            BaseCore.__init__(self, "consumergroup remove_consumer", usage, "", "")
            self.parser.add_option("--consumerid", dest="consumerid",
                           help="Consumer Identifier")
            self.parser.add_option("--groupid", dest="groupid",
                           help="Consumer Group Identifier")

    def _validate_options(self):
        pass

    def _usage(self):
        print "\nUsage: %s MODULENAME ACTION [options] --help\n" % os.path.basename(sys.argv[0])
        print "Supported Actions:\n"
        items = self.actions.items()
        items.sort()
        for (name, cmd) in items:
            print("\t%-14s %-25s" % (name, cmd))
        print("")

    def _do_core(self):
        self._validate_options()
        if self.action == "create":
            self._create()
        if self.action == "list":
            self._list()
        if self.action == "remove":
            self._delete()
        if self.action == "add_consumer":
            self._add_consumer()
        if self.action == "remove_consumer":
            self._remove_consumer()

    def _create(self):
        (self.options, self.args) = self.parser.parse_args()
        if not self.options.id:
            print("consumer group id required. Try --help")
            sys.exit(0)
        if not self.options.name:
            print("consumer group name required. Try --help")
            sys.exit(0)
        if not self.options.description:
            self.options.description = ""
        if not self.options.consumerids:
            print("Creating empty consumer group")
            self.options.consumerids = []
        try:
            consumergroup = self.cgconn.create(self.options.id, self.options.name, self.options.description,
                                    self.options.consumerids)
            print _(" Successfully created Consumer group [ %s ] with description [ %s ]" % \
                                     (consumergroup['name'], consumergroup["description"]))
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise

    def _list(self):
        (self.options, self.args) = self.parser.parse_args()
        try:
            groups = self.cgconn.consumergroups()
            columns = ["id", "name", "description", "consumerids"]
            data = [ _sub_dict(group, columns) for group in groups]
            if not len(data):
                print _("No consumer groups available to list")
                sys.exit(0)
            print """+-------------------------------------------+\n    List of Available Consumer Groups \n+-------------------------------------------+"""
            for group in data:
                    print constants.AVAILABLE_CONSUMER_GROUP_INFO % (group["id"], group["name"], group["description"], group["consumerids"] )
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise


    def _delete(self):
        (self.options, self.args) = self.parser.parse_args()
        if not self.options.id:
            print("Group id required. Try --help")
            sys.exit(0)
        try:
            self.cgconn.delete(id=self.options.id)
            print _(" Successful removed Consumer Group [ %s ] " % self.options.id)
        except RestlibException, re:
            print _(" Deleted operation failed Consumer Group [ %s ] " % \
                  self.options.id)
            log.error("Error: %s" % re)
            sys.exit(-1)
        except Exception, e:
            print _(" Removed operation failed on Consumer Group [ %s ]. " % \
                  self.options.id)
            log.error("Error: %s" % e)
            sys.exit(-1)


    def _add_consumer(self):
        (self.options, self.args) = self.parser.parse_args()
        if not self.options.consumerid:
            print("consumer id required. Try --help")
            sys.exit(0)
        if not self.options.groupid:
            print("group id required. Try --help")
            sys.exit(0)
        try:
            self.cgconn.add_consumer(self.options.groupid, self.options.consumerid)
            print _(" Successfully added Consumer [%s] to Group [%s]" % (self.options.consumerid, self.options.groupid))
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise

    def _remove_consumer(self):
        (self.options, self.args) = self.parser.parse_args()
        if not self.options.consumerid:
            print("consumer id required. Try --help")
            sys.exit(0)
        if not self.options.groupid:
            print("group id required. Try --help")
            sys.exit(0)
        try:
            self.cgconn.remove_consumer(self.options.groupid, self.options.consumerid)
            print _(" Successfully removed Consumer [%s] from Group [%s]" % (self.options.consumerid, self.options.groupid))
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise


def _sub_dict(datadict, subkeys, default=None) :
    return dict([ (k, datadict.get(k, default) ) for k in subkeys ] )
