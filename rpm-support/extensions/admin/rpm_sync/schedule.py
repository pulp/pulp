# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
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

When using the generic commands below, extra options may be added to them that
are related to the specific functionality being worked with. Those values
will be passed through to the strategy in keyword arguments for use in the
underlying API calls.

Eventually this will move to a more general location outside of repositories
directly, we just need to figure out what that looks like first.
"""

from gettext import gettext as _
import logging

from pulp.client.extensions.extensions import PulpCliCommand
from pulp.client.arg_utils import convert_boolean_arguments, convert_removed_options

# -- constants ----------------------------------------------------------------

# Order for render_document_list
SCHEDULE_ORDER = ['schedule', 'id', 'enabled', 'last_run', 'next_run']
DETAILED_SCHEDULE_ORDER = ['schedule', 'id', 'enabled', 'remaining_runs', 'consecutive_failures', 'failure_threshold', 'first_run', 'last_run', 'next_run']

SCHEDULE_DESCRIPTION = _('time to execute (with optional recurrence) in iso8601 format (yyyy-mm-ddThh:mm:ssZ/PiuT)')
FAILURE_THRESHOLD_DESCRIPTION = _('number of failures before the schedule is automatically disabled; unspecified '\
                                  'means the schedule will never be automatically disabled')
ENABLED_DESCRIPTION = _('controls whether or not the operation will execute at its scheduled time')

LOG = logging.getLogger(__name__)

# -- reusable scheduling classes ----------------------------------------------

class ListScheduleCommand(PulpCliCommand):

    def __init__(self, context, strategy, name, description):
        PulpCliCommand.__init__(self, name, description, self.list)
        self.context = context
        self.strategy = strategy

        self.create_flag('--details', _('if specified, extra information (including its server ID) about the schedule is displayed'))

    def list(self, **kwargs):
        self.context.prompt.render_title(_('Schedules'))

        schedules = self.strategy.retrieve_schedules(kwargs).response_body

        if len(schedules) is 0:
            self.context.prompt.render_paragraph(_('There are no schedules defined for this operation.'))
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

    def __init__(self, context, strategy, name, description):
        PulpCliCommand.__init__(self, name, description, self.add)
        self.context = context
        self.strategy = strategy

        self.create_option('--schedule', SCHEDULE_DESCRIPTION, aliases=['-s'], required=True)
        self.create_option('--failure-threshold', FAILURE_THRESHOLD_DESCRIPTION, aliases=['-f'], required=False)

    def add(self, **kwargs):
        schedule = kwargs['schedule']
        failure_threshold = kwargs['failure-threshold']
        enabled = True # we could ask but it just added clutter to the CLI, so default to true

        try:
            response = self.strategy.create_schedule(schedule, failure_threshold, enabled, kwargs)
            self.context.prompt.render_success_message('Schedule successfully created')
        except ValueError, e:
            LOG.exception(e)
            self.context.prompt.render_failure_message(_('One or more values were invalid:'))
            self.context.prompt.render_failure_message(e[0])


class DeleteScheduleCommand(PulpCliCommand):

    def __init__(self, context, strategy, name, description):
        PulpCliCommand.__init__(self, name, description, self.delete)
        self.context = context
        self.strategy = strategy

        d = 'identifies the schedule to delete'
        self.create_option('--schedule-id', _(d), required=True)

    def delete(self, **kwargs):
        schedule_id = kwargs['schedule-id']

        response = self.strategy.delete_schedule(schedule_id, kwargs)
        self.context.prompt.render_success_message(_('Schedule successfully deleted'))

class UpdateScheduleCommand(PulpCliCommand):

    def __init__(self, context, strategy, name, description):
        PulpCliCommand.__init__(self, name, description, self.update)
        self.context = context
        self.strategy = strategy

        d = 'identifies the schedule to update'
        self.create_option('--schedule-id', _(d), required=True)
        self.create_option('--schedule', SCHEDULE_DESCRIPTION, aliases=['-s'], required=False)
        self.create_option('--failure-threshold', FAILURE_THRESHOLD_DESCRIPTION, aliases=['-f'], required=False)
        self.create_option('--enabled', ENABLED_DESCRIPTION, aliases=['-e'], required=False)

    def update(self, **kwargs):
        schedule_id = kwargs.pop('schedule-id')
        ft = kwargs.pop('failure-threshold', None)
        if ft:
            kwargs['failure_threshold'] = ft

        convert_removed_options(kwargs)
        convert_boolean_arguments(['enabled'], kwargs)

        response = self.strategy.update_schedule(schedule_id, **kwargs)
        self.context.prompt.render_success_message(_('Successfully updated schedule'))

class NextRunCommand(PulpCliCommand):

    def __init__(self, context, strategy, name, description):
        PulpCliCommand.__init__(self, name, description, self.next_run)
        self.context = context
        self.strategy = strategy

        self.create_flag('--quiet', _('only output the next time without verbiage around it'), aliases=['-q'])

    def next_run(self, **kwargs):
        schedules = self.strategy.retrieve_schedules(kwargs).response_body

        if len(schedules) is 0:
            self.context.prompt.render_paragraph(_('There are no schedules defined for this operation.'))
            return

        sorted_schedules = sorted(schedules, key=lambda x : x['next_run'])
        next_schedule = sorted_schedules[0]

        if kwargs['quiet']:
            msg = next_schedule['next_run']
        else:
            msg_data = {
                'next_run' : next_schedule['next_run'],
                'schedule' : next_schedule['schedule'],
            }
            template = 'The next scheduled run is at %(next_run)s driven by the ' \
            'schedule %(schedule)s'
            msg = _(template) % msg_data

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