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

from gettext import gettext as _

from pulp.client.api.consumer import ConsumerAPI
from pulp.client.api.service import ServiceAPI
from pulp.client import constants
from pulp.client.lib import repolib
from pulp.client.lib import utils
from pulp.client.lib.repo_file import RepoFile
from pulp.client.pluginlib.command import Action, Command
from pulp.common import dateutils

# base consumer action --------------------------------------------------------

class ConsumerAction(Action):

    def __init__(self, cfg):
        super(ConsumerAction, self).__init__(cfg)
        self.consumer_api = ConsumerAPI()

# consumer actions ------------------------------------------------------------

class Unregister(ConsumerAction):

    name = "unregister"
    description = _('unregister the consumer')

    def run(self, consumerid):
        self.consumer_api.delete(consumerid)


class Bind(ConsumerAction):

    name = "bind"
    description = _('bind the consumer to listed repos')

    def setup_parser(self):
        super(Bind, self).setup_parser()
        self.parser.add_option("--repoid", dest="repoid",
                       help=_("repo identifier (required)"))

    def run(self, consumerid, repoid):
        bind_data = self.consumer_api.bind(consumerid, repoid)
        return bind_data


class Unbind(ConsumerAction):

    name = "unbind"
    description = _('unbind the consumer from repos')

    def setup_parser(self):
        super(Unbind, self).setup_parser()
        self.parser.add_option("--repoid", dest="repoid",
                       help=_("repo identifier (required)"))

    def run(self, consumerid, repoid):
        repoid = self.get_required_option('repoid')
        self.consumer_api.unbind(consumerid, repoid)


class History(ConsumerAction):

    name = "history"
    description = _('view the consumer history')

    def setup_parser(self):
        super(History, self).setup_parser()
        self.parser.add_option('--event_type', dest='event_type',
                               help=_('limits displayed history entries to the given type; \
                                       supported types: \
                                       ("consumer_registered", \
                                       "consumer_unregistered", "repo_bound", "repo_unbound", \
                                       "package_installed", \
                                       "package_uninstalled", \
                                       "errata_installed", "profile_changed")'))
        self.parser.add_option('--limit', dest='limit',
                               help=_('limits displayed history entries to the given amount (must be greater than zero)'))
        self.parser.add_option('--sort', dest='sort',
                               help=_('indicates the sort direction ("ascending" or "descending") based on the entry\'s timestamp'))
        self.parser.add_option('--start_date', dest='start_date',
                               help=_('only return entries that occur on or after the given date (format: yyyy-mm-dd)'))
        self.parser.add_option('--end_date', dest='end_date',
                               help=_('only return entries that occur on or before the given date (format: yyyy-mm-dd)'))

    def run(self, consumerid):
        # Assemble the query parameters
        query_params = {
            'event_type' : self.opts.event_type,
            'limit' : self.opts.limit,
            'sort' : self.opts.sort,
            'start_date' : self.opts.start_date,
            'end_date' : self.opts.end_date,
        }
        results = self.consumer_api.history(consumerid, query_params)
        utils.print_header(_("Consumer History"))
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

    name = "consumer"
    description = _('consumer specific actions to pulp server')
