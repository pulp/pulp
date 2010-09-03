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
from M2Crypto import SSL
import pulp.client.utils as utils
import pulp.client.constants as constants
from pulp.client.core.basecore import BaseCore, systemExit
from pulp.client.connection import ConsumerConnection, RestlibException
from pulp.client.repolib import RepoLib
from pulp.client.logutil import getLogger
from pulp.client.config import Config
from pulp.client.package_profile import PackageProfile
from pulp.client import json_utils
import urlparse
log = getLogger(__name__)
CFG = Config()
#TODO: move this to config
CONSUMERID = "/etc/pulp/consumer"


import gettext
_ = gettext.gettext

class consumer(BaseCore):
    def __init__(self, is_admin=True, actions=None):
        usage = "consumer [OPTIONS]"
        shortdesc = "consumer specific actions to pulp server."
        desc = ""
        self.name = "consumer"
        self.actions = actions or {"delete"        : "Delete the consumer",
                                   "update"        : "Update consumer profile",
                                   "list"          : "List of accessible consumer info",
                                   "bind"          : "Bind the consumer to listed repos",
                                   "unbind"        : "Unbind the consumer from repos",
                                   "history"       : "View the consumer history",
        }
        self.is_admin = is_admin
        BaseCore.__init__(self, "consumer", usage, shortdesc, desc)
        self.cconn = None
        
        
    def load_server(self):
        self.cconn = ConsumerConnection(host=CFG.server.host or "localhost", 
                                        port=443, username=self.username,
                                        password=self.password,
                                        cert_file=self.cert_filename,
                                        key_file=self.key_filename)
        self.repolib = RepoLib()

    def generate_options(self):
        self.action = self._get_action()
        if self.action == "create":
            usage = "consumer create [OPTIONS]"
            self.setup_option_parser(usage, "", True)
            self.parser.add_option("--id", dest="id",
                           help="Consumer Identifier eg: foo.example.com")
            self.parser.add_option("--description", dest="description",
                           help="consumer description eg: foo's web server")
            self.parser.add_option("--server", dest="server",
                           help="The fully qualified hostname of the Pulp server you wish to create this consumer on")

        if self.action == "update":
            usage = "usage: %prog consumer update [OPTIONS]"
            self.setup_option_parser(usage, "", True)
            self.parser.add_option("--id", dest="id",
                           help="Consumer Identifier eg: foo.example.com")

        if self.action == "bind":
            usage = "usage: %prog consumer bind [OPTIONS]"
            self.setup_option_parser(usage, "", True)
            self.parser.add_option("--repoid", dest="repoid",
                           help="Repo Identifier")
            if self.is_admin:
                self.parser.add_option("--id", dest="id",
                                       help="Consumer Identifier")

        if self.action == "unbind":
            usage = "usage: %prog consumer unbind [OPTIONS]"
            self.setup_option_parser(usage, "", True)
            self.parser.add_option("--repoid", dest="repoid",
                           help="Repo Identifier")
            if self.is_admin:
                self.parser.add_option("--id", dest="id",
                                       help="Consumer Identifier")

        if self.action == "list":
            usage = "usage: %prog consumer list [OPTIONS]"
            self.setup_option_parser(usage, "", True)

        if self.action == "delete":
            usage = "usage: %prog consumer delete [OPTIONS]"
            self.setup_option_parser(usage, "", True)
            if self.is_admin:
                self.parser.add_option("--id", dest="id",
                                       help="Consumer Identifier")

        if self.action == "history":
            # TODO: This will be flushed out with query options eventually, for now I'm
            # just getting the base functionality in place for the sprint demo
            usage = "usage: %prog consumer history [OPTIONS]"
            self.setup_option_parser(usage, "", True)

    def _do_core(self):
        if self.action == "create":
            self._create()
        if self.action == "list":
            self._list()
        if self.action == "update":
            self._update()
        if self.action == "delete":
            self._delete()
        if self.action == "bind":
            self._bind()
        if self.action == "unbind":
            self._unbind()
        if self.action == "history":
            self._history()

    def _create(self):
        if (not self.options.username and not self.options.password 
                and (len(self.args) > 0)):
            print("username and password are required. Try --help")
            sys.exit(1)
        if not self.options.id:
            print("consumer id required. Try --help")
            sys.exit(0)
        if not self.options.description:
            self.options.description = self.options.id
        if self.options.server:
            CFG.server.host = self.options.server
            CFG.write()
            self.load_server()
        try:
            try:
                consumer = self.cconn.create(self.options.id, self.options.description)
            except SSL.Checker.WrongHost, wh:
                print "ERROR: The server hostname you have configured in /etc/pulp/ does not match the"
                print "hostname returned from the Pulp server you are connecting to.  "
                print ""
                print "You have: [%s] configured but received: [%s] from the server." % (wh.expectedHost, wh.actualHost)
                print ""
                print "Either correct the host in /etc/pulp/ or specify --server=%s" % wh.actualHost
                sys.exit(1)   

            cert_dict = self.cconn.certificate(self.options.id)
            certificate = cert_dict['certificate']
            key = cert_dict['private_key']
            utils.writeToFile(CONSUMERID, consumer['id'])
            utils.writeToFile(ConsumerConnection.CERT_PATH, certificate)
            utils.writeToFile(ConsumerConnection.KEY_PATH, key)
            pkginfo = PackageProfile().getPackageList()
            self.cconn.profile(self.options.id, pkginfo)
            print _(" Successfully created consumer [ %s ]" % consumer['id'])
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s", exc_info=True)
            raise
            
    def _update(self):
        
        consumer_id = self.getConsumer()
        try:
            pkginfo = PackageProfile().getPackageList()
            self.cconn.profile(consumer_id, pkginfo)
            print _(" Successfully updated consumer [%s] profile" % consumer_id)
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise

    def _info(self):
        try:
            cons = self.cconn.consumer(self.getConsumer())
            pkgs = " "
            for pkg in cons['package_profile'].values():
                for pkgversion in pkg:
                    pkgs += " " + utils.getRpmName(pkgversion)
            cons['package_profile'] = pkgs
            print """+-------------------------------------------+\n    Consumer Information \n+-------------------------------------------+"""
            for con in cons:
                print constants.AVAILABLE_CONSUMER_INFO % \
                        (con["id"], con["description"], con["repoids"], con["package_profile"])
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise
        
    def _list(self):
        try:
            cons = self.cconn.consumers()
            baseurl = "%s://%s:%s" % (CFG.server.scheme, CFG.server.host, CFG.server.port)
            for con in cons: 
                con['package_profile'] = urlparse.urljoin(baseurl, con['package_profile'])
            print """+-------------------------------------------+\n    Consumer Information \n+-------------------------------------------+"""
            for con in cons:
                print constants.AVAILABLE_CONSUMER_INFO % \
                        (con["id"], con["description"], con["repoids"], con["package_profile"])
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise

    def _bind(self):
        consumerid = self.getConsumer()
        if not self.options.repoid:
            print("repo id required. Try --help")
            sys.exit(0)
        try:
            self.cconn.bind(consumerid, self.options.repoid)
            self.repolib.update()
            print _(" Successfully subscribed consumer [%s] to repo [%s]" % (consumerid, self.options.repoid))
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise

    def _unbind(self):
        consumerid = self.getConsumer()
        if not self.options.repoid:
            print("repo id required. Try --help")
            sys.exit(0)
        try:
            self.cconn.unbind(consumerid, self.options.repoid)
            self.repolib.update()
            print _(" Successfully unsubscribed consumer [%s] from repo [%s]" % (consumerid, self.options.repoid))
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise


    def _delete(self):
        consumerid = self.getConsumer()
        try:
            self.cconn.delete(consumerid)
            print _(" Successfully deleted consumer [%s]" % consumerid)
        except RestlibException, re:
            print _(" Deleted operation failed on consumer [ %s ] " % \
                  consumerid)
            log.error("Error: %s" % re)
            sys.exit(-1)
        except Exception, e:
            log.error("Error: %s" % e)
            raise

    def _history(self):
        consumerid = self.getConsumer()
        try:
            results = self.cconn.history(consumerid)

            print """+-------------------------------------------+\n    Consumer History \n+-------------------------------------------+"""
            for entry in results:
                print constants.CONSUMER_HISTORY_ENTRY % \
                      (entry['type_name'], json_utils.parse_date(entry['timestamp']), entry['originator'])
                print('')

        except RestlibException, re:
            print _(" History retrieval failed for consumer [%s]" % consumerid)
            sys.exit(-1)

    def getConsumer(self):
        if not self.options.id:
            print("consumer id required. Try --help")
            sys.exit(0)
            
        return self.options.id
