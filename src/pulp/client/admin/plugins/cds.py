#
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

import datetime
from gettext import gettext as _
import logging
from optparse import OptionGroup
import sys

from pulp.client.admin.plugin import AdminPlugin
from pulp.client.api.cds import CDSAPI
from pulp.client.api.server import ServerRequestError
from pulp.client.lib.utils import print_header, parse_interval_schedule
from pulp.client import constants
from pulp.client.pluginlib.command import Action, Command
from pulp.common import dateutils

# -- constants ----------------------------------------------------------------

LOG = logging.getLogger(__name__)

# If the next scheduled sync time is in the past, one of these two statuses
# will be returned in the next_scheduled_sync field, depending on if the sync
# is in the process of running (likely case) or is blocked waiting on the
# server to free up threads. The caller should translate these statuses into
# human readable notifications of the state. See the _next_scheduled_sync docs
# for usage.
SYNC_WAITING = 'sync-waiting'
SYNC_RUNNING = 'sync-running'
SYNC_MISSING = 'sync-missing'

# Mapping of state to user-friendly display
STATE_TRANSLATIONS = {
    'finished'  : 'Success',
    'scheduled' : 'Scheduled',
    'running'   : 'Running',
    'error'     : 'Error',
    'timed out' : 'Timed Out',
}

# -- utilities ----------------------------------------------------------------

def _print_cds(cds, next_sync=None):
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

    sync_schedule = cds['sync_schedule']

    # This is wonky but has to do with how the APIs are structured that next
    # sync isn't available in the CDS list, so rather than hammer the server
    # with more calls we omit it in most cases
    if next_sync is None:
        print(constants.CDS_INFO % \
            (cds['name'],
             cds['hostname'],
             cds['description'],
             cds['cluster_id'],
             sync_schedule,
             repo_list,
             formatted_date,
             responding,
             last_heartbeat,))
    else:
        print(constants.CDS_DETAILED_INFO % \
            (cds['name'],
             cds['hostname'],
             cds['description'],
             cds['cluster_id'],
             sync_schedule,
             repo_list,
             next_sync,
             formatted_date,
             responding,
             last_heartbeat,))


# -- actions ----------------------------------------------------------------------

class CDSAction(Action):

    def __init__(self, cfg):
        super(CDSAction, self).__init__(cfg)
        self.cds_api = CDSAPI()


class Register(CDSAction):

    name = "register"
    description = _('associates a CDS instance with the pulp server')

    def setup_parser(self):
        self.parser.add_option('--hostname', dest='hostname',
                               help=_('CDS hostname (required)'))
        self.parser.add_option('--name', dest='name',
                               help=_('display name'))
        self.parser.add_option('--description', dest='description',
                               help=_('description of the CDS'))
        self.parser.add_option('--cluster_id', dest='cluster_id',
                               help=_('if specified, the CDS will belong to the given cluster'))

        schedule = OptionGroup(self.parser, _('CDS Sync Schedule'))
        schedule.add_option('--interval', dest='schedule_interval', default=None,
                            help=_('length of time between each run in iso8601 duration format: P[n]Y[n]M[n]DT[n]H[n]M[n]S (e.g. "P3Y6M4DT12H30M5S" for "three years, six months, four days, twelve hours, thirty minutes, and five seconds")'))
        schedule.add_option('--start', dest='schedule_start', default=None,
                            help=_('date and time of the first run in iso8601 combined date and time format (e.g. "2012-03-01T13:00:00Z"), omitting implies starting immediately'))
        schedule.add_option('--runs', dest='schedule_runs', default=None,
                            help=_('number of times to run the scheduled sync, omitting implies running indefinitely'))
        self.parser.add_option_group(schedule)

    def run(self):
        # Collect user data
        hostname = self.get_required_option('hostname')
        name = self.opts.name
        description = self.opts.description
        cluster_id = self.opts.cluster_id
        schedule = parse_interval_schedule(self.opts.schedule_interval,
                                           self.opts.schedule_start,
                                           self.opts.schedule_runs)
        try:
            self.cds_api.register(hostname, name, description, schedule, cluster_id)
            print(_('Successfully registered CDS [%s]' % hostname))
        except ServerRequestError, sre:

            # If the issue isn't a conflict, remind the user that the CDS packages
            # need to be installed and running
            if sre[0] != 409:
                print(_('Check that the CDS packages have been installed on the CDS and have been started'))

            raise sre, None, sys.exc_info()[2]

class Unregister(CDSAction):

    name = "unregister"
    description = _('removes the association between the Pulp server and a CDS')

    def setup_parser(self):
        self.parser.add_option('--hostname', dest='hostname',
                               help=_('CDS hostname (required)'))
        self.parser.add_option('--force', dest='force', action='store_true', default=False,
                               help=_('if specified, the CDS will be removed from the server regardless of whether or not the CDS receives the release call'))

    def run(self):
        hostname = self.get_required_option('hostname')
        self.cds_api.unregister(hostname, self.opts.force)
        print(_('Successfully unregistered CDS [%s]' % hostname))

class Update(CDSAction):

    name = "update"
    description = _('updates an existing CDS instance')

    def setup_parser(self):
        self.parser.add_option('--hostname', dest='hostname',
                               help=_('CDS hostname (required)'))
        self.parser.add_option('--name', dest='name',
                               help=_('display name'))
        self.parser.add_option('--description', dest='description',
                               help=_('description of the CDS'))
        self.parser.add_option('--cluster_id', dest='cluster_id',
                               help=_('assigns the CDS to the given group'))

        self.parser.add_option('--remove_cluster', dest='remove_cluster', action='store_true', default=False,
                               help=_('removes the CDS from a cluster if it is in one'))
        self.parser.add_option('--remove_sync_schedule', dest='remove_sync_schedule', action='store_true', default=False,
                               help=_('removes scheduled syncs for this CDS'))

        schedule = OptionGroup(self.parser, _('CDS Sync Schedule'))
        schedule.add_option('--interval', dest='schedule_interval', default=None,
                            help=_('length of time between each run in iso8601 duration format: P[n]Y[n]M[n]DT[n]H[n]M[n]S (e.g. "P3Y6M4DT12H30M5S" for "three years, six months, four days, twelve hours, thirty minutes, and five seconds")'))
        schedule.add_option('--start', dest='schedule_start', default=None,
                            help=_('date and time of the first run in iso8601 combined date and time format (e.g. "2012-03-01T13:00:00Z"), omitting implies starting immediately'))
        schedule.add_option('--runs', dest='schedule_runs', default=None,
                            help=_('number of times to run the scheduled sync, omitting implies running indefinitely'))
        self.parser.add_option_group(schedule)

    def run(self):
        hostname = self.get_required_option('hostname')

        schedule = parse_interval_schedule(self.opts.schedule_interval,
                                           self.opts.schedule_start,
                                           self.opts.schedule_runs)

        # Sanity checks
        if self.opts.cluster_id is not None and self.opts.remove_cluster:
            print(_('A cluster ID may not be specified while removing the cluster'))
            return

        if schedule is not None and self.opts.remove_sync_schedule:
            print(_('A sync schedule may not be specified while removing scheduled syncs'))
            return

        # Package updates into a single delta dict
        delta = {}

        if self.opts.name is not None:
            delta['name'] = self.opts.name
        if self.opts.description is not None:
            delta['description'] = self.opts.description

        if self.opts.cluster_id is not None:
            delta['cluster_id'] = self.opts.cluster_id
        elif self.opts.remove_cluster:
            delta['cluster_id'] = None

        if schedule is not None:
            delta['sync_schedule'] = schedule
        elif self.opts.remove_sync_schedule:
            delta['sync_schedule'] = None
            
        self.cds_api.update(hostname, delta)
        print(_('Successfully updated CDS [%s]' % hostname))
        
class List(CDSAction):

    name = "list"
    description = _('lists all CDS instances associated with the pulp server')

    def run(self):
        all_cds = self.cds_api.list()

        print_header(_('CDS Instances'))

        for cds in all_cds:
            _print_cds(cds)

class Info(CDSAction):

    name = "info"
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

    name = "history"
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

    name = "associate_repo"
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

    name = "unassociate_repo"
    description = _('unassociates a repo from a CDS')

    def setup_parser(self):
        self.parser.add_option('--hostname', dest='hostname',
                               help=_('CDS hostname (required)'))
        self.parser.add_option('--repoid', dest='repoid',
                               help=_('repo identifier (required)'))

    def run(self):
        hostname = self.get_required_option('hostname')
        repo_id = self.get_required_option('repoid')

        result = self.cds_api.unassociate(hostname, repo_id)
        if result:
            print(_('Successfully unassociated repo [%s] from CDS [%s]' % (repo_id, hostname)))
        else:
            print(_('Error occurred during association, please check the server for more information'))

class Sync(CDSAction):

    name = "sync"
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

    name = "status"
    description = _('displays the sync status of the given CDS')

    def setup_parser(self):
        self.parser.add_option('--hostname', dest='hostname',
                               help=_('CDS hostname (required)'))
        self.parser.add_option('--recent', dest='num_recent_syncs', default='1', action='store',
                               help=_('number of most recent syncs for which to show details'))

    def run(self):
        hostname = self.get_required_option('hostname')

        # -- Server Data Retrieval --------------
        cds = self.cds_api.cds(hostname)

        try:
            sync_list = self.cds_api.sync_list(hostname)
        except ServerRequestError, e:
            if e[0] == 404:
                sync_list = []
            else:
                raise e, None, sys.exc_info()[2]

        try:
            history_list = self.cds_api.sync_history(hostname)
        except ServerRequestError, e:
            if e[0] == 404:
                history_list = []
            else:
                raise e, None, sys.exc_info()[2]

        # -- Data Analysis ------------------
        next_sync_date = self._next_scheduled_sync(sync_list)

        # Next Sync
        if next_sync_date is SYNC_WAITING:
            next_sync = _('Awaiting Execution')
        elif next_sync_date is SYNC_RUNNING:
            next_sync = _('In Progress')
        elif next_sync_date is SYNC_MISSING:
            next_sync = _('Not Scheduled')
        else:
            next_sync = dateutils.parse_iso8601_datetime(next_sync_date)

        # -- Display ------------------------

        print_header(_('CDS Status'))
        _print_cds(cds, next_sync=next_sync)

        # Sync History
        print_header(_('Most Recent Sync Tasks'))
        
        if len(history_list) is 0:
            print _('The CDS has not yet been synchronized')
        else:
            history_list.sort(key=lambda x : x['finish_time'], reverse=True)

            # Apply limit restrictions
            if int(self.opts.num_recent_syncs) < len(history_list):
                upper_limit = int(self.opts.num_recent_syncs)
            else:
                upper_limit = len(history_list)

            # Render each item
            for i in range(0, upper_limit):
                item = history_list[i]
                start_time = item['start_time']
                finish_time = item['finish_time']
                sync_last_result = item['state']
                sync_last_exception = item['exception']
                sync_last_traceback = item['traceback']

                if sync_last_result is None:
                    last_result = 'Never'
                else:
                    last_result = STATE_TRANSLATIONS.get(sync_last_result, 'Unknown')

                if start_time is not None:
                    start_time = dateutils.parse_iso8601_datetime(start_time)

                if finish_time is not None:
                    finish_time = dateutils.parse_iso8601_datetime(finish_time)

                print('Start Time:     %s' % start_time)
                print('Finish Time:    %s' % finish_time)
                print('Result:         %s' % last_result)

                if item['exception'] is not None:
                    print('Exception:      ' + sync_last_exception)

                if item['traceback'] is not None:
                    print('Traceback:')
                    print('\n'.join(sync_last_traceback))

    def _next_scheduled_sync(self, task_list):
        """
        Examines the given task list to determine when the next sync will occur. There
        are three possible results from this call:

        - If the next sync time is in the future, that time will be returned.
        - If the next sync time is in the past and the task is currently executing,
          the SYNC_RUNNING constant is returned.
        - If the next sync time is in the past and the task is still waiting for the
          server resources to free up and run it, the SYNC_WAITING constant is returned.
        - If the sync list is empty, which shouldn't happen and likely represents an
          error, the SYNC_MISSING constant is returned.

        If multiple tasks are present in the given task list, the one with the earliest
        next sync time will be used.

        @param task_list: list of task objects retrieved from the server
        @type  task_list: list of dict

        @return: ISO formatted string describing the next scheduled sync time or one
                 of the SYNC_* constants to denote that the sync is in progress
        @rtype:  str
        """

        # This shouldn't happen, but just in case let's handle it specifically
        if task_list is None or len(task_list) == 0:
            return SYNC_MISSING

        # Sort them so the earliest executing task is first. This is necessary in the
        # case where there are two tasks on the queue, one for the normally scheduled
        # repo sync and another if the user has elected to manually trigger a sync.
        task_list.sort(key=lambda x : x['scheduled_time'])

        task = None
        for t in task_list:
            if t['scheduled_time'] is not None:
                task = t
                break

        if task is None:
            LOG.exception('No task with a valid scheduled time can be found')
            return SYNC_MISSING

        next_date = dateutils.parse_iso8601_datetime(task['scheduled_time'])

        if next_date < datetime.datetime.now(tz=dateutils.local_tz()):
            # The next sync was scheduled in the past. It's either waiting for server
            # time to run or is currently running, so figure out which.

            if task['state'] == 'waiting':
                return SYNC_WAITING
            elif task['state'] == 'running':
                return SYNC_RUNNING
            else:
                LOG.error('Unexpected task state found [%s]' % task['state'])
                LOG.error(task)
                return SYNC_MISSING # can't think of anything better to return here
        else:
            # Next sync is going to occur in the future, so just return that time
            return task['scheduled_time'] # the ISO formatted string, not the date object


# -- command ----------------------------------------------------------------------

class Cds(Command):

    name = "cds"
    description = _('CDS instance management actions')

    actions = [ Register,
                Unregister,
                Update,
                Associate,
                Unassociate,
                List,
                History,
                Sync,
                Status,
                Info ]

# -- plugin ----------------------------------------------------------------------

class CdsPlugin(AdminPlugin):

    name = "cds"
    commands = [ Cds ]
