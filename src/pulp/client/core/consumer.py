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

import os
import urlparse
from gettext import gettext as _
from optparse import SUPPRESS_HELP

from pulp.client import constants
from pulp.client import json_utils
from pulp.client import utils
from pulp.client.config import Config
from pulp.client.connection import ConsumerConnection
from pulp.client.core.base import Action, Command
from pulp.client.core.utils import print_header, system_exit
from pulp.client.credentials import Consumer as ConsumerBundle
from pulp.client.package_profile import PackageProfile
from pulp.client.repolib import RepoLib



_cfg = Config()

# base consumer action --------------------------------------------------------

class ConsumerAction(Action):

    def __init__(self):
        super(ConsumerAction, self).__init__()
        self.repolib = RepoLib()

    def setup_connections(self):
        self.cconn = ConsumerConnection()

    def setup_parser(self):
        help = _("consumer identifier eg: foo.example.com (required)")
        default = None
        id = self.getconsumerid()
        if id is not None:
            help = SUPPRESS_HELP
            default = id
        self.parser.add_option("--id", dest="id", default=default, help=help)

# consumer actions ------------------------------------------------------------

class List(ConsumerAction):

    description = _('list all known consumers')

    def setup_parser(self):
        self.parser.add_option("--key", dest="key", help=_("key identifier"))
        self.parser.add_option("--value", dest="value",
                               help=_("value corresponding to the key"))

    def run(self):
        key = self.opts.key
        value = self.opts.value
        cons = self.cconn.consumers()
        baseurl = "%s://%s:%s" % (_cfg.server.scheme, _cfg.server.host,
                                  _cfg.server.port)
        for con in cons:
            con['package_profile'] = urlparse.urljoin(baseurl,
                                                      con['package_profile'])
        if key is None:
            print_header(_("Consumer Information"))
            for con in cons:
                print constants.AVAILABLE_CONSUMER_INFO % \
                        (con["id"], con["description"], con["repoids"],
                         con["package_profile"], con["key_value_pairs"])
            system_exit(os.EX_OK)

        if value is None:
            print _("Consumers with key : %s") % key
            for con in cons:
                key_value_pairs = self.cconn.get_keyvalues(con["id"])
                if key not in key_value_pairs.keys():
                    continue
                print "%s  -  %s : %s" % (con["id"], key, key_value_pairs[key])
            system_exit(os.EX_OK)

        print _("Consumers with %s : %s") % (key, value)
        for con in cons:
            key_value_pairs = self.cconn.get_keyvalues(con["id"])
            if (key in key_value_pairs.keys()) and \
                    (key_value_pairs[key] == value):
                print con["id"]


class Info(ConsumerAction):

    description = _('list of accessible consumer info')

    def run(self):
        id = self.get_required_option('id')
        cons = self.cconn.consumer(id)
        pkgs = ""
        for pkg in cons['package_profile'].values():
            for pkgversion in pkg:
                pkgs += " " + utils.getRpmName(pkgversion)
        cons['package_profile'] = pkgs
        print_header(_("Consumer Information"))
        for con in cons:
            print constants.AVAILABLE_CONSUMER_INFO % \
                    (con["id"], con["description"], con["repoids"],
                     con["package_profile"])


class Create(ConsumerAction):

    description = _('create a consumer')

    def setup_parser(self):
        # always provide --id option for create, even on registered clients
        self.parser.add_option('--id', dest='id',
                               help=_("consumer identifier eg: foo.example.com (required)"))
        self.parser.add_option("--description", dest="description",
                               help=_("consumer description eg: foo's web server"))

    def run(self):
        id = self.get_required_option('id')
        description = getattr(self.opts, 'description', id)
        consumer = self.cconn.create(id, description)
        cert_dict = self.cconn.certificate(id)
        key = cert_dict['private_key']
        crt = cert_dict['certificate']
        bundle = ConsumerBundle()
        bundle.write(key, crt)
        pkginfo = PackageProfile().getPackageList()
        self.cconn.profile(id, pkginfo)
        print _("Successfully created consumer [ %s ]") % consumer['id']


class Delete(ConsumerAction):

    description = _('delete the consumer')

    def run(self):
        consumerid = self.get_required_option('id')
        self.cconn.delete(consumerid)
        print _("Successfully deleted consumer [%s]") % consumerid


class Update(ConsumerAction):

    description = _('update consumer profile')

    def run(self):
        consumer_id = self.get_required_option('id')
        pkginfo = PackageProfile().getPackageList()
        self.cconn.profile(consumer_id, pkginfo)
        print _("Successfully updated consumer [%s] profile") % consumer_id


class Bind(ConsumerAction):

    description = _('bind the consumer to listed repos')

    def setup_parser(self):
        super(Bind, self).setup_parser()
        self.parser.add_option("--repoid", dest="repoid",
                       help=_("repo identifier (required)"))

    def run(self):
        myid = self.getconsumerid()
        consumerid = self.get_required_option('id')
        repoid = self.get_required_option('repoid')
        self.cconn.bind(consumerid, repoid)
        if myid and myid == consumerid:
            self.repolib.update()
        print _("Successfully subscribed consumer [%s] to repo [%s]") % \
                (consumerid, repoid)


class Unbind(ConsumerAction):

    description = _('unbind the consumer from repos')

    def setup_parser(self):
        super(Unbind, self).setup_parser()
        self.parser.add_option("--repoid", dest="repoid",
                       help=_("repo identifier (required)"))

    def run(self):
        myid = self.getconsumerid()
        consumerid = self.get_required_option('id')
        repoid = self.get_required_option('repoid')
        self.cconn.unbind(consumerid, repoid)
        if myid and myid == consumerid:
            self.repolib.update()
        print _("Successfully unsubscribed consumer [%s] from repo [%s]") % \
                (consumerid, repoid)


class AddKeyValue(ConsumerAction):

    description = _('add key-value information to consumer')

    def setup_parser(self):
        super(AddKeyValue, self).setup_parser()
        self.parser.add_option("--key", dest="key",
                               help=_("key identifier (required)"))
        self.parser.add_option("--value", dest="value",
                               help=_("value corresponding to the key (required)"))

    def run(self):
        consumerid = self.get_required_option('id')
        key = self.get_required_option('key')
        value = self.get_required_option('value')
        self.cconn.add_key_value_pair(consumerid, key, value)
        print _("Successfully added key-value pair %s:%s") % (key, value)


class DeleteKeyValue(ConsumerAction):

    description = _('delete key-value information from consumer')

    def setup_parser(self):
        super(DeleteKeyValue, self).setup_parser()
        self.parser.add_option("--key", dest="key",
                       help=_("key identifier (required)"))

    def run(self):
        consumerid = self.get_required_option('id')
        key = self.get_required_option('key')
        self.cconn.delete_key_value_pair(consumerid, key)
        print _("Successfully deleted key: %s") % key


class UpdateKeyValue(ConsumerAction):

    description = _('update key-value information of a consumer')

    def setup_parser(self):
        super(UpdateKeyValue, self).setup_parser()
        self.parser.add_option("--key", dest="key",
                       help=_("key identifier (required)"))
        self.parser.add_option("--value", dest="value",
                       help=_("value corresponding to the key (required)"))

    def run(self):
        consumerid = self.get_required_option('id')
        key = self.get_required_option('key')
        value = self.get_required_option('value')
        self.cconn.update_key_value_pair(consumerid, key, value)
        print _("Successfully updated key-value pair %s:%s") % (key, value)


class GetKeyValues(ConsumerAction):

    description = _('get key-value attributes for given consumer')

    def run(self):
        consumerid = self.get_required_option('id')
        keyvalues = self.cconn.get_keyvalues(consumerid)
        print_header(_("Consumer Key-values"))
        print constants.CONSUMER_KEY_VALUE_INFO % ("KEY", "VALUE")
        print "--------------------------------------------"
        for key in keyvalues.keys():
            print constants.CONSUMER_KEY_VALUE_INFO % (key, keyvalues[key])
        system_exit(os.EX_OK)       



class History(ConsumerAction):

    description = _('view the consumer history')

    def setup_parser(self):
        super(History, self).setup_parser()
        self.parser.add_option('--event_type', dest='event_type',
                               help=_('limits displayed history entries to the given type'))
        self.parser.add_option('--limit', dest='limit',
                               help=_('limits displayed history entries to the given amount (must be greater than zero)'))
        self.parser.add_option('--sort', dest='sort',
                               help=_('indicates the sort direction ("ascending" or "descending") based on the entry\'s timestamp'))
        self.parser.add_option('--start_date', dest='start_date',
                               help=_('only return entries that occur on or after the given date (format: yyyy-mm-dd)'))
        self.parser.add_option('--end_date', dest='end_date',
                               help=_('only return entries that occur on or before the given date (format: yyyy-mm-dd)'))

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
        print_header(_("Consumer History"))
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

# consumer command ------------------------------------------------------------

class Consumer(Command):

    description = _('consumer specific actions to pulp server')
