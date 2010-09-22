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

import gettext
import sys
import urlparse

from M2Crypto import SSL

import pulp.client.constants as constants
import pulp.client.utils as utils
from pulp.client import json_utils
from pulp.client.config import Config
from pulp.client.connection import ConsumerConnection, RestlibException
from pulp.client.core.basecore import BaseCore, systemExit, print_header
from pulp.client.logutil import getLogger
from pulp.client.package_profile import PackageProfile
from pulp.client.repolib import RepoLib



log = getLogger(__name__)
CFG = Config()
#TODO: move this to config
CONSUMERID = "/etc/pulp/consumer"

_ = gettext.gettext


class consumer(BaseCore):
    def __init__(self, is_admin=True, actions=None):
        usage = "consumer [OPTIONS]"
        shortdesc = "consumer specific actions to pulp server."
        desc = ""
        self.name = "consumer"
        self.actions = actions or {"delete"           : "Delete the consumer",
                                   "update"           : "Update consumer profile",
                                   "list"             : "List of accessible consumer info",
                                   "bind"             : "Bind the consumer to listed repos",
                                   "unbind"           : "Unbind the consumer from repos",
                                   "add_keyvalue"     : "Add key-value information to consumer",
                                   "delete_keyvalue"  : "Delete key-value information to consumer",
                                   "history"          : "View the consumer history",
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
            self.parser.add_option("--location", dest="location",
                           help="Location or datacenter of the consumer")

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
                
        if self.action == "add_keyvalue":
            usage = "usage: %prog consumer add_keyvalue [OPTIONS]"
            self.setup_option_parser(usage, "", True)
            self.parser.add_option("--key", dest="key",
                           help="Key Identifier")
            self.parser.add_option("--value", dest="value",
                           help="Value corresponding to the key")      
            if self.is_admin:   
                self.parser.add_option("--id", dest="id",
                                       help="Consumer Identifier")
                
        if self.action == "delete_keyvalue":
            usage = "usage: %prog consumer delete_keyvalue [OPTIONS]"
            self.setup_option_parser(usage, "", True)
            self.parser.add_option("--key", dest="key",
                           help="Key Identifier")
            if self.is_admin:   
                self.parser.add_option("--id", dest="id",
                                       help="Consumer Identifier")       
                
        if self.action == "list":
            usage = "usage: %prog consumer list [OPTIONS]"
            self.setup_option_parser(usage, "", True)
            self.parser.add_option("--key", dest="key",
                           help="Key Identifier")
            self.parser.add_option("--value", dest="value",
                           help="Value corresponding to the key") 

        if self.action == "delete":
            usage = "usage: %prog consumer delete [OPTIONS]"
            self.setup_option_parser(usage, "", True)
            if self.is_admin:
                self.parser.add_option("--id", dest="id",
                                       help="Consumer Identifier")

        if self.action == "history":
            usage = "usage: %prog consumer history [OPTIONS]"
            self.setup_option_parser(usage, "", True)
            self.parser.add_option('--event_type', dest='event_type',
                                   help='Limits displayed history entries to the given type')
            self.parser.add_option('--limit', dest='limit',
                                   help='Limits displayed history entries to the given amount (must be greater than zero)')
            self.parser.add_option('--sort', dest='sort',
                                   help='Indicates the sort direction ("ascending" or "descending") based on the entry\'s timestamp')
            self.parser.add_option('--start_date', dest='start_date',
                                   help='Only return entries that occur after the given date (format: mm-dd-yyyy)')
            self.parser.add_option('--end_date', dest='end_date',
                                   help='Only return entries that occur before the given date (format: mm-dd-yyyy)')

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
        if self.action == "add_keyvalue":
            self._add_keyvalue()
        if self.action == "delete_keyvalue":
            self._delete_keyvalue()
        if self.action == "history":
            self._history()

    def _create(self):
        if (not self.options.username and not self.options.password
                and (len(self.args) > 0)):
            print _("username and password are required. Try --help")
            sys.exit(1)
        if not self.options.id:
            print _("consumer id required. Try --help")
            sys.exit(0)
        if not self.options.description:
            self.options.description = self.options.id
        if self.options.location:
            key_value_pairs = {'location': self.options.location}
        else:
            key_value_pairs = {}
        if self.options.server:
            CFG.server.host = self.options.server
            CFG.write()
            self.load_server()
        try:
            try:
                consumer = self.cconn.create(self.options.id, self.options.description, key_value_pairs)
            except SSL.Checker.WrongHost, wh:
                print constants.CONSUMER_WRONG_HOST_ERROR % \
                    (wh.expectedHost, wh.actualHost, wh.actualHost)
                sys.exit(1)

            cert_dict = self.cconn.certificate(self.options.id)
            certificate = cert_dict['certificate']
            key = cert_dict['private_key']
            utils.writeToFile(CONSUMERID, consumer['id'])
            utils.writeToFile(ConsumerConnection.CERT_PATH, certificate)
            utils.writeToFile(ConsumerConnection.KEY_PATH, key)
            pkginfo = PackageProfile().getPackageList()
            self.cconn.profile(self.options.id, pkginfo)
            print _(" Successfully created consumer [ %s ]") % consumer['id']
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
            print _(" Successfully updated consumer [%s] profile") % consumer_id
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
            print_header("Consumer Information")
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
        if self.options.key and not self.options.value:
            print _("key-value required. Try --help")
            sys.exit(0) 
        try:
            cons = self.cconn.consumers()
            baseurl = "%s://%s:%s" % (CFG.server.scheme, CFG.server.host, CFG.server.port)
            for con in cons:
                con['package_profile'] = urlparse.urljoin(baseurl, con['package_profile'])
            if not self.options.key:
                print_header("Consumer Information ")
                for con in cons:
                    print constants.AVAILABLE_CONSUMER_INFO % \
                            (con["id"], con["description"], con["repoids"], con["package_profile"],
                             con["key_value_pairs"])
            else:
                consumers_with_keyvalues = []
                for con in cons:
                    key_value_pairs = con['key_value_pairs']
                    if (self.options.key in key_value_pairs.keys()) and (key_value_pairs[self.options.key] == self.options.value):
                        consumers_with_keyvalues.append(con)
                for con in consumers_with_keyvalues:
                    print constants.AVAILABLE_CONSUMER_INFO % \
                            (con["id"], con["description"], con["repoids"], con["package_profile"],
                             con["key_value_pairs"])                          
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise

    def _bind(self):
        consumerid = self.getConsumer()
        if not self.options.repoid:
            print _("repo id required. Try --help")
            sys.exit(0)
        try:
            self.cconn.bind(consumerid, self.options.repoid)
            self.repolib.update()
            print _(" Successfully subscribed consumer [%s] to repo [%s]") % \
                (consumerid, self.options.repoid)
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise

    def _unbind(self):
        consumerid = self.getConsumer()
        if not self.options.repoid:
            print _("repo id required. Try --help")
            sys.exit(0)
        try:
            self.cconn.unbind(consumerid, self.options.repoid)
            self.repolib.update()
            print _(" Successfully unsubscribed consumer [%s] from repo [%s]") % \
                (consumerid, self.options.repoid)
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise

    def _add_keyvalue(self):    
        consumerid = self.getConsumer()
        if not self.options.key:
            print("Key is required. Try --help")
            sys.exit(0)
        if not self.options.value:
            print("Value is required. Try --help")
            sys.exit(0)            
        try:
            self.cconn.add_key_value_pair(consumerid, self.options.key, self.options.value)
            print _(" Successfully added key-value pair %s:%s" % (self.options.key, self.options.value))
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise
        
    def _delete_keyvalue(self):    
        consumerid = self.getConsumer()
        if not self.options.key:
            print("Key is required. Try --help")
            sys.exit(0)
        try:
            self.cconn.delete_key_value_pair(consumerid, self.options.key)
            print _(" Successfully deleted key: %s" % self.options.key)
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
            print _(" Successfully deleted consumer [%s]") % consumerid
        except RestlibException, re:
            print _(" Deleted operation failed on consumer [ %s ]") % consumerid
            log.error("Error: %s" % re)
            sys.exit(-1)
        except Exception, e:
            log.error("Error: %s" % e)
            raise

    def _history(self):
        consumerid = self.getConsumer()
        try:
            # Assemble the query parameters
            query_params = {
                'event_type' : self.options.event_type,
                'limit' : self.options.limit,
                'sort' : self.options.sort,
                'start_date' : self.options.start_date,
                'end_date' : self.options.end_date,
            }

            results = self.cconn.history(consumerid, query_params)

            print_header("Consumer History ")
            for entry in results:

                # Attempt to translate the programmatic event type name to a user readable one
                if constants.CONSUMER_HISTORY_EVENT_TYPES.has_key(entry['type_name']):
                    event_type = constants.CONSUMER_HISTORY_EVENT_TYPES[entry['type_name']]
                else:
                    event_type = entry['type_name']

                # Common event details
                print constants.CONSUMER_HISTORY_ENTRY % \
                      (event_type, json_utils.parse_date(entry['timestamp']), entry['originator'])

                # Based on the type of event, add on the event specific details. Otherwise,
                # just throw an empty line to account for the blank line that's added
                # by the details rendering.
                if entry['type_name'] == 'repo_bound' or entry['type_name'] == 'repo_unbound':
                    print constants.CONSUMER_HISTORY_REPO % (entry['details']['repo_id'])
                if entry['type_name'] == 'package_installed' or entry['type_name'] == 'package_uninstalled':
                    print constants.CONSUMER_HISTORY_PACKAGES

                    for package_nvera in entry['details']['package_nveras']:
                        print '  %s' % package_nvera

                print ''

        except RestlibException, re:
            print _(" History retrieval failed for consumer [%s]") % consumerid
            sys.exit(-1)

    def getConsumer(self):
        if not self.options.id:
            print _("consumer id required. Try --help")
            sys.exit(0)

        return self.options.id
