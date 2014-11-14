import os
from gettext import gettext as _

from okaara.prompt import CLEAR_REMAINDER, COLOR_GREEN, COLOR_RED, MOVE_UP

from pulp.bindings.exceptions import NotFoundException
from pulp.client import validators
from pulp.client.commands.polling import PollingCommand
from pulp.client.commands.options import DESC_ID, OPTION_CONSUMER_ID
from pulp.client.commands.schedule import (DeleteScheduleCommand, ListScheduleCommand,
                                           CreateScheduleCommand, UpdateScheduleCommand,
                                           NextRunCommand, ScheduleStrategy)
from pulp.client.extensions.extensions import PulpCliOption, PulpCliSection


class ConsumerContentSection(PulpCliSection):
    def __init__(self, context, name=None, description=None):
        name = name or 'content'
        description = description or _('content installation management')
        super(ConsumerContentSection, self).__init__(name, description)

        for section_class in (ConsumerContentInstallSection,
                              ConsumerContentUpdateSection,
                              ConsumerContentUninstallSection):
            self.add_subsection(section_class(context))


class ConsumerContentInstallSection(PulpCliSection):
    def __init__(self, context, name=None, description=None):
        name = name or 'install'
        description = description or _('run or schedule a content unit installation task')
        super(ConsumerContentInstallSection, self).__init__(name, description)

        self.add_command(ConsumerContentInstallCommand(context))
        self.add_subsection(ConsumerContentSchedulesSection(context, 'install'))


class ConsumerContentInstallCommand(PollingCommand):
    """
    Base class that installs content of an arbitrary type to a consumer.
    """

    def __init__(self, context, name=None, description=None, progress_tracker=None):
        name = name or 'run'
        description = description or _('triggers an immediate content unit install on the consumer')
        super(ConsumerContentInstallCommand, self).__init__(name, description, self.run, context)

        self.add_consumer_option()
        self.add_content_options()
        self.add_install_options()

        self.progress_tracker = progress_tracker or ConsumerContentProgressTracker(context.prompt)
        self.api = context.server.consumer_content

    def add_consumer_option(self):
        """
        Override this method to a no-op to skip adding the consumer id option.
        This allows commands (such as the consumer command) to find the consumer
        id via other means than a command line option.
        """
        self.add_option(OPTION_CONSUMER_ID)

    def get_consumer_id(self, kwargs):
        """
        Override this method to provide the consumer id to the run method.
        """
        return kwargs[OPTION_CONSUMER_ID.keyword]

    def add_content_options(self):
        """
        Override this method to provide content-type specific content options.
        """
        self.add_option(OPTION_CONTENT_TYPE_ID)
        self.add_option(OPTION_CONTENT_UNIT)

    def add_install_options(self):
        """
        Override this method to provide content-type specific installation options.
        """
        pass

    def run(self, **kwargs):
        consumer_id = self.get_consumer_id(kwargs)
        options = self.get_install_options(kwargs)
        units = self.get_content_units(kwargs)

        try:
            response = self.api.install(consumer_id, units=units, options=options)

        except NotFoundException:
            msg = _('Consumer [ %(c)s ] not found') % {'c': consumer_id}
            self.context.prompt.render_failure_message(msg, tag='not-found')
            return os.EX_DATAERR

        else:
            task = response.response_body
            for task_id in [t.task_id for t in task.spawned_tasks]:
                msg = _('Install task created with id [ %(t)s ]') % {'t': task_id}
                self.context.prompt.render_success_message(msg)

            self.poll([task], kwargs)

    def get_install_options(self, kwargs):
        """
        Override this method to get content-type specific installation options
        from the keyword arguments passed to run.
        """
        return {}

    def get_content_units(self, kwargs):
        """
        Override this method to build custom content specification documents.
        """
        content_type_id = kwargs[OPTION_CONTENT_TYPE_ID.keyword]

        def _unit_dict(unit_name):
            return {'type_id': content_type_id,
                    'unit_key': {'name': unit_name}}

        units = map(_unit_dict, kwargs[OPTION_CONTENT_UNIT.keyword])
        return units

    def progress(self, task, spinner):
        self.progress_tracker.display(task.progress_report)

    def succeeded(self, task):
        msg = _('Install Succeeded')
        self.context.prompt.render_success_message(msg)

    def failed(self, task):
        msg = _('Install Failed')
        self.context.prompt.render_failure_message(msg)


class ConsumerContentUpdateSection(PulpCliSection):
    def __init__(self, context, name=None, description=None):
        name = name or 'update'
        description = description or _('run or schedule a content unit update task')
        super(ConsumerContentUpdateSection, self).__init__(name, description)

        self.add_command(ConsumerContentUpdateCommand(context))
        self.add_subsection(ConsumerContentSchedulesSection(context, 'update'))


class ConsumerContentUpdateCommand(PollingCommand):
    """
    Base class that updates content of an arbitrary type to a consumer.
    """

    def __init__(self, context, name=None, description=None, progress_tracker=None):
        name = name or 'run'
        description = description or _('triggers an immediate content unit update on a consumer')
        super(ConsumerContentUpdateCommand, self).__init__(name, description, self.run, context)

        self.add_consumer_option()
        self.add_content_options()
        self.add_update_options()

        self.progress_tracker = progress_tracker or ConsumerContentProgressTracker(context.prompt)
        self.api = context.server.consumer_content

    def add_consumer_option(self):
        """
        Override this method to a no-op to skip adding the consumer id option.
        This allows commands (such as the consumer command) to find the consumer
        id via other means than a command line option.
        """
        self.add_option(OPTION_CONSUMER_ID)

    def get_consumer_id(self, kwargs):
        """
        Override this method to provide the consumer id to the run method.
        """
        return kwargs[OPTION_CONSUMER_ID.keyword]

    def add_content_options(self):
        """
        Override this method to provide content-type specific content options.
        """
        self.add_option(OPTION_CONTENT_TYPE_ID)
        self.add_option(OPTION_CONTENT_UNIT)

    def add_update_options(self):
        """
        Override this method to provide content-type specific update options.
        """
        pass

    def run(self, **kwargs):
        consumer_id = self.get_consumer_id(kwargs)
        options = self.get_update_options(kwargs)
        units = self.get_content_units(kwargs)

        if not units:
            msg = _('No content units specified')
            self.context.prompt.render_failure_message(msg)
            return

        try:
            response = self.api.update(consumer_id, units=units, options=options)

        except NotFoundException:
            msg = _('Consumer [ %(c)s ] not found') % {'c': consumer_id}
            self.context.prompt.render_failure_message(msg, tag='not-found')
            return os.EX_DATAERR

        else:
            task = response.response_body
            for task_id in [t.task_id for t in task.spawned_tasks]:
                msg = _('Update task created with id [ %(t)s ]') % {'t': task_id}
                self.context.prompt.render_success_message(msg)

            self.poll([task], kwargs)

    def get_update_options(self, kwargs):
        """
        Override this method to get content-type specific update options
        from the keyword arguments passed to run.
        """
        return {}

    def get_content_units(self, kwargs):
        """
        Override this method to build custom content specification documents.
        """
        content_type_id = kwargs[OPTION_CONTENT_TYPE_ID.keyword]

        def _unit_dict(unit_name):
            return {'type_id': content_type_id,
                    'unit_key': {'name': unit_name}}

        units = map(_unit_dict, kwargs.get(OPTION_CONTENT_UNIT.keyword) or [])
        return units

    def progress(self, task, spinner):
        self.progress_tracker.display(task.progress_report)

    def succeeded(self, task):
        msg = _('Update Succeeded')
        self.context.prompt.render_success_message(msg)

    def failed(self, task):
        msg = _('Update Failed')
        self.context.prompt.render_failure_message(msg)


class ConsumerContentUninstallSection(PulpCliSection):
    def __init__(self, context, name=None, description=None):
        name = name or 'uninstall'
        description = description or _('run or schedule a content unit removal task')
        super(ConsumerContentUninstallSection, self).__init__(name, description)

        self.add_command(ConsumerContentUninstallCommand(context))
        self.add_subsection(ConsumerContentSchedulesSection(context, 'uninstall'))


class ConsumerContentUninstallCommand(PollingCommand):
    """
    Base class that uninstalls content of an arbitrary type from a consumer.
    """

    def __init__(self, context, name=None, description=None, progress_tracker=None):
        name = name or 'run'
        description = description or _('triggers an immediate content unit removal on a consumer')
        super(ConsumerContentUninstallCommand, self).__init__(name, description, self.run, context)

        self.add_consumer_option()
        self.add_content_options()
        self.add_uninstall_options()

        self.progress_tracker = progress_tracker or ConsumerContentProgressTracker(context.prompt)
        self.api = context.server.consumer_content

    def add_consumer_option(self):
        """
        Override this method to a no-op to skip adding the consumer id option.
        This allows commands (such as the consumer command) to find the consumer
        id via other means than a command line option.
        """
        self.add_option(OPTION_CONSUMER_ID)

    def get_consumer_id(self, kwargs):
        """
        Override this method to provide the consumer id to the run method.
        """
        return kwargs[OPTION_CONSUMER_ID.keyword]

    def add_content_options(self):
        """
        Override this method to provide content-type specific content options.
        """
        self.add_option(OPTION_CONTENT_TYPE_ID)
        self.add_option(OPTION_CONTENT_UNIT)

    def add_uninstall_options(self):
        """
        Override this method to provide content-type specific uninstall options.
        """
        pass

    def run(self, **kwargs):
        consumer_id = self.get_consumer_id(kwargs)
        options = self.get_uninstall_options(kwargs)
        units = self.get_content_units(kwargs)

        try:
            response = self.api.uninstall(consumer_id, units=units, options=options)

        except NotFoundException:
            msg = _('Consumer [ %(c)s ] not found') % {'c': consumer_id}
            self.context.prompt.render_failure_message(msg, tag='not-found')
            return os.EX_DATAERR

        else:
            task = response.response_body
            for task_id in [t.task_id for t in task.spawned_tasks]:
                msg = _('Uninstall task created with id [ %(t)s ]') % {'t': task_id}
                self.context.prompt.render_success_message(msg)

            self.poll([task], kwargs)

    def get_uninstall_options(self, kwargs):
        """
        Override this method to get content-type specific uninstall options
        from the keyword arguments passed to run.
        """
        return {}

    def get_content_units(self, kwargs):
        """
        Override this method to build custom content specification documents.
        """
        content_type_id = kwargs[OPTION_CONTENT_TYPE_ID.keyword]

        def _unit_dict(unit_name):
            return {'type_id': content_type_id,
                    'unit_key': {'name': unit_name}}

        units = map(_unit_dict, kwargs[OPTION_CONTENT_UNIT.keyword])
        return units

    def progress(self, task, spinner):
        self.progress_tracker.display(task.progress_report)

    def succeeded(self, task):
        msg = _('Uninstall Succeeded')
        self.context.prompt.render_success_message(msg)

    def failed(self, task):
        msg = _('Uninstall Failed')
        self.context.prompt.render_failure_message(msg)


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
