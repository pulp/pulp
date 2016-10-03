from gettext import gettext as _

from okaara.prompt import CLEAR_REMAINDER, COLOR_GREEN, COLOR_RED, MOVE_UP

from pulp.client import validators
from pulp.client.commands.options import DESC_ID, OPTION_CONSUMER_ID
from pulp.client.commands.schedule import (DeleteScheduleCommand, ListScheduleCommand,
                                           CreateScheduleCommand, UpdateScheduleCommand,
                                           NextRunCommand, ScheduleStrategy)
from pulp.client.extensions.extensions import PulpCliOption, PulpCliSection


class ConsumerContentProgressTracker(object):
    def __init__(self, prompt):
        self.prompt = prompt
        self.next_step = 0
        self.details = None
        self.ok = prompt.color(_('OK'), COLOR_GREEN)
        self.failed = prompt.color(_('FAILED'), COLOR_RED)

    def reset(self):
        self.next_step = 0
        self.details = None

    def display(self, report):
        # report can be None or {}
        if report:
            self.display_steps(report['steps'])
            self.display_details(report['details'])

    def display_steps(self, steps):
        num_steps = len(steps)
        self.backup()
        for i in xrange(self.next_step, num_steps):
            self.write_step(steps[i])
            self.next_step = i

    def backup(self):
        lines = 1
        if self.details:
            lines += len(self.details.split('\n'))
        self.prompt.move(MOVE_UP % lines)
        self.prompt.clear(CLEAR_REMAINDER)

    def write_step(self, step):
        name, status = step

        if status is None:
            self.prompt.write(name)
            return

        status = (status and self.ok) or self.failed
        self.prompt.write('%-40s[ %s ]' % (name, status))

    def display_details(self, details):
        action = details.get('action')
        content_unit = details.get('content_unit')
        error = details.get('error')

        self.details = None

        if action is not None:
            self.details = '+12%s: %s' % (action, content_unit)
            self.prompt.write(self.details)

        if error is not None:
            action = _('Error')
            self.details = '+12%s: %s' % (action, error)
            self.prompt.write(self.details, COLOR_RED)


class ConsumerContentSchedulesSection(PulpCliSection):
    def __init__(self, context, action, name=None, description=None):
        name = name or 'schedules'
        description = description or _('manage consumer content %(a)s schedules') % {'a': action}
        super(ConsumerContentSchedulesSection, self).__init__(name, description)

        self.add_command(ConsumerContentListScheduleCommand(context, action))
        self.add_command(ConsumerContentCreateScheduleCommand(context, action))
        self.add_command(ConsumerContentDeleteScheduleCommand(context, action))
        self.add_command(ConsumerContentNextRunCommand(context, action))


class ConsumerContentListScheduleCommand(ListScheduleCommand):
    def __init__(self, context, action, strategy=None, name=None, description=None):
        strategy = strategy or ConsumerContentScheduleStrategy(context, action)
        name = name or 'list'
        description = description or _('list scheduled %(a)s operations') % {'a': action}
        super(ConsumerContentListScheduleCommand, self).__init__(context, strategy, name,
                                                                 description)

        self.add_option(OPTION_CONSUMER_ID)


class ConsumerContentCreateScheduleCommand(CreateScheduleCommand):
    def __init__(self, context, action, strategy=None, name=None, description=None):
        strategy = strategy or ConsumerContentScheduleStrategy(context, action)
        name = name or 'create'
        description = description or _('adds a new scheduled %(a)s operation') % {'a': action}
        super(ConsumerContentCreateScheduleCommand, self).__init__(context, strategy, name,
                                                                   description)

        self.add_option(OPTION_CONSUMER_ID)
        self.add_option(OPTION_CONTENT_TYPE_ID)
        self.add_option(OPTION_CONTENT_UNIT)


class ConsumerContentDeleteScheduleCommand(DeleteScheduleCommand):
    def __init__(self, context, action, strategy=None, name=None, description=None):
        strategy = strategy or ConsumerContentScheduleStrategy(context, action)
        name = name or 'delete'
        description = description or _('deletes a %(a)s schedule') % {'a': action}
        super(ConsumerContentDeleteScheduleCommand, self).__init__(context, strategy, name,
                                                                   description)

        self.add_option(OPTION_CONSUMER_ID)


class ConsumerContentUpdateScheduleCommand(UpdateScheduleCommand):
    def __init__(self, context, action, strategy=None, name=None, description=None):
        strategy = strategy or ConsumerContentScheduleStrategy(context, action)
        name = name or 'update'
        description = description or _('update an existing %(a)s schedule') % {'a': action}
        super(ConsumerContentUpdateScheduleCommand, self).__init__(context, strategy, name,
                                                                   description)

        self.add_option(OPTION_CONSUMER_ID)


class ConsumerContentNextRunCommand(NextRunCommand):
    def __init__(self, context, action, strategy=None, name=None, description=None):
        strategy = strategy or ConsumerContentScheduleStrategy(context, action)
        name = name or 'next'
        description = description or _('displays the next scheduled %(a)s for a'
                                       ' consumer') % {'a': action}
        super(ConsumerContentNextRunCommand, self).__init__(context, strategy, name, description)

        self.add_option(OPTION_CONSUMER_ID)


class ConsumerContentScheduleStrategy(ScheduleStrategy):
    def __init__(self, context, action):
        super(ConsumerContentScheduleStrategy, self).__init__()

        self.context = context
        self.action = action
        self.api = context.server.consumer_content_schedules

    def create_schedule(self, schedule, failure_threshold, enabled, kwargs):
        consumer_id = kwargs[OPTION_CONSUMER_ID.keyword]
        content_type_id = kwargs[OPTION_CONTENT_TYPE_ID.keyword]

        options = {}

        def _unit_dict(unit_name):
            return {'type_id': content_type_id,
                    'unit_key': {'name': unit_name}}

        units = map(_unit_dict, kwargs[OPTION_CONTENT_UNIT.keyword])

        return self.api.add_schedule(self.action, consumer_id, schedule, units,
                                     failure_threshold, enabled, options)

    def delete_schedule(self, schedule_id, kwargs):
        consumer_id = kwargs[OPTION_CONSUMER_ID.keyword]
        return self.api.delete_schedule(self.action, consumer_id, schedule_id)

    def retrieve_schedules(self, kwargs):
        consumer_id = kwargs[OPTION_CONSUMER_ID.keyword]
        return self.api.list_schedules(self.action, consumer_id)

    def update_schedule(self, schedule_id, **kwargs):
        consumer_id = kwargs.pop(OPTION_CONSUMER_ID.keyword)
        return self.api.update_schedule(self.action, consumer_id, schedule_id, **kwargs)


OPTION_CONTENT_TYPE_ID = PulpCliOption('--content-type-id',
                                       DESC_ID,
                                       required=True,
                                       validate_func=validators.id_validator)

OPTION_CONTENT_UNIT = PulpCliOption('--content-unit',
                                    _('content unit id; may be repeated for '
                                      'multiple content units'),
                                    required=True,
                                    allow_multiple=True)
