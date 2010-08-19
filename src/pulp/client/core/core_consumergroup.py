#!/usr/bin/python
#
# Pulp Repo management module
#
# Copyright (c) 2010 Red Hat, Inc.

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

import pulp.client.constants as constants
from pulp.client.core.basecore import BaseCore, systemExit
from pulp.client.connection import ConsumerGroupConnection, RestlibException
from pulp.client.logutil import getLogger
from pulp.client.repolib import RepoLib
from pulp.client.config import Config
CFG = Config()

import gettext
_ = gettext.gettext
log = getLogger(__name__)

class consumergroup(BaseCore):
    def __init__(self):
        usage = "consumergroup [OPTIONS]"
        shortdesc = "consumer group specific actions to pulp server."
        desc = ""
        self.name = "consumergroup"
        self.actions = {"create" : "Create a consumer group",
                        "add_consumer" : "Add a consumer to the group",
                        "delete_consumer" : "Delete a consumer from the group",
                        "list"   : "List available consumer groups",
                        "delete" : "Delete a consumer group",
                        "bind"   : "Bind the consumer group to listed repos",
                        "unbind" : "UnBind the consumer group from repos",}
        BaseCore.__init__(self, "consumergroup", usage, shortdesc, desc)
        self.repolib = RepoLib()

    def load_server(self):
        self.cgconn = ConsumerGroupConnection(host=CFG.server.host or "localhost", 
                                              port=CFG.server.port or 8811,
                                              username=self.username, 
                                              password=self.password)

    def generate_options(self):
        self.action = self._get_action()
        if self.action == "create":
            usage = "consumergroup create [OPTIONS]"
            self.setup_option_parser(usage, "", True)
            self.parser.add_option("--id", dest="id",
                           help="consumer group id"),
            self.parser.add_option("--description", dest="description",
                           help="description of consumer group")
            self.parser.add_option("--consumerids", dest="consumerids",
                           help="consumer id list to be included in this group")
        if self.action == "delete":
            usage = "consumergroup delete [OPTIONS]"
            self.setup_option_parser(usage, "", True)
            self.parser.add_option("--id", dest="id",
                           help="Consumer group id")
        if self.action == "list":
            usage = "consumergroup list [OPTIONS]"
            self.setup_option_parser(usage, "", True)
        if self.action == "add_consumer":
            usage = "consumergroup add_consumer [OPTIONS]"
            self.setup_option_parser(usage, "", True)
            self.parser.add_option("--consumerid", dest="consumerid",
                           help="Consumer Identifier")
            self.parser.add_option("--id", dest="groupid",
                           help="Consumer Group Identifier")
        if self.action == "delete_consumer":
            usage = "consumergroup delete_consumer [OPTIONS]"
            self.setup_option_parser(usage, "", True)
            self.parser.add_option("--consumerid", dest="consumerid",
                           help="Consumer Identifier")
            self.parser.add_option("--id", dest="groupid",
                           help="Consumer Group Identifier")
        if self.action == "bind":
            usage = "consumergroup bind [OPTIONS]"
            self.setup_option_parser(usage, "", True)
            self.parser.add_option("--repoid", dest="repoid",
                           help="Repo Identifier")
            self.parser.add_option("--id", dest="groupid",
                           help="Consumer Group Identifier")
        if self.action == "unbind":
            usage = "consumergroup unbind [OPTIONS]"
            self.setup_option_parser(usage, "", True)
            self.parser.add_option("--repoid", dest="repoid",
                           help="Repo Identifier")
            self.parser.add_option("--id", dest="groupid",
                           help="Consumer Group Identifier")

    def _do_core(self):
        if self.action == "create":
            self._create()
        if self.action == "list":
            self._list()
        if self.action == "delete":
            self._delete()
        if self.action == "add_consumer":
            self._add_consumer()
        if self.action == "delete_consumer":
            self._delete_consumer()
        if self.action == "bind":
            self._bind()
        if self.action == "unbind":
            self._unbind()

    def _create(self):
        if not self.options.id:
            print("consumer group id required. Try --help")
            sys.exit(0)
        if not self.options.description:
            self.options.description = ""
        if not self.options.consumerids:
            print("Creating empty consumer group")
            self.options.consumerids = []
        else:
            self.options.consumerids = self.options.consumerids.split(",")
        try:
            consumergroup = self.cgconn.create(self.options.id, self.options.description,
                                    self.options.consumerids)
            print _(" Successfully created Consumer group [ %s ] with description [ %s ]" % \
                                     (consumergroup['id'], consumergroup["description"]))
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise

    def _list(self):
        try:
            groups = self.cgconn.consumergroups()
            if not len(groups):
                print _("No consumer groups available to list")
                sys.exit(0)
            print """+-------------------------------------------+\n    List of Available Consumer Groups \n+-------------------------------------------+"""
            for group in groups:
                    print constants.AVAILABLE_CONSUMER_GROUP_INFO % (group["id"], group["description"], group["consumerids"] )
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise


    def _delete(self):
        if not self.options.id:
            print("Group id required. Try --help")
            sys.exit(0)
        group = self.cgconn.consumergroup(id=self.options.id)
        if not group:
            print _(" Consumer Group [ %s ] does not exist" % \
                  self.options.id)
            sys.exit(-1)
        try:
            self.cgconn.delete(id=self.options.id)
            print _(" Successfully deleted Consumer Group [ %s ] " % self.options.id)
        except RestlibException, re:
            print _(" Delete operation failed Consumer Group [ %s ] " % \
                  self.options.id)
            log.error("Error: %s" % re)
            sys.exit(-1)
        except Exception, e:
            print _(" Delete operation failed on Consumer Group [ %s ]. " % \
                  self.options.id)
            log.error("Error: %s" % e)
            sys.exit(-1)


    def _add_consumer(self):
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
            print _(" Adding consumer failed ")
            log.error("Error: %s" % re)
            sys.exit(-1)
        except Exception, e:
            log.error("Error: %s" % e)
            raise

    def _delete_consumer(self):
        if not self.options.consumerid:
            print("consumer id required. Try --help")
            sys.exit(0)
        if not self.options.groupid:
            print("group id required. Try --help")
            sys.exit(0)
        try:
            self.cgconn.delete_consumer(self.options.groupid, self.options.consumerid)
            print _(" Successfully deleted Consumer [%s] from Group [%s]" % (self.options.consumerid, self.options.groupid))
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise

    def _bind(self):
        if not self.options.groupid:
            print("consumer group id required. Try --help")
            sys.exit(0)
        if not self.options.repoid:
            print("repo id required. Try --help")
            sys.exit(0)
        try:
            self.cgconn.bind(self.options.groupid, self.options.repoid)
            self.repolib.update()
            print _(" Successfully subscribed Consumer Group [%s] to Repo [%s]" % (self.options.groupid, self.options.repoid))
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise

    def _unbind(self):
        if not self.options.groupid:
            print("consumer group id required. Try --help")
            sys.exit(0)
        if not self.options.repoid:
            print("repo id required. Try --help")
            sys.exit(0)
        try:
            self.cgconn.unbind(self.options.groupid, self.options.repoid)
            self.repolib.update()
            print _(" Successfully unsubscribed Consumer  Group [%s] from Repo [%s]" % (self.options.groupid, self.options.repoid))
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise
