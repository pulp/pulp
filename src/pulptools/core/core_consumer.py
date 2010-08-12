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
CERT_PATH = "/etc/pki/consumer/cert.pem"
KEY_PATH = "/etc/pki/consumer/key.pem"


import gettext
_ = gettext.gettext

class consumer(BaseCore):
    def __init__(self, is_admin=True, actions=None):
        usage = "usage: %prog consumer [OPTIONS]"
        shortdesc = "consumer specific actions to pulp server."
        desc = ""
        self.name = "consumer"
        self.actions = actions or {"delete"        : "Delete a consumer",
                                   "update"        : "Update consumer profile",
                                   "list"          : "List of accessible consumer info",
                                   "bind"          : "Bind the consumer to listed repos",
                                   "unbind"        : "UnBind the consumer from repos",}
        self.is_admin = is_admin
        BaseCore.__init__(self, "consumer", usage, shortdesc, desc)
        self.cconn = None
        self.repolib = RepoLib()
        
    def load_server(self):
        cert_path = None 
        key_path = None
        if (os.path.exists(CERT_PATH) and
                os.path.exists(KEY_PATH)):
            cert_path = CERT_PATH
            key_path = KEY_PATH
        self.cconn = ConsumerConnection(host=CFG.server.host or "localhost", 
                                        port=8811, cert_file=cert_path,
                                        key_file=key_path, username=self.username, 
                                        password=self.password)

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
                           help="Server hostname to register the consumer. Defaults to localhost")
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

    def _create(self):
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
            cert_dict = self.cconn.certificate(self.options.id)
            certificate = cert_dict['certificate']
            key = cert_dict['private_key']
            utils.writeToFile(CONSUMERID, consumer['id'])
            utils.writeToFile(CERT_PATH, certificate)
            utils.writeToFile(KEY_PATH, key)
            pkginfo = PackageProfile().getPackageList()
            self.cconn.profile(consumer['id'], pkginfo)
            print _(" Successfully created Consumer [ %s ]" % consumer['id'])
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
            print _(" Successfully subscribed Consumer [%s] to Repo [%s]" % (consumerid, self.options.repoid))
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
            print _(" Successfully unsubscribed Consumer [%s] from Repo [%s]" % (consumerid, self.options.repoid))
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
            print _(" Deleted operation failed on Consumer [ %s ] " % \
                  consumerid)
            log.error("Error: %s" % re)
            sys.exit(-1)
        except Exception, e:
            log.error("Error: %s" % e)
            raise
    
    def getConsumer(self):
        if not self.options.id:
            print("consumer id required. Try --help")
            sys.exit(0)
            
        return self.options.id
