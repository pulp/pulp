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
import pulptools.utils as utils
import pulptools.constants as constants
from pulptools.core.basecore import BaseCore, systemExit
from pulptools.connection import ConsumerConnection, RestlibException
from pulptools.repolib import RepoLib
from pulptools.logutil import getLogger
from pulptools.config import Config
from pulptools.package_profile import PackageProfile
import urlparse
log = getLogger(__name__)
CFG = Config()
#TODO: move this to config
CONSUMERID = "/etc/pulp/consumer"
import gettext
_ = gettext.gettext

class consumer(BaseCore):
    def __init__(self):
        usage = "usage: %prog consumer [OPTIONS]"
        shortdesc = "consumer specific actions to pulp server."
        desc = ""

        BaseCore.__init__(self, "consumer", usage, shortdesc, desc)
        self.actions = {"register"      : "Register this system as a consumer", 
                        "unregister"    : "Delete a consumer", 
                        "list"          : "List of accessible consumer info",
                        "bind"          : "Bind the consumer to listed repos",
                        "unbind"        : "UnBind the consumer from repos",}
        self.name = "consumer"
        self.username = None
        self.password = None
        self.cconn = None
        self.load_server()
        self.repolib = RepoLib()
        self.generate_options()
        
    def load_server(self):
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
        if self.action == "register":
            usage = "usage: %prog consumer register [OPTIONS]"
            BaseCore.__init__(self, "consumer register", usage, "", "")
            self.parser.add_option("--id", dest="id",
                           help="Consumer Identifier eg: foo.example.com")
            self.parser.add_option("--description", dest="description",
                           help="consumer description eg: foo's web server")
            self.parser.add_option("--server", dest="server",
                           help="Server hostname to register the consumer. Defaults to localhost")
        if self.action == "bind":
            usage = "usage: %prog consumer bind [OPTIONS]"
            BaseCore.__init__(self, "consumer bind", usage, "", "")
            self.parser.add_option("--repoid", dest="repoid",
                           help="Repo Identifier")
            self.parser.add_option("--consumerid", dest="consumerid",
                           help="Consumer Identifier")
        if self.action == "unbind":
            usage = "usage: %prog consumer unbind [OPTIONS]"
            BaseCore.__init__(self, "consumer unbind", usage, "", "")
            self.parser.add_option("--repoid", dest="repoid",
                           help="Repo Identifier")
            self.parser.add_option("--consumerid", dest="consumerid",
                           help="Consumer Identifier")
        if self.action == "list":
            usage = "usage: %prog consumer list [OPTIONS]"
            BaseCore.__init__(self, "consumer list", usage, "", "")
        if self.action == "unregister":
            usage = "usage: %prog consumer unregister [OPTIONS]"
            BaseCore.__init__(self, "consumer unregister", usage, "", "")

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
        if self.action == "register":
            self._create()
        if self.action == "list":
            self._list()
        if self.action == "unregister":
            self._delete()
        if self.action == "bind":
            self._bind()
        if self.action == "unbind":
            self._unbind()

    def _create(self):
        (self.options, self.args) = self.parser.parse_args()
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
            consumer = self.cconn.create(self.options.id, self.options.description)
            utils.writeToFile(CONSUMERID, consumer['id'])
            pkginfo = PackageProfile().getPackageList()
            self.cconn.profile(consumer['id'], pkginfo)
            print _(" Successfully created Consumer [ %s ]" % consumer['id'])
        except RestlibException, re:
            raise
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise

    def _info(self):
        (self.options, self.args) = self.parser.parse_args()
        try:
            cons = self.cconn.consumer(getConsumer())
            pkgs = " "
            for pkg in cons['package_profile'].values():
                for pkgversion in pkg:
                    pkgs += " " + utils.getRpmName(pkgversion)
            cons['package_profile'] = pkgs
            columns = ["id", "description", "repoids", "package_profile"]
            data = [ _sub_dict(cons, columns)]# for con in cons]
            print """+-------------------------------------------+\n    Consumer Information \n+-------------------------------------------+"""
            for con in data:
                print constants.AVAILABLE_CONSUMER_INFO % \
                        (con["id"], con["description"], con["repoids"], con["package_profile"])
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise
        
    def _list(self):
        (self.options, self.args) = self.parser.parse_args()
        try:
            cons = self.cconn.consumers()
            baseurl = "%s://%s:%s" % (CFG.server.scheme, CFG.server.host, CFG.server.port)
            for con in cons: 
                con['package_profile'] = urlparse.urljoin(baseurl, con['package_profile']['href'])
            columns = ["id", "description", "repoids", "package_profile"]
            data = [ _sub_dict(con, columns) for con in cons]
            print """+-------------------------------------------+\n    Consumer Information \n+-------------------------------------------+"""
            for con in data:
                print constants.AVAILABLE_CONSUMER_INFO % \
                        (con["id"], con["description"], con["repoids"], con["package_profile"])
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise

    def _bind(self):
        (self.options, self.args) = self.parser.parse_args()
        if not self.options.consumerid:
            print("consumer id required. Try --help")
            sys.exit(0)
        if not self.options.repoid:
            print("repo id required. Try --help")
            sys.exit(0)
        try:
            self.cconn.bind(self.options.consumerid, self.options.repoid)
            self.repolib.update()
            print _(" Successfully subscribed Consumer [%s] to Repo [%s]" % (self.options.consumerid, self.options.repoid))
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise

    def _unbind(self):
        (self.options, self.args) = self.parser.parse_args()
        if not self.options.consumerid:
            print("consumer id required. Try --help")
            sys.exit(0)
        if not self.options.repoid:
            print("repo id required. Try --help")
            sys.exit(0)
        try:
            self.cconn.unbind(self.options.consumerid, self.options.repoid)
            self.repolib.update()
            print _(" Successfully unsubscribed Consumer [%s] from Repo [%s]" % (self.options.consumerid, self.options.repoid))
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise


    def _delete(self):
        print "under Construction"
        
def getConsumer():
    ##TODO: this will eventually be a x509 cert
    if not os.path.exists(CONSUMERID):
        print("Error: This client is currently not registered. Please register to continue")
        sys.exit(0)
    try:
        consumerid = open(CONSUMERID).read()
    except Exception, e:
        print("Error reading consumer." + e)
        sys.exit(-1)
    return consumerid
        
def _sub_dict(datadict, subkeys, default=None) :
    return dict([ (k, datadict.get(k, default) ) for k in subkeys ] )
