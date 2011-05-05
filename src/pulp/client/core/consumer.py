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

from pulp.client import constants
from pulp.client import utils
from pulp.client.api.consumer import ConsumerAPI
from pulp.client.api.service import ServiceAPI
from pulp.client.config import Config
from pulp.client.core.base import Action, Command
from pulp.client.core.utils import print_header, system_exit
from pulp.client.credentials import Consumer as ConsumerBundle
from pulp.client.package_profile import PackageProfile
import pulp.client.repolib as repolib
from pulp.client.repo_file import RepoFile
from pulp.common import dateutils



_cfg = Config()

# base consumer action --------------------------------------------------------

class ConsumerAction(Action):

    def __init__(self, is_consumer_client=False):
        super(ConsumerAction, self).__init__()
        self.consumer_api = ConsumerAPI()
        self.is_consumer_client = is_consumer_client
        self.consumerid = None

    def setup_parser(self):
        help = _("consumer identifier eg: foo.example.com (required)")
        consumerid = self.getconsumerid()

        # Do not accept consumerid when running pulp-client consumer commands on existing consumer
        if consumerid is not None and self.is_consumer_client:
            self.consumerid = consumerid
        else:
            self.parser.add_option("--id", dest="id", help=help)

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
        cons = self.consumer_api.consumers()
        baseurl = "%s://%s:%s" % (_cfg.server.scheme, _cfg.server.host,
                                  _cfg.server.port)
        for con in cons:
            con['package_profile'] = urlparse.urljoin(baseurl,
                                                      con['package_profile'])
        if key is None:
            print_header(_("Consumer Information"))
            for con in cons:
                kvpair = []
                key_value_pairs = self.consumer_api.get_keyvalues(con["id"])
                for k, v in key_value_pairs.items():
                    kvpair.append("%s  :  %s" % (str(k), str(v)))
                stat = con['heartbeat']
                if stat[0]:
                    responding = _('Yes')
                else:
                    responding = _('No')
                if stat[1]:
                    last_heartbeat = dateutils.parse_iso8601_datetime(stat[1])
                else:
                    last_heartbeat = stat[1]
                print constants.AVAILABLE_CONSUMER_INFO % \
                        (con["id"],
                         con["description"], \
                         con["repoids"].keys(),
                         responding,
                         last_heartbeat,
                         '\n \t\t\t'.join(kvpair[:]))
            system_exit(os.EX_OK)

        if value is None:
            print _("Consumers with key : %s") % key
            for con in cons:
                key_value_pairs = self.consumer_api.get_keyvalues(con["id"])
                if key not in key_value_pairs.keys():
                    continue
                print "%s  -  %s : %s" % (con["id"], key, key_value_pairs[key])
            system_exit(os.EX_OK)

        print _("Consumers with %s : %s") % (key, value)
        for con in cons:
            key_value_pairs = self.consumer_api.get_keyvalues(con["id"])
            if (key in key_value_pairs.keys()) and \
                    (key_value_pairs[key] == value):
                print con["id"]


class Info(ConsumerAction):

    description = _('list of accessible consumer info')

    def setup_parser(self):
        super(Info, self).setup_parser()
        self.parser.add_option('--show-profile', action="store_true",
                               help=_("show package profile information associated with this consumer"))

    def run(self):
        id = self.get_required_option('id')
        cons = self.consumer_api.consumer(id)
        kvpair = []
        key_value_pairs = self.consumer_api.get_keyvalues(cons["id"])
        for k, v in key_value_pairs.items():
            kvpair.append("%s  :  %s" % (str(k), str(v)))
        stat = cons['heartbeat']
        if stat[0]:
            responding = _('Yes')
        else:
            responding = _('No')
        if stat[1]:
            last_heartbeat = dateutils.parse_iso8601_datetime(stat[1])
        else:
            last_heartbeat = stat[1]
        print_header(_("Consumer Information"))
        print constants.AVAILABLE_CONSUMER_INFO % \
                (cons["id"],
                 cons["description"],
                 cons["repoids"].keys(),
                 responding,
                 last_heartbeat,
                 '\n \t\t\t'.join(kvpair[:]))
        if not self.opts.show_profile:
            system_exit(os.EX_OK)
        # Construct package profile list
        print_header(_("Package Profile associated with consumer [%s]" % id))
        pkgs = ""
        for pkg in cons['package_profile']:
            pkgs += " \n" + utils.getRpmName(pkg)

        system_exit(os.EX_OK, pkgs)

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
        consumer = self.consumer_api.create(id, description)
        cert_dict = self.consumer_api.certificate(id)
        key = cert_dict['private_key']
        crt = cert_dict['certificate']
        bundle = ConsumerBundle()
        bundle.write(key, crt)
        pkginfo = PackageProfile().getPackageList()
        self.consumer_api.profile(id, pkginfo)
        print _("Successfully created consumer [ %s ]") % consumer['id']


class Delete(ConsumerAction):

    description = _('delete the consumer')

    def run(self):
        if not self.consumerid:
            consumerid = self.get_required_option('id')
        else:
            consumerid = self.consumerid
        self.consumer_api.delete(consumerid)
        if self.consumerid:
            repo_file = RepoFile(_cfg.client.repo_file)
            repo_file.delete()

            bundle = ConsumerBundle()
            bundle.delete()
        print _("Successfully deleted consumer [%s]") % consumerid


class Update(ConsumerAction):

    description = _('update consumer profile')

    def run(self):
        consumer_id = self.getconsumerid()
        if not consumer_id:
            system_exit(os.EX_NOHOST, _("This client is not registered; cannot perform an update"))
        pkginfo = PackageProfile().getPackageList()
        try:
            self.consumer_api.profile(consumer_id, pkginfo)
            print _("Successfully updated consumer [%s] profile") % consumer_id
        except:
            system_exit(os.EX_DATAERR, _("Error updating consumer [%s]." % consumer_id))


class Bind(ConsumerAction):

    description = _('bind the consumer to listed repos')

    def setup_parser(self):
        super(Bind, self).setup_parser()
        self.parser.add_option("--repoid", dest="repoid",
                       help=_("repo identifier (required)"))

    def run(self):
        if not self.consumerid:
            consumerid = self.get_required_option('id')
        else:
            consumerid = self.consumerid
        repoid = self.get_required_option('repoid')
        bind_data = self.consumer_api.bind(consumerid, repoid)

        if bind_data:
            if self.consumerid:
                mirror_list_filename = repolib.mirror_list_filename(_cfg.client.mirror_list_dir, repoid)
                repolib.bind(_cfg.client.repo_file, mirror_list_filename, _cfg.client.gpg_keys_dir,
                             repoid, bind_data['repo'], bind_data['host_urls'], bind_data['gpg_keys'])

            print _("Successfully subscribed consumer [%s] to repo [%s]") % \
                  (consumerid, repoid)
        else:
            print _('Repo [%s] already bound to the consumer' % repoid)


class Unbind(ConsumerAction):

    description = _('unbind the consumer from repos')

    def setup_parser(self):
        super(Unbind, self).setup_parser()
        self.parser.add_option("--repoid", dest="repoid",
                       help=_("repo identifier (required)"))

    def run(self):
        if not self.consumerid:
            consumerid = self.get_required_option('id')
        else:
            consumerid = self.consumerid
        repoid = self.get_required_option('repoid')
        self.consumer_api.unbind(consumerid, repoid)
        if self.consumerid:
            mirror_list_filename = repolib.mirror_list_filename(_cfg.client.mirror_list_dir, repoid)
            repolib.unbind(_cfg.client.repo_file, mirror_list_filename, _cfg.client.gpg_keys_dir, repoid)
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
        self.consumer_api.add_key_value_pair(consumerid, key, value)
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
        self.consumer_api.delete_key_value_pair(consumerid, key)
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
        self.consumer_api.update_key_value_pair(consumerid, key, value)
        print _("Successfully updated key-value pair %s:%s") % (key, value)


class GetKeyValues(ConsumerAction):

    description = _('get key-value attributes for given consumer')

    def run(self):
        consumerid = self.get_required_option('id')
        keyvalues = self.consumer_api.get_keyvalues(consumerid)
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
                               help=_('limits displayed history entries to the given type; \
                                       supported types: ("consumer_created", "consumer_deleted", "repo_bound", "repo_unbound", \
                                       "package_installed", "package_uninstalled", "errata_installed", "profile_changed")'))
        self.parser.add_option('--limit', dest='limit',
                               help=_('limits displayed history entries to the given amount (must be greater than zero)'))
        self.parser.add_option('--sort', dest='sort',
                               help=_('indicates the sort direction ("ascending" or "descending") based on the entry\'s timestamp'))
        self.parser.add_option('--start_date', dest='start_date',
                               help=_('only return entries that occur on or after the given date (format: yyyy-mm-dd)'))
        self.parser.add_option('--end_date', dest='end_date',
                               help=_('only return entries that occur on or before the given date (format: yyyy-mm-dd)'))

    def run(self):
        if not self.consumerid:
            consumerid = self.get_required_option('id')
        else:
            consumerid = self.consumerid
        # Assemble the query parameters
        query_params = {
            'event_type' : self.opts.event_type,
            'limit' : self.opts.limit,
            'sort' : self.opts.sort,
            'start_date' : self.opts.start_date,
            'end_date' : self.opts.end_date,
        }
        results = self.consumer_api.history(consumerid, query_params)
        print_header(_("Consumer History"))
        for entry in results:
            # Attempt to translate the programmatic event type name to a user readable one
            type_name = entry['type_name']
            event_type = constants.CONSUMER_HISTORY_EVENT_TYPES.get(type_name, type_name)
            # Common event details
            print constants.CONSUMER_HISTORY_ENTRY % \
                  (event_type, dateutils.parse_iso8601_datetime(entry['timestamp']), entry['originator'])
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
