# Copyright (c) 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""
Contains classes related to listing, creating, and deleting schedules on the
Pulp server. All classes in this module are agnostic of the resource and operation
being scheduled. Specific functionality is achieved by subclassing the
ScheduleStrategy class and instantiating the commands, using the strategy
to properly scope the calls.

In other words, this module should never contain any references to a specific
resource (e.g. repositories) or operation (e.g. sync).

When using the commands below, extra options may be added to them that
are related to the specific functionality being worked with. Those values
will be passed through to the strategy in keyword arguments for use in the
underlying API calls.
"""

import copy
from gettext import gettext as _
import logging

from pulp.client import parsers
from pulp.client.arg_utils import convert_boolean_arguments, convert_removed_options
from pulp.client.commands.options import OPTION_REPO_ID
from pulp.client.extensions.extensions import PulpCliCommand, PulpCliOption, PulpCliFlag
from pulp.client.validators import interval_iso6801_validator

# -- constants ----------------------------------------------------------------

# Command configuration
NAME_LIST = 'list'
DESC_LIST = _('lists schedules')

NAME_CREATE = 'create'
DESC_CREATE = _('creates a new schedule')

NAME_UPDATE = 'update'
DESC_UPDATE = _('updates an existing schedule')

NAME_DELETE = 'delete'
DESC_DELETE = _('deletes a schedule')

NAME_NEXT_RUN = 'next'
DESC_NEXT_RUN = _('displays the next time the operation will run across all schedules')

# Order for render_document_list
SCHEDULE_ORDER = ['schedule', 'id', 'enabled', 'last_run', 'next_run']
DETAILED_SCHEDULE_ORDER = ['schedule', 'id', 'enabled', 'remaining_runs',
                           'consecutive_failures', 'failure_threshold',
                           'first_run', 'last_run', 'next_run']

# Options
DESC_SCHEDULE_ID = _('identifies an existing schedule')
OPT_SCHEDULE_ID = PulpCliOption('--schedule-id', DESC_SCHEDULE_ID, required=True)

DESC_SCHEDULE = _('time to execute in iso8601 format '
                  '(yyyy-mm-ddThh:mm:ssZ/PiuT); the number of recurrences may '
                  'be specified in this value')
OPT_SCHEDULE = PulpCliOption('--schedule', DESC_SCHEDULE, aliases=['-s'], required=True,
                             validate_func=interval_iso6801_validator)

DESC_FAILURE_THRESHOLD = _('number of failures before the schedule is automatically '
                           'disabled; unspecified means the schedule will never '
                           'be automatically disabled')
OPT_FAILURE_THRESHOLD = PulpCliOption('--failure-threshold', DESC_FAILURE_THRESHOLD,
                                      aliases=['-f'], required=False,
                                      parse_func=parsers.pulp_parse_optional_positive_int)

DESC_ENABLED = _('if "false", the schedule will exist but will not trigger any '
                 'executions; defaults to true')
OPT_ENABLED = PulpCliOption('--enabled', DESC_ENABLED, required=False)

DESC_DETAILS = _('if specified, extra information (including its ID) '
                 'about the schedule is displayed')
FLAG_DETAILS = PulpCliFlag('--details', DESC_DETAILS)

DESC_QUIET = _('only output the next time without verbiage around it')
FLAG_QUIET = PulpCliFlag('--quiet', DESC_QUIET, aliases=['-q'])

LOG = logging.getLogger(__name__)

# -- reusable scheduling classes ----------------------------------------------

class ListScheduleCommand(PulpCliCommand):
    """
    Displays the schedules returned from the supplied strategy instance.
    """

    def __init__(self, context, strategy, name=NAME_LIST, description=DESC_LIST):
        PulpCliCommand.__init__(self, name, description, self.run)
        self.context = context
        self.strategy = strategy

        self.add_flag(FLAG_DETAILS)

    def run(self, **kwargs):
        self.context.prompt.render_title(_('Schedules'))

        schedules = self.strategy.retrieve_schedules(kwargs).response_body

        if len(schedules) is 0:
            m = _('There are no schedules defined for this operation.')
            self.context.prompt.render_paragraph(m)
            return

        for s in schedules:
            # Need to convert _id into id in each document
            s['id'] = s.pop('_id')

            if s['remaining_runs'] is None:
                s['remaining_runs'] = _('N/A')

        if kwargs['details']:
            order = filters = DETAILED_SCHEDULE_ORDER
        else:
            order = filters = SCHEDULE_ORDER

        self.context.prompt.render_document_list(schedules, order=order, filters=filters)


class CreateScheduleCommand(PulpCliCommand):
    """
    Creates a new schedule. This command will provide the basic pieces necessary
    to accept and parse a schedule and its associated configuration. Subclasses
    or instances of this class should add any extra options that need to be
    specified for the resource/operation at hand. The strategy instance will be
    passed all of the keyword arguments provided by the user to perform the
    actual schedule creation call.
    """

    def __init__(self, context, strategy, name=NAME_CREATE, description=DESC_CREATE):
        PulpCliCommand.__init__(self, name, description, self.run)
        self.context = context
        self.strategy = strategy

        self.add_option(OPT_SCHEDULE)
        self.add_option(OPT_FAILURE_THRESHOLD)

    def run(self, **kwargs):
        schedule = kwargs[OPT_SCHEDULE.keyword]
        failure_threshold = kwargs[OPT_FAILURE_THRESHOLD.keyword]
        enabled = True # we could ask but it just added clutter to the CLI, so default to true

        try:
            self.strategy.create_schedule(schedule, failure_threshold, enabled, kwargs)
            self.context.prompt.render_success_message(_('Schedule successfully created'))
        except ValueError, e:
            LOG.exception(e)
            self.context.prompt.render_failure_message(_('One or more values were invalid:'))
            self.context.prompt.render_failure_message(e[0])


class DeleteScheduleCommand(PulpCliCommand):
    """
    Prompts the user for the schedule to delete and calls the appropriate
    method in the strategy instance.
    """

    def __init__(self, context, strategy, name=NAME_DELETE, description=DESC_DELETE):
        PulpCliCommand.__init__(self, name, description, self.run)
        self.context = context
        self.strategy = strategy

        self.add_option(OPT_SCHEDULE_ID)

    def run(self, **kwargs):
        schedule_id = kwargs[OPT_SCHEDULE_ID.keyword]

        self.strategy.delete_schedule(schedule_id, kwargs)
        self.context.prompt.render_success_message(_('Schedule successfully deleted'))


class UpdateScheduleCommand(PulpCliCommand):
    """
    Provides options for manipulating the standard schedule configuration such
    as the schedule itself or whether or not it is enabled. Subclasses or'
    instances should add any extra options that are required. The corresponding
    strategy method will be invoked with all of the user specified arguments.

    """

    def __init__(self, context, strategy, name=NAME_UPDATE, description=DESC_UPDATE):
        PulpCliCommand.__init__(self, name, description, self.run)
        self.context = context
        self.strategy = strategy

        self.add_option(OPT_SCHEDULE_ID)
        self.add_option(OPT_FAILURE_THRESHOLD)
        self.add_option(OPT_ENABLED)

        schedule_copy = copy.copy(OPT_SCHEDULE)
        schedule_copy.required = False
        self.add_option(schedule_copy)

    def run(self, **kwargs):
        schedule_id = kwargs.pop(OPT_SCHEDULE_ID.keyword)
        ft = kwargs.pop(OPT_FAILURE_THRESHOLD.keyword, None)
        if ft:
            kwargs['failure_threshold'] = ft

        convert_removed_options(kwargs)
        convert_boolean_arguments([OPT_ENABLED.keyword], kwargs)

        self.strategy.update_schedule(schedule_id, **kwargs)
        self.context.prompt.render_success_message(_('Successfully updated schedule'))


class NextRunCommand(PulpCliCommand):
    """
    Calculates and displays the next time an operation will execute. This call
    will use the strategy's retrieve_schedules command to check across all
    existing schedules to determine which will execute next.
    """

    def __init__(self, context, strategy, name=NAME_NEXT_RUN, description=DESC_NEXT_RUN):
        PulpCliCommand.__init__(self, name, description, self.run)
        self.context = context
        self.strategy = strategy

        self.add_flag(FLAG_QUIET)

    def run(self, **kwargs):
        schedules = self.strategy.retrieve_schedules(kwargs).response_body

        if len(schedules) == 0:
            self.context.prompt.render_paragraph(_('There are no schedules defined for this operation.'))
            return

        sorted_schedules = sorted(schedules, key=lambda x : x['next_run'])
        next_schedule = sorted_schedules[0]

        if kwargs[FLAG_QUIET.keyword]:
            msg = next_schedule['next_run']
        else:
            msg_data = {
                'next_run' : next_schedule['next_run'],
                'schedule' : next_schedule['iso_schedule'],
            }
            template = _('The next scheduled run is at %(next_run)s driven by the '
                         'schedule %(schedule)s')
            msg = template % msg_data

        self.context.prompt.render_paragraph(msg)

# -- strategy classes ---------------------------------------------------------

class ScheduleStrategy(object):
    """
    Encapsulates the schedule related calls for a particular resource and operation.

    Subclasses of this class can hide the details of the specific type of schedule
    and its calls. The CLI handling code can then use instances of the class to
    provide common scheduling functionality across disparate resource types.

    The scope of this class should be a specific resource and operation. Subclasses
    should simply chain the calls into this class to the appropriate API; allow
    all exceptions and return values from the bindings to return to the caller
    as is.

    This class merely defines the API and should not be used directly (i.e. it's
    an interface in Python).
    """

    def create_schedule(self, schedule, failure_threshold, enabled, kwargs):
        """
        Creates a new schedule for the strategy's underlying resource and operation.

        Most schedules can have an override config specified when created. If
        applicable, this method should retrieve any user-specified values in
        kwargs that are relevant and correctly assemble them into the override
        config before creating the repository. If the user args are invalid,
        a ValueError should be raised with a user-presentable message (e.g.
        already i18n'ed) as the first argument so the scheduling UI can properly
        notify the user of the bad data.

        @param schedule: iso8601 formatted schedule
        @type  schedule: str

        @param failure_threshold: number of failures before the schedule is disabled
        @type  failure_threshold: int

        @param enabled: describes if the newly created schedule should be enabled immediatley
        @type  enabled: bool

        @param kwargs: all keyword args passed in by the user, retrieved from the framework
        @type  kwargs: dict

        @return: response object from the server call
        @rtype:  Response
        """
        raise NotImplementedError()

    def delete_schedule(self, schedule_id, kwargs):
        """
        Deletes the schedule with the given ID.

        @param schedule_id: unique identifier for the schedule resource
        @type  schedule_id: str

        @param kwargs: all keyword args passed in by the user, retrieved from the framework
        @type  kwargs: dict

        @return: response object from the server call
        @rtype:  Response
        """
        raise NotImplementedError()

    def retrieve_schedules(self, kwargs):
        """
        Returns a list of all schedules for the approprate resource.

        @param kwargs: all keyword args passed in by the user, retrieved from the framework
        @type  kwargs: dict

        @return: response object from the server call
        @rtype:  Response
        """
        raise NotImplementedError()

    def update_schedule(self, schedule_id, **kwargs):
        """
        Updates the given schedule with any changes specified. Only values to
        be changed will be included as keyword arguments, therefore None as
        a value is meant to be the actual value and not an indication to skip
        changing the property.

        @param schedule_id: identifies the schedule being changed
        @type  schedule_id: str

        @param kwargs: key value pairs only for values to be changed

        @return: response object from the server call
        @rtype:  Response
        """
        raise NotImplementedError()


class RepoScheduleStrategy(ScheduleStrategy):
    """
    This is a ScheduleStrategy that wraps repository API bindings.

    Please see ScheduleStrategy for the method documentation.
    """
    def __init__(self, api, type_id):
        """
        This __init__ method merely stores the api and type_id on self. The api argument should be
        a binding to a PulpAPI that has the following methods: add_schedule, delete_schedule,
        list_schedules, and update_schedules. Currently, only the SyncAPI and PublishAPI classes offer these
        method. The type_id should be an importer's or a distributor's type ID.

        :param api:     The PulpAPI binding class that this strategy class should wrap.
        :type  api:     pulp.bindings.base.PulpAPI
        :param type_id: An importer's or a distributor's ID, to be passed to the api bindings
        :type  type_id: basestring
        """
        super(RepoScheduleStrategy, self).__init__()
        self.api = api
        self.type_id = type_id

    def create_schedule(self, schedule, failure_threshold, enabled, kwargs):
        repo_id = kwargs[OPTION_REPO_ID.keyword]

        # Eventually we'll support passing in sync arguments to the scheduled
        # call. When we do, override_config will be created here from kwargs.
        override_config = {}

        return self.api.add_schedule(repo_id, self.type_id, schedule, override_config,
                                      failure_threshold, enabled)

    def delete_schedule(self, schedule_id, kwargs):
        repo_id = kwargs[OPTION_REPO_ID.keyword]
        return self.api.delete_schedule(repo_id, self.type_id, schedule_id)

    def retrieve_schedules(self, kwargs):
        repo_id = kwargs[OPTION_REPO_ID.keyword]
        return self.api.list_schedules(repo_id, self.type_id)

    def update_schedule(self, schedule_id, **kwargs):
        repo_id = kwargs.pop(OPTION_REPO_ID.keyword)
        return self.api.update_schedule(repo_id, self.type_id, schedule_id, **kwargs)
