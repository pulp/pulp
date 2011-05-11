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
from pulp.client import constants
from pulp.client.api.cds import CDSAPI
from pulp.client.core.base import Action, Command
from pulp.client.core.utils import print_header, parse_interval_schedule
from pulp.common import dateutils



# -- utilities ---------------------------------------------------------------------

def _print_cds(cds):
    if cds['repo_ids']:
        repo_list = ', '.join(cds['repo_ids'])
    else:
        repo_list = _('None')

    if cds['last_sync'] is None:
        formatted_date = _('Never')
    else:
        formatted_date = dateutils.parse_iso8601_datetime(cds['last_sync'])

    stat = cds['heartbeat']
    if stat[0]:
        responding = _('Yes')
    else:
        responding = _('No')
    if stat[1]:
        last_heartbeat = dateutils.parse_iso8601_datetime(stat[1])
    else:
        last_heartbeat = stat[1]
    print(constants.CDS_INFO % \
        (cds['hostname'],
         cds['name'],
         cds['description'],
         repo_list,
         formatted_date,
         responding,
         last_heartbeat,))

# -- commands ----------------------------------------------------------------------

class Cds(Command):

    description = _('CDS instance management actions')

# -- actions ----------------------------------------------------------------------

class CDSAction(Action):

    def __init__(self):
        super(CDSAction, self).__init__()
        self.cds_api = CDSAPI()


class Register(CDSAction):

    description = _('associates a CDS instance with the pulp server')

    def setup_parser(self):
        self.parser.add_option('--hostname', dest='hostname',
                               help=_('CDS hostname (required)'))
        self.parser.add_option('--name', dest='name',
                               help=_('display name'))
        self.parser.add_option('--description', dest='description',
                               help=_('description of the CDS'))

        schedule = OptionGroup(self.parser, _('CDS Sync Schedule'))
        schedule.add_option('--interval', dest='schedule_interval', default=None,
                            help=_('length of time between each run in iso8601 duration format'))
        schedule.add_option('--start', dest='schedule_start', default=None,
                            help=_('date and time of the first run in iso8601 combined date and time format'))
        schedule.add_option('--runs', dest='schedule_runs', default=None,
                            help=_('number of times to run the scheduled sync, ommitting implies running indefinitely'))
        self.parser.add_option_group(schedule)

    def run(self):
        # Collect user data
        hostname = self.get_required_option('hostname')
        name = self.opts.name
        description = self.opts.description
        schedule = parse_interval_schedule(self.opts.schedule_interval,
                                           self.opts.schedule_start,
                                           self.opts.schedule_runs)
        try:
            self.cds_api.register(hostname, name, description, schedule)
            print(_('Successfully registered CDS [%s]' % hostname))
        except:
            print(_('Error attempting to register CDS [%s]' % hostname))
            print(_('Check that the CDS packages have been installed on the CDS and have been started'))

class Unregister(CDSAction):

    description = _('removes the association between the pulp server and a CDS')

    def setup_parser(self):
        self.parser.add_option('--hostname', dest='hostname',
                               help=_('CDS hostname (required)'))

    def run(self):
        hostname = self.get_required_option('hostname')
        self.cds_api.unregister(hostname)
        print(_('Successfully unregistered CDS [%s]' % hostname))

class List(CDSAction):

    description = _('lists all CDS instances associated with the pulp server')

    def run(self):
        all_cds = self.cds_api.list()

        print_header(_('CDS Instances'))

        for cds in all_cds:
            _print_cds(cds)

class Info(CDSAction):

    description = _('lists all CDS instances associated with the pulp server')

    def setup_parser(self):
        self.parser.add_option('--hostname', dest='hostname',
                               help=_('CDS hostname (required)'))

    def run(self):
        print_header(_('CDS'))
        hostname = self.get_required_option('hostname')
        cds = self.cds_api.cds(hostname)
        _print_cds(cds)


class History(CDSAction):

    description = _('displays the history of events on a CDS')

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

        results = self.cds_api.history(hostname, event_type=self.opts.event_type,
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
                  (event_type, dateutils.parse_iso8601_datetime(entry['timestamp']), entry['originator'])

            # Based on the type of event, add on the event specific details. Otherwise,
            # just throw an empty line to account for the blank line that's added
            # by the details rendering.

            if type_name == 'repo_associated' or type_name == 'repo_unassociated':
                print(_(constants.CONSUMER_HISTORY_REPO % entry['details']['repo_id']))

            if type_name == 'sync_finished' and \
               'error' in entry['details'] and \
               entry['details']['error'] is not None:
                print(_(constants.CDS_HISTORY_ENTRY_ERROR % entry['details']['error']))

class Associate(CDSAction):

    description = _('associates a repo with a CDS')

    def setup_parser(self):
        self.parser.add_option('--hostname', dest='hostname',
                               help=_('CDS hostname (required)'))
        self.parser.add_option('--repoid', dest='repoid',
                               help=_('repo identifier (required)'))

    def run(self):
        hostname = self.get_required_option('hostname')
        repo_id = self.get_required_option('repoid')

        result = self.cds_api.associate(hostname, repo_id)
        if result:
            print(_('Successfully associated CDS [%s] with repo [%s]' % (hostname, repo_id)))
        else:
            print(_('Error occurred during association, please check the server for more information'))

class Unassociate(CDSAction):

    description = _('unassociates a repo from a CDS')

    def setup_parser(self):
        self.parser.add_option('--hostname', dest='hostname',
                               help=_('CDS hostname (required)'))
        self.parser.add_option('--repoid', dest='repo_id',
                               help=_('repo identifier (required)'))

    def run(self):
        hostname = self.get_required_option('hostname')
        repo_id = self.get_required_option('repo_id')

        result = self.cds_api.unassociate(hostname, repo_id)
        if result:
            print(_('Successfully unassociated repo [%s] from CDS [%s]' % (repo_id, hostname)))
        else:
            print(_('Error occurred during association, please check the server for more information'))

class Sync(CDSAction):

    description = _('triggers an immediate sync between the pulp server and the given CDS')

    def setup_parser(self):
        self.parser.add_option('--hostname', dest='hostname',
                               help=_('CDS hostname (required)'))

    def run(self):
        hostname = self.get_required_option('hostname')

        self.cds_api.sync(hostname)
        print(_('Sync for CDS [%s] started' % hostname))
        print(_('Use "cds status" to check on the progress'))

class Status(CDSAction):

    description = _('displays the sync status of the given CDS')

    def setup_parser(self):
        self.parser.add_option('--hostname', dest='hostname',
                               help=_('CDS hostname (required)'))
        self.parser.add_option('--recent', dest='num_recent_syncs', default='1', action='store',
                               help=_('number of most recent syncs for which to show details'))

    def run(self):
        hostname = self.get_required_option('hostname')

        # Server data retrieval
        cds = self.cds_api.cds(hostname)
        sync_list = self.cds_api.sync_list(hostname)

        # Print the CDS details
        print_header(_('CDS Status'))
        _print_cds(cds)

        # Print details of the latest sync
        if sync_list is None or len(sync_list) == 0:
            return

        print_header(_('Most Recent Sync Tasks'))

        if int(self.opts.num_recent_syncs) < len(sync_list):
            upper_limit = int(self.opts.num_recent_syncs)
        else:
            upper_limit = len(sync_list)

        counter = 0
        while counter < upper_limit:
            if sync_list[counter]['start_time'] is not None:
                start_time = dateutils.parse_iso8601_datetime(sync_list[counter]['start_time'])
            else:
                start_time = _('Not Started')

            if sync_list[counter]['finish_time'] is not None:
                finish_time = dateutils.parse_iso8601_datetime(sync_list[counter]['finish_time'])
            else:
                finish_time = _('In Progress')

            print(_(constants.CDS_SYNC_DETAILS % (sync_list[counter]['state'], start_time, finish_time)))

            if sync_list[counter]['exception'] is not None:
                msg = _(constants.CDS_HISTORY_ENTRY_ERROR % sync_list[counter]['exception'])
                print(msg)

            if sync_list[counter]['traceback'] is not None:
                print(_('Traceback'))
                # The spaces here are to indent the traceback so it's more obvious that
                # it is part of the reporting and not a result of running the CLI command
                formatted = '    ' + '      '.join(sync_list[counter]['traceback'])
                print(formatted)

            counter += 1
