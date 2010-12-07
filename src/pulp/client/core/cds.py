#!/usr/bin/python
#
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

# Python
from gettext import gettext as _

# Pulp
from pulp.client import constants, json_utils
from pulp.client.connection import CdsConnection
from pulp.client.core.base import Action, Command
from pulp.client.core.utils import print_header


# commands ----------------------------------------------------------------------

class Cds(Command):

    description = _('CDS instance management actions')

# actions ----------------------------------------------------------------------

class Register(Action):

    description = _('associates a CDS instance with the pulp server')

    def setup_connections(self):
        self.cds_conn = CdsConnection()

    def setup_parser(self):
        self.parser.add_option('--hostname', dest='hostname',
                               help=_('CDS hostname (required)'))
        self.parser.add_option('--name', dest='name',
                               help=_('display name'))
        self.parser.add_option('--description', dest='description',
                               help=_('description of the CDS'))

    def run(self):
        # Collect user data
        hostname = self.get_required_option('hostname')
        name = self.opts.name
        description = self.opts.description

        self.cds_conn.register(hostname, name, description)
        print(_('Successfully registered CDS [%s]' % hostname))

class Unregister(Action):

    description = _('removes the association between the pulp server and a CDS')

    def setup_connections(self):
        self.cds_conn = CdsConnection()

    def setup_parser(self):
        self.parser.add_option('--hostname', dest='hostname',
                               help=_('CDS hostname (required)'))

    def run(self):
        hostname = self.get_required_option('hostname')
        self.cds_conn.unregister(hostname)
        print(_('Successfully unregistered CDS [%s]' % hostname))

class List(Action):

    description = _('lists all CDS instances associated with the pulp server')

    def setup_connections(self):
        self.cds_conn = CdsConnection()

    def run(self):
        all_cds = self.cds_conn.list()

        print_header(_('CDS Instances'))

        for cds in all_cds:
            if cds['repo_ids']:
                repo_list = ', '.join(cds['repo_ids'])
            else:
                repo_list = _('None')
            print(constants.CDS_INFO % (cds['hostname'], cds['name'], cds['description'], repo_list, cds['last_sync']))

class History(Action):

    description = _('displays the history of events on a CDS')

    def setup_connections(self):
        self.cds_conn = CdsConnection()

    def setup_parser(self):
        self.parser.add_option('--hostname', dest='hostname',
                               help=_('CDS hostname (required)'))
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
        hostname = self.get_required_option('hostname')

        results = self.cds_conn.history(hostname, event_type=self.opts.event_type,
                                        limit=self.opts.limit, sort=self.opts.sort,
                                        start_date=self.opts.start_date,
                                        end_date=self.opts.end_date)

        print_header(_("CDS History"))
        for entry in results:
            # Attempt to translate the programmatic event type name to a user readable one
            type_name = entry['type_name']
            event_type = constants.CDS_HISTORY_EVENT_TYPES.get(type_name, type_name)

            # Common event details
            print constants.CDS_HISTORY_ENTRY % \
                  (event_type, json_utils.parse_date(entry['timestamp']), entry['originator'])

            # Based on the type of event, add on the event specific details. Otherwise,
            # just throw an empty line to account for the blank line that's added
            # by the details rendering.
            if type_name == 'repo_associated' or type_name == 'repo_unassociated':
                print constants.CONSUMER_HISTORY_REPO % (entry['details']['repo_id'])

class Associate(Action):

    description = _('associates a repo with a CDS')

    def setup_connections(self):
        self.cds_conn = CdsConnection()

    def setup_parser(self):
        self.parser.add_option('--hostname', dest='hostname',
                               help=_('CDS hostname (required)'))
        self.parser.add_option('--repoid', dest='repoid',
                               help=_('repo identifier (required)'))

    def run(self):
        hostname = self.get_required_option('hostname')
        repo_id = self.get_required_option('repoid')

        result = self.cds_conn.associate(hostname, repo_id)
        if result:
            print(_('Successfully associated CDS [%s] with repo [%s]' % (hostname, repo_id)))
        else:
            print(_('Error occurred during association, please check the server for more information'))

class Unassociate(Action):

    description = _('unassociates a repo from a CDS')

    def setup_connections(self):
        self.cds_conn = CdsConnection()

    def setup_parser(self):
        self.parser.add_option('--hostname', dest='hostname',
                               help=_('CDS hostname (required)'))
        self.parser.add_option('--repoid', dest='repo_id',
                               help=_('repo identifier (required)'))

    def run(self):
        hostname = self.get_required_option('hostname')
        repo_id = self.get_required_option('repo_id')

        result = self.cds_conn.unassociate(hostname, repo_id)
        if result:
            print(_('Successfully associated CDS [%s] with repo [%s]' % (hostname, repo_id)))
        else:
            print(_('Error occurred during association, please check the server for more information'))

class Sync(Action):

    description = _('triggers an immediate sync between the pulp server and the given CDS')

    def setup_connections(self):
        self.cds_conn = CdsConnection()

    def setup_parser(self):
        self.parser.add_option('--hostname', dest='hostname',
                               help=_('CDS hostname (required)'))

    def run(self):
        hostname = self.get_required_option('hostname')

        result = self.cds_conn.sync(hostname)
        print(result)
