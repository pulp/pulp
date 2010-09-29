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

import urlparse
from gettext import gettext as _
from optparse import SUPPRESS_HELP

from pulp.client import constants
from pulp.client import json_utils
from pulp.client import utils
from pulp.client.config import Config
from pulp.client.connection import ConsumerConnection
from pulp.client.core.base import Action, BaseCore, print_header, system_exit
from pulp.client.package_profile import PackageProfile
from pulp.client.repolib import RepoLib


_cfg = Config()
#TODO: move this to config
_consumer_file = "/etc/pulp/consumer"

# base consumer action --------------------------------------------------------

class ConsumerAction(Action):

    def __init__(self):
        super(ConsumerAction, self).__init__()
        self.repolib = RepoLib()

    def connections(self):
        return {'cconn': ConsumerConnection}

    def setup_parser(self):
        help = _("consumer identifier eg: foo.example.com")
        default = None
        if hasattr(self, id):
            help = SUPPRESS_HELP
            default = self.id
        self.parser.add_option("--id", dest="id", default=default, help=help)

# consumer actions ------------------------------------------------------------

class Info(ConsumerAction):

    name = 'info'
    plug = 'list of accessible consumer info'

    def run(self):
        id = self.get_required_option('id')
        cons = self.cconn.consumer(id)
        pkgs = ""
        for pkg in cons['package_profile'].values():
            for pkgversion in pkg:
                pkgs += " " + utils.getRpmName(pkgversion)
        cons['package_profile'] = pkgs
        print_header("Consumer Information")
        for con in cons:
            print constants.AVAILABLE_CONSUMER_INFO % \
                    (con["id"], con["description"], con["repoids"],
                     con["package_profile"])


class List(ConsumerAction):

    name = 'list'
    plug = 'list all known consumers'

    def setup_parser(self):
        self.parser.add_option("--key", dest="key", help="key identifier")
        self.parser.add_option("--value", dest="value",
                               help="value corresponding to the key")

    def run(self):
        key = self.opts.key
        value = None
        if key is not None:
            value = self.get_required_option('value')
        cons = self.cconn.consumers()
        baseurl = "%s://%s:%s" % (_cfg.server.scheme, _cfg.server.host,
                                  _cfg.server.port)
        for con in cons:
            con['package_profile'] = urlparse.urljoin(baseurl,
                                                      con['package_profile'])
        if key is None:
            print_header("Consumer Information ")
            for con in cons:
                print constants.AVAILABLE_CONSUMER_INFO % \
                        (con["id"], con["description"], con["repoids"],
                         con["package_profile"], con["key_value_pairs"])
            system_exit(0)

        consumers_with_keyvalues = []
        for con in cons:
            key_value_pairs = con['key_value_pairs']
            if (key in key_value_pairs.keys()) and \
                (key_value_pairs[key] == value):
                consumers_with_keyvalues.append(con)
        for con in consumers_with_keyvalues:
            print constants.AVAILABLE_CONSUMER_INFO % \
                    (con["id"], con["description"], con["repoids"],
                     con["package_profile"], con["key_value_pairs"])


class Create(ConsumerAction):

    name = 'create'
    plug = 'create a consumer'

    def setup_parser(self):
        super(Create, self).setup_parser()
        self.parser.add_option("--description", dest="description",
                               help="consumer description eg: foo's web server")
        self.parser.add_option("--location", dest="location",
                               help="location or datacenter of the consumer")

    def run(self):
        id = self.get_required_option('id')
        description = getattr(self.opts, 'description', id)
        location = getattr(self.opts, 'location', None)
        key_value_pairs = {} if location is None else {'location': location}
        consumer = self.cconn.create(id, description, key_value_pairs)
        cert_dict = self.cconn.certificate(id)
        certificate = cert_dict['certificate']
        key = cert_dict['private_key']
        utils.writeToFile(_consumer_file, consumer['id'])
        utils.writeToFile(ConsumerConnection.CERT_PATH, certificate)
        utils.writeToFile(ConsumerConnection.KEY_PATH, key)
        pkginfo = PackageProfile().getPackageList()
        self.cconn.profile(id, pkginfo)
        print _(" successfully created consumer [ %s ]") % consumer['id']


class Delete(ConsumerAction):

    name = 'delete'
    plug = 'delete the consumer'

    def run(self):
        consumerid = self.get_required_option('id')
        self.cconn.delete(consumerid)
        print _(" successfully deleted consumer [%s]") % consumerid


class Update(ConsumerAction):

    name = 'update'
    plug = 'update consumer profile'

    def run(self):
        consumer_id = self.get_required_option('id')
        pkginfo = PackageProfile().getPackageList()
        self.cconn.profile(consumer_id, pkginfo)
        print _(" successfully updated consumer [%s] profile") % consumer_id


class Bind(ConsumerAction):

    name = 'bind'
    plug = 'bind the consumer to listed repos'

    def setup_parser(self):
        super(Bind, self).setup_parser()
        self.parser.add_option("--repoid", dest="repoid",
                       help="repo identifier")

    def run(self):
        consumerid = self.get_required_option('id')
        repoid = self.get_required_option('repoid')
        self.cconn.bind(consumerid, repoid)
        self.repolib.update()
        print _(" successfully subscribed consumer [%s] to repo [%s]") % \
                (consumerid, repoid)


class Unbind(ConsumerAction):

    name = 'unbind'
    plug = 'unbind the consumer from repos'

    def setup_parser(self):
        super(Unbind, self).setup_parser()
        self.parser.add_option("--repoid", dest="repoid",
                       help="repo identifier")

    def run(self):
        consumerid = self.get_required_option('id')
        repoid = self.get_required_option('repoid')
        self.cconn.unbind(consumerid, repoid)
        self.repolib.update()
        print _(" successfully unsubscribed consumer [%s] from repo [%s]") % \
                (consumerid, repoid)


class AddKeyValue(ConsumerAction):

    name = 'add_keyvalue'
    plug = 'add key-value information to consumer'

    def setup_parser(self):
        super(AddKeyValue, self).setup_parser()
        self.parser.add_option("--key", dest="key",
                       help="key identifier")
        self.parser.add_option("--value", dest="value",
                       help="value corresponding to the key")

    def run(self):
        consumerid = self.get_required_option('id')
        key = self.get_required_option('key')
        value = self.get_required_option('value')
        self.cconn.add_key_value_pair(consumerid, key, value)
        print _(" successfully added key-value pair %s:%s") % (key, value)


class DeleteKeyValue(ConsumerAction):

    name = 'delete_keyvalue'
    plug = 'delete key-value information from consumer'

    def setup_parser(self):
        super(DeleteKeyValue, self).setup_parser()
        self.parser.add_option("--key", dest="key",
                       help="key identifier")

    def run(self):
        consumerid = self.get_required_option('id')
        key = self.get_required_option('key')
        self.cconn.delete_key_value_pair(consumerid, key)
        print _(" successfully deleted key: %s") % key


class History(ConsumerAction):

    name = 'history'
    plug = 'view the consumer history'

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
        consumerid = self.get_required_option('id')
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
            type_name = entry['type_name']
            event_type = constants.CONSUMER_HISTORY_EVENT_TYPES.get(type_name, type_name)
            # Common event details
            print constants.CONSUMER_HISTORY_ENTRY % \
                  (event_type, json_utils.parse_date(entry['timestamp']), entry['originator'])
            # Based on the type of event, add on the event specific details. Otherwise,
            # just throw an empty line to account for the blank line that's added
            # by the details rendering.
            if type_name == 'repo_bound' or type_name == 'repo_unbound':
                print constants.CONSUMER_HISTORY_REPO % (entry['details']['repo_id'])
            if type_name == 'package_installed' or type_name == 'package_uninstalled':
                print constants.CONSUMER_HISTORY_PACKAGES
                for package_nvera in entry['details']['package_nveras']:
                    print '  %s' % package_nvera
            print ''

# consumer command ------------------------------------------------------------

class Consumer(BaseCore):

    _default_actions = ('info', 'list', 'create', 'delete', 'update',
                        'bind', 'unbind', 'add_keyvalue', 'delete_keyvalue',
                        'history')

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
