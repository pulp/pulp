#
# Pulp Registration and subscription module
# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

import os
import urlparse
from gettext import gettext as _

from pulp.client.admin.config import AdminConfig
from pulp.client.admin.plugin import AdminPlugin
from pulp.client.api.consumer import ConsumerAPI
from pulp.client.api.service import ServiceAPI
from pulp.client.lib.utils import print_header, system_exit
from pulp.client import constants
from pulp.client.lib import utils
from pulp.client.plugins.consumer import (ConsumerAction, Consumer,
    Unregister, Bind, Unbind, History)
from pulp.client.lib.repo_file import RepoFile
from pulp.common import dateutils
from pulp.common.capabilities import AgentCapabilities
from rhsm.profile import get_profile
import pulp.client.lib.repolib as repolib

# base consumer action --------------------------------------------------------

class ConsumerAdminAction(ConsumerAction):

    def setup_parser(self):
        help = _("consumer identifier eg: foo.example.com (required)")
        self.parser.add_option("--id", dest="id", help=help)

# consumer actions ------------------------------------------------------------

class List(ConsumerAdminAction):

    name = "list"
    description = _('list all known consumers')

    def setup_parser(self):
        self.parser.add_option("--key", dest="key", help=_("key identifier"))
        self.parser.add_option("--value", dest="value",
                               help=_("value corresponding to the key"))

    def run(self):
        key = self.opts.key
        value = self.opts.value
        all = self.consumer_api.consumers()
        # ALL
        if key is None:
            for cons in all:
                Info.print_consumer(self.consumer_api, cons)
            system_exit(os.EX_OK)
        # BY KEY ONLY
        if value is None:
            print _("Consumers with key : %s") % key
            for con in cons:
                key_value_pairs = self.consumer_api.get_keyvalues(con["id"])
                if key in key_value_pairs.keys():
                    Info.print_consumer(self.consumer_api, cons)
            system_exit(os.EX_OK)
        # BY KEY & VALUE
        print _("Consumers with %s : %s") % (key, value)
        for con in cons:
            key_value_pairs = self.consumer_api.get_keyvalues(con["id"])
            if (key in key_value_pairs.keys()) and (key_value_pairs[key] == value):
                Info.print_consumer(self.consumer_api, cons)
            system_exit(os.EX_OK)

class Info(ConsumerAdminAction):

    name = "info"
    description = _('list of accessible consumer info')

    @classmethod
    def agent_status(cls, cons):
        stat = cons['heartbeat']
        if stat[0]:
            responding = _('Yes')
        else:
            responding = _('No')
        if stat[1]:
            last_heartbeat = dateutils.parse_iso8601_datetime(stat[1])
        else:
            last_heartbeat = stat[1]
        return (responding, last_heartbeat)

    @classmethod
    def capflags(cls, capabilities):
        flags = []
        for k in capabilities.names():
            if capabilities[k]:
                x = 'x'
            else:
                x = ' '
            flags.append('  [%s] %s' % (x, k))
        return '\n'.join(flags)

    @classmethod
    def print_consumer(cls, api, cons, show_profile=False):
        kvpair = []
        capabilities = AgentCapabilities(cons['capabilities'])
        key_value_pairs = api.get_keyvalues(cons["id"])
        for k, v in key_value_pairs.items():
            kvpair.append("%s  :  %s" % (str(k), str(v)))
        print_header(_("Consumer Information"))
        if capabilities.heartbeat():
            responding, last_heartbeat = cls.agent_status(cons)
            print constants.AVAILABLE_CONSUMER_INFO % \
                    (cons["id"],
                     cons["description"],
                     cls.capflags(capabilities),
                     sorted(cons["repoids"].keys()),
                     responding,
                     last_heartbeat,
                     '\n \t\t\t'.join(kvpair[:]))
        else:
            print constants.CONSUMER_INFO_NO_HEARTBEAT % \
                    (cons["id"],
                     cons["description"],
                     cls.capflags(capabilities),
                     cons["repoids"].keys(),
                     '\n \t\t\t'.join(kvpair[:]))
        if show_profile:
            print _("Package Profile")
            pkgs = []
            for pkg in sorted(cons['package_profile']):
                pkgs.append('  %s' % utils.getRpmName(pkg))
            print '\n'.join(pkgs)

    def setup_parser(self):
        super(Info, self).setup_parser()
        self.parser.add_option('--show-profile', action="store_true",
                               help=_("show package profile information associated with this consumer"))

    def run(self):
        id = self.get_required_option('id')
        cons = self.consumer_api.consumer(id)
        self.print_consumer(self.consumer_api, cons, self.opts.show_profile)
        return


class AddKeyValue(ConsumerAdminAction):

    name = "add_keyvalue"
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


class DeleteKeyValue(ConsumerAdminAction):

    name = "delete_keyvalue"
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


class UpdateKeyValue(ConsumerAdminAction):

    name = "update_keyvalue"
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


class GetKeyValues(ConsumerAdminAction):

    name = "get_keyvalues"
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

# consumer overridden actions  ------------------------------------------------------------

class AdminUnregister(Unregister):

    def setup_parser(self):
        super(AdminUnregister, self).setup_parser()
        help = _("consumer identifier eg: foo.example.com (required)")
        self.parser.add_option("--id", dest="id", help=help)

    def run(self):
        consumerid = self.get_required_option('id')
        Unregister.run(self, consumerid)
        print _("Successfully unregistered consumer [%s]") % consumerid


class AdminBind(Bind):

    def setup_parser(self):
        super(AdminBind, self).setup_parser()
        help = _("consumer identifier eg: foo.example.com (required)")
        self.parser.add_option("--id", dest="id", help=help)

    def run(self):
        consumerid = self.get_required_option('id')
        repoid = self.get_required_option('repoid')
        bind_data = Bind.run(self, consumerid, repoid)

        if bind_data:
            print _("Successfully subscribed consumer [%s] to repo [%s]") % \
                  (consumerid, repoid)
        else:
            print _('Repo [%s] already bound to the consumer' % repoid)


class AdminUnbind(Unbind):

    def setup_parser(self):
        super(AdminUnbind, self).setup_parser()
        help = _("consumer identifier eg: foo.example.com (required)")
        self.parser.add_option("--id", dest="id", help=help)

    def run(self):
        consumerid = self.get_required_option('id')
        repoid = self.get_required_option('repoid')
        Unbind.run(self, consumerid, repoid)
        print _("Successfully unsubscribed consumer [%s] from repo [%s]") % \
                (consumerid, repoid)


class AdminHistory(History):

    def setup_parser(self):
        super(AdminHistory, self).setup_parser()
        help = _("consumer identifier eg: foo.example.com (required)")
        self.parser.add_option("--id", dest="id", help=help)

    def run(self):
        consumerid = self.get_required_option('id')
        History.run(self, consumerid)

# consumer command ------------------------------------------------------------

class AdminConsumer(Consumer):

    actions = [ List,
                Info,
                AdminUnregister,
                AdminBind,
                AdminUnbind,
                AddKeyValue,
                DeleteKeyValue,
                GetKeyValues,
                UpdateKeyValue,
                AdminHistory ]

# consumer plugin ------------------------------------------------------------

class ConsumerPlugin(AdminPlugin):

    name = "consumer"
    commands = [ AdminConsumer ]
