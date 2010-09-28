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
import urlparse
from gettext import gettext as _

from M2Crypto import SSL

from pulp.client import constants
from pulp.client import json_utils
from pulp.client import utils
from pulp.client.config import Config
from pulp.client.connection import ConsumerConnection, RestlibException
from pulp.client.core.base import Action, BaseCore, systemExit, print_header
from pulp.client.logutil import getLogger
from pulp.client.package_profile import PackageProfile
from pulp.client.repolib import RepoLib



log = getLogger(__name__)
CFG = Config()
#TODO: move this to config
CONSUMERID = "/etc/pulp/consumer"

# base consumer action --------------------------------------------------------

class ConsumerAction(Action):

    def setup_parser(self):
        self.parser.add_option("--id", dest="id",
                       help="consumer identifier eg: foo.example.com")
        if hasattr(self, id):
            self.parser.set_defaults(id=self.id)

    def setup_server(self):
        self.cconn = ConsumerConnection(host=CFG.server.host or "localhost",
                                        port=443, username=self.username,
                                        password=self.password,
                                        cert_file=self.cert_filename,
                                        key_file=self.key_filename)
        self.repolib = RepoLib()

    def get_consumer(self):
        if not hasattr(self.opts, 'id'):
            self.parser.error(_("consumer id required; try --help"))
        return self.opts.id

    getConsumer = get_consumer

# consumer actions ------------------------------------------------------------

class Info(ConsumerAction):

    def run(self):
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


class List(ConsumerAction):

    def setup_parser(self):
        self.parser.add_option("--key", dest="key",
                       help="key identifier")
        self.parser.add_option("--value", dest="value",
                       help="value corresponding to the key")

    def run(self):
        if self.opts.key and not self.opts.value:
            print _("key-value required. Try --help")
            sys.exit(0)
        try:
            cons = self.cconn.consumers()
            baseurl = "%s://%s:%s" % (CFG.server.scheme, CFG.server.host, CFG.server.port)
            for con in cons:
                con['package_profile'] = urlparse.urljoin(baseurl, con['package_profile'])
            if not self.opts.key:
                print_header("Consumer Information ")
                for con in cons:
                    print constants.AVAILABLE_CONSUMER_INFO % \
                            (con["id"], con["description"], con["repoids"], con["package_profile"],
                             con["key_value_pairs"])
            else:
                consumers_with_keyvalues = []
                for con in cons:
                    key_value_pairs = con['key_value_pairs']
                    if (self.opts.key in key_value_pairs.keys()) and (key_value_pairs[self.opts.key] == self.opts.value):
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


class Create(ConsumerAction):

    def setup_parser(self):
        super(Create, self).setup_parser()
        self.parser.add_option("--description", dest="description",
                       help="consumer description eg: foo's web server")
        self.parser.add_option("--server", dest="server",
                       help="the fully qualified hostname of the pulp server you wish to create this consumer on")
        self.parser.add_option("--location", dest="location",
                       help="location or datacenter of the consumer")

    def run(self):
        if (not self.opts.username and not self.opts.password
                and (len(self.args) > 0)):
            print _("username and password are required. Try --help")
            sys.exit(1)
        if not self.opts.id:
            print _("consumer id required. Try --help")
            sys.exit(0)
        if not self.opts.description:
            self.opts.description = self.opts.id
        if self.opts.location:
            key_value_pairs = {'location': self.opts.location}
        else:
            key_value_pairs = {}
        if self.opts.server:
            CFG.server.host = self.opts.server
            CFG.write()
            self.load_server()
        try:
            try:
                consumer = self.cconn.create(self.opts.id, self.opts.description, key_value_pairs)
            except SSL.Checker.WrongHost, wh:
                print constants.CONSUMER_WRONG_HOST_ERROR % \
                    (wh.expectedHost, wh.actualHost, wh.actualHost)
                sys.exit(1)

            cert_dict = self.cconn.certificate(self.opts.id)
            certificate = cert_dict['certificate']
            key = cert_dict['private_key']
            utils.writeToFile(CONSUMERID, consumer['id'])
            utils.writeToFile(ConsumerConnection.CERT_PATH, certificate)
            utils.writeToFile(ConsumerConnection.KEY_PATH, key)
            pkginfo = PackageProfile().getPackageList()
            self.cconn.profile(self.opts.id, pkginfo)
            print _(" Successfully created consumer [ %s ]") % consumer['id']
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s", exc_info=True)
            raise


class Delete(ConsumerAction):

    def run(self):
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


class Update(ConsumerAction):

    def run(self):
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


class Bind(ConsumerAction):

    def setup_parser(self):
        super(Bind, self).setup_parser()
        self.parser.add_option("--repoid", dest="repoid",
                       help="repo identifier")

    def run(self):
        consumerid = self.getConsumer()
        if not self.opts.repoid:
            print _("repo id required. Try --help")
            sys.exit(0)
        try:
            self.cconn.bind(consumerid, self.opts.repoid)
            self.repolib.update()
            print _(" Successfully subscribed consumer [%s] to repo [%s]") % \
                (consumerid, self.opts.repoid)
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise


class Unbind(ConsumerAction):

    def setup_parser(self):
        super(Unbind, self).setup_parser()
        self.parser.add_option("--repoid", dest="repoid",
                       help="repo identifier")

    def run(self):
        consumerid = self.getConsumer()
        if not self.opts.repoid:
            print _("repo id required. Try --help")
            sys.exit(0)
        try:
            self.cconn.unbind(consumerid, self.opts.repoid)
            self.repolib.update()
            print _(" Successfully unsubscribed consumer [%s] from repo [%s]") % \
                (consumerid, self.opts.repoid)
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise


class AddKeyValue(ConsumerAction):

    def setup_parser(self):
        super(AddKeyValue, self).setup_parser()
        self.parser.add_option("--key", dest="key",
                       help="key identifier")
        self.parser.add_option("--value", dest="value",
                       help="value corresponding to the key")

    def run(self):
        consumerid = self.getConsumer()
        if not self.opts.key:
            print("Key is required. Try --help")
            sys.exit(0)
        if not self.opts.value:
            print("Value is required. Try --help")
            sys.exit(0)
        try:
            self.cconn.add_key_value_pair(consumerid, self.opts.key, self.opts.value)
            print _(" Successfully added key-value pair %s:%s" % (self.opts.key, self.opts.value))
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise


class DeleteKeyValue(ConsumerAction):

    def setup_parser(self):
        super(DeleteKeyValue, self).setup_parser()
        self.parser.add_option("--key", dest="key",
                       help="key identifier")

    def run(self):
        consumerid = self.getConsumer()
        if not self.opts.key:
            print("Key is required. Try --help")
            sys.exit(0)
        try:
            self.cconn.delete_key_value_pair(consumerid, self.opts.key)
            print _(" Successfully deleted key: %s" % self.opts.key)
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise


class History(ConsumerAction):

    def setup_parser(self):
        super(History, self).setup_parser()
        self.parser.add_option('--event_type', dest='event_type',
                               help='limits displayed history entries to the given type')
        self.parser.add_option('--limit', dest='limit',
                               help='limits displayed history entries to the given amount (must be greater than zero)')
        self.parser.add_option('--sort', dest='sort',
                               help='indicates the sort direction ("ascending" or "descending") based on the entry\'s timestamp')
        self.parser.add_option('--start_date', dest='start_date',
                               help='only return entries that occur after the given date (format: mm-dd-yyyy)')
        self.parser.add_option('--end_date', dest='end_date',
                               help='only return entries that occur before the given date (format: mm-dd-yyyy)')

    def run(self):
        consumerid = self.getConsumer()
        try:
            # Assemble the query parameters
            query_params = {
                'event_type' : self.opts.event_type,
                'limit' : self.opts.limit,
                'sort' : self.opts.sort,
                'start_date' : self.opts.start_date,
                'end_date' : self.opts.end_date,
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
            if re.code != 401:
                print _(" History retrieval failed for consumer [%s]" % consumerid)
            else:
                systemExit(re.code, re.msg)


# consumer command ------------------------------------------------------------

class Consumer(BaseCore):

    _default_actions = {
        "list": "List of accessible consumer info",
        "delete": "Delete the consumer",
        "update": "Update consumer profile",
        "bind": "Bind the consumer to listed repos",
        "unbind": "Unbind the consumer from repos",
        "add_keyvalue": "Add key-value information to consumer",
        "delete_keyvalue": "Delete key-value information to consumer",
        "history": "View the consumer history",
    }

    def __init__(self, name='consumer', actions=_default_actions):
        super(Consumer, self).__init__(name, actions)
        self.info = Info()
        self.list = List()
        self.create = Create()
        self.delete = Delete()
        self.update = Update()
        self.bind = Bind()
        self.unbind = Unbind()
        self.add_keyvalue = AddKeyValue()
        self.delete_keyvalue = DeleteKeyValue()
        self.history = History()


command_class = consumer = Consumer
