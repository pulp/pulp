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

import copy
import time
from gettext import gettext as _

from pulp.client.extensions.extensions import PulpCliSection, PulpCliCommand, \
    PulpCliOption, PulpCliFlag
from pulp.bindings.exceptions import NotFoundException
from pulp.client.search import SearchCommand

# -- framework hook -----------------------------------------------------------

def initialize(context):
    consumer_section = AdminConsumerSection(context)
    consumer_section.add_subsection(ContentSection(context))
    consumer_section.add_subsection(ConsumerGroupSection(context))
    context.cli.add_section(consumer_section)
    
# -- common exceptions --------------------------------------------------------

class InvalidConfig(Exception):
    """
    During parsing of the user supplied arguments, this will indicate a
    malformed set of values. The message in the exception (e[0]) is formatted
    and i18n'ed to be displayed directly to the user.
    """
    pass

# -- sections -----------------------------------------------------------------

class AdminConsumerSection(PulpCliSection):

    def __init__(self, context):
        PulpCliSection.__init__(self, 'consumer', 'consumer lifecycle (list, update, etc.) commands')

        self.context = context
        self.prompt = context.prompt # for easier access

        # Common Options
        consumer_id_option = PulpCliOption('--consumer-id', 'uniquely identifies the consumer; only alphanumeric, -, and _ allowed', required=True)
        name_option = PulpCliOption('--display-name', 'user-readable display name for the consumer', required=False)
        description_option = PulpCliOption('--description', 'user-readable description for the consumer', required=False)

        # Update Command
        update_command = PulpCliCommand('update', 'changes metadata on an existing consumer', self.update)
        update_command.add_option(consumer_id_option)
        update_command.add_option(name_option)
        update_command.add_option(description_option)
        d =  'adds/updates/deletes notes to programmatically identify the consumer; '
        d += 'key-value pairs must be separated by an equal sign (e.g. key=value); multiple notes can '
        d += 'be changed by specifying this option multiple times; notes are deleted by '
        d += 'specifying "" as the value'
        update_command.add_option(PulpCliOption('--note', d, required=False, allow_multiple=True))
        self.add_command(update_command)

        # Unregister Command
        unregister_command = PulpCliCommand('unregister', 'unregisters a consumer', self.unregister)
        unregister_command.add_option(PulpCliOption('--consumer-id', 'identifies the consumer to be unregistered', required=True))
        self.add_command(unregister_command)

        # List Command
        list_command = PulpCliCommand('list', 'lists summary of consumers registered to the Pulp server', self.list)
        list_command.add_option(PulpCliFlag('--details', 'if specified, all the consumer information is displayed'))
        list_command.add_option(PulpCliFlag('--bindings', 'if specified, the bindings information is displayed'))
        list_command.add_option(PulpCliOption('--fields', 'comma-separated list of consumer fields; if specified, only the given fields will displayed', required=False))
        self.add_command(list_command)

        # Search Command
        self.add_command(SearchCommand(self.search))

        # Bind Command
        bind_command = PulpCliCommand('bind', 'binds a consumer to a repository distributor for consuming published content', self.bind)
        bind_command.add_option(PulpCliOption('--consumer-id', 'consumer id', required=True))
        bind_command.add_option(PulpCliOption('--repo-id', 'repository id', required=True))
        bind_command.add_option(PulpCliOption('--distributor-id', 'distributor id', required=True))
        self.add_command(bind_command)

        # Unbind Command
        unbind_command = PulpCliCommand('unbind', 'unbinds a consumer from a repository distributor', self.unbind)
        unbind_command.add_option(PulpCliOption('--consumer-id', 'consumer id', required=True))
        unbind_command.add_option(PulpCliOption('--repo-id', 'repository id', required=True))
        unbind_command.add_option(PulpCliOption('--distributor-id', 'distributor id', required=True))
        self.add_command(unbind_command)
        
        # History Retrieval Command
        history_command = PulpCliCommand('history', 'lists history of a consumer', self.history)
        history_command.add_option(PulpCliOption('--consumer-id', 'consumer id', required=True))
        d = 'limits displayed history entries to the given type;'
        d += 'supported types: ("consumer_registered", "consumer_unregistered", "repo_bound", "repo_unbound",'
        d += '"content_unit_installed", "content_unit_uninstalled", "unit_profile_changed", "added_to_group",'
        d += '"removed_from_group")'
        history_command.add_option(PulpCliOption('--event-type', d, required=False))
        history_command.add_option(PulpCliOption('--limit', 'limits displayed history entries to the given amount (must be greater than zero)', required=False))
        history_command.add_option(PulpCliOption('--sort', 'indicates the sort direction ("ascending" or "descending") based on the entry\'s timestamp', required=False))
        history_command.add_option(PulpCliOption('--start-date', 'only return entries that occur on or after the given date in iso8601 format (yyyy-mm-ddThh:mm:ssZ)', required=False))
        history_command.add_option(PulpCliOption('--end-date', 'only return entries that occur on or before the given date in iso8601 format (yyyy-mm-ddThh:mm:ssZ)', required=False))
        self.add_command(history_command)


    def update(self, **kwargs):

        # Assemble the delta for all options that were passed in
        delta = dict([(k, v) for k, v in kwargs.items() if v is not None])
        delta.pop('consumer-id') # not needed in the delta
        if 'note' in delta.keys():
            if delta['note']:
                delta['notes'] = self._parse_notes(delta['note'])
            delta.pop('note')

        try:
            self.context.server.consumer.update(kwargs['consumer-id'], delta)
            self.prompt.render_success_message('Consumer [%s] successfully updated' % kwargs['consumer-id'])
        except NotFoundException:
            self.prompt.write('Consumer [%s] does not exist on the server' % kwargs['consumer-id'], tag='not-found')

    def unregister(self, **kwargs):
        consumer_id = kwargs['consumer-id']

        try:
            self.context.server.consumer.unregister(consumer_id)
            self.prompt.render_success_message('Consumer [%s] successfully unregistered' % consumer_id)
        except NotFoundException:
            self.prompt.write('Consumer [%s] does not exist on the server' % consumer_id, tag='not-found')

    def list(self, **kwargs):
        options = {}
        binding = self.context.server.consumer
        # query
        for opt in ('details', 'bindings'):
            if kwargs[opt]:
                options[opt] = kwargs[opt]
        response = binding.consumers(**options)
        # filters & ordering
        filters = ['id', 'display_name', 'description', 'bindings', 'notes']
        order = filters
        if kwargs['details']:
            order = filters[:2]
            filters = None
        elif kwargs['fields']:
            filters = kwargs['fields'].split(',')
            if 'bindings' not in filters:
                filters.append('bindings')
            if 'id' not in filters:
                filters.insert(0, 'id')
        # render
        self.prompt.render_title('Consumers')
        for c in response.response_body:
            self.prompt.render_document(c, filters=filters, order=order)

    def search(self, **kwargs):
        consumer_list = self.context.server.consumer_search.search(**kwargs)
        for consumer in consumer_list:
            self.prompt.render_document(consumer)

    def bind(self, **kwargs):
        consumer_id = kwargs['consumer-id']
        repo_id = kwargs['repo-id']
        distributor_id = kwargs['distributor-id']
        try:
            self.context.server.bind.bind(consumer_id, repo_id, distributor_id)
            self.prompt.render_success_message('Consumer [%s] successfully bound to repository distributor [%s : %s]' % (consumer_id, repo_id, distributor_id))
        except NotFoundException:
            self.prompt.write('Consumer [%s] does not exist on the server' % consumer_id, tag='not-found')

    def unbind(self, **kwargs):
        consumer_id = kwargs['consumer-id']
        repo_id = kwargs['repo-id']
        distributor_id = kwargs['distributor-id']
        try:
            self.context.server.bind.unbind(consumer_id, repo_id, distributor_id)
            self.prompt.render_success_message('Consumer [%s] successfully unbound from repository distributor [%s : %s]' % (consumer_id, repo_id, distributor_id))
        except NotFoundException:
            self.prompt.write('Consumer [%s] does not exist on the server' % consumer_id, tag='not-found')

    def history(self, **kwargs):
        self.prompt.render_title(_('Consumer History [%(i)s]') % {'i' : kwargs['consumer-id']})

        history_list = self.context.server.consumer_history.history(kwargs['consumer-id'], kwargs['event-type'], kwargs['limit'], kwargs['sort'],
                                                            kwargs['start-date'], kwargs['end-date']).response_body
        filters = ['consumer_id', 'type', 'details', 'originator', 'timestamp']
        order = filters
        for history in history_list:
            self.prompt.render_document(history, filters=filters, order=order)


    def install(self, **kwargs):
        consumer_id = kwargs['consumer-id']
        units = []
        for name in kwargs['name']:
            unit_key = dict(name=name)
            unit = dict(type_id='rpm', unit_key=unit_key)
            units.append(unit)
        try:
            task = self.context.server.consumer_content.install(consumer_id, units=units)
            self.prompt.render_success_message('Install task created with id [%s]' % task.task_id)
            # Wait for task to finish
            self.prompt.render_success_message('Content units [%s] successfully installed on consumer [%s]' % (kwargs['name'], consumer_id))
        except NotFoundException:
            self.prompt.write('Consumer [%s] does not exist on the server' % consumer_id, tag='not-found')


    def _parse_notes(self, notes_list):
        """
        Extracts notes information from the user-specified options and puts them in a dictionary

        @return: dict of notes

        @raises InvalidConfig: if one or more of the notes is malformed
        """

        notes_dict = {}
        for note in notes_list:
            pieces = note.split('=', 1)

            if len(pieces) < 2:
                raise InvalidConfig(_('Notes must be specified in the format key=value'))

            key = pieces[0]
            value = pieces[1]

            if value in (None, '', '""'):
                value = None

            if key in notes_dict.keys():
                self.prompt.write('Multiple values entered for a note with key [%s]. All except first value will be ignored.' % key)
                continue

            notes_dict[key] = value

        return notes_dict


class ContentSection(PulpCliSection):

    def __init__(self, context):
        PulpCliSection.__init__(self, 'content', _('content unit installation management'))
        for Command in (InstallContent, UpdateContent, UninstallContent):
            command = Command(context)
            command.create_option(
                '--consumer-id',
                _('identifies the consumer'),
                required=True)
            command.create_option(
                '--type',
                _('content unit type ID'),
                required=True)
            command.create_option(
                '--name',
                _('content unit key (name)'),
                required=True,
                allow_multiple=True,
                aliases=['-n'])
            command.create_flag(
                '--no-commit',
                _('transaction not committed'))
            self.add_command(command)


class PollingCommand(PulpCliCommand):

    def process(self, id, task):
        prompt = self.context.prompt
        m = 'This command may be exited via CTRL+C without affecting the install.'
        prompt.render_paragraph(_(m))
        try:
            task = self.poll(task)
            if task.was_successful():
                self.succeeded(id, task)
                return
            if task.was_failure():
                self.failed(id, task)
                return
            if task.was_cancelled():
                self.cancelled(id, task)
                return
        except KeyboardInterrupt:
            # graceful interrupt
            pass

    def poll(self, task):
        server = self.context.server
        cfg = self.context.config
        spinner = self.context.prompt.create_spinner()
        interval = float(cfg['output']['poll_frequency_in_seconds'])
        while not task.is_completed():
            if task.is_waiting():
                spinner.next(_('Waiting to begin'))
            else:
                spinner.next()
            time.sleep(interval)
            response = server.tasks.get_task(task.task_id)
            task = response.response_body
        return task

    def rejected(self, task):
        rejected = task.is_rejected()
        if rejected:
            prompt = self.context.prompt
            msg = 'The request was rejected by the server'
            prompt.render_failure_message(_(msg))
            msg = 'This is likely due to an impending delete request for the consumer.'
            prompt.render_failure_message(_(msg))
        return rejected

    def postponed(self, task):
        postponed = task.is_postponed()
        if postponed:
            msg  = \
                'The request to update content was accepted but postponed ' \
                'due to one or more previous requests against the consumer.' \
                ' This request will take place at the earliest possible time.'
            self.context.prompt.render_paragraph(_(msg))
        return postponed

    def failed(self, id, task):
        prompt = self.context.prompt
        msg = 'Request Failed'
        prompt.render_failure_message(_(msg))
        prompt.render_failure_message(task.exception)

    def cancelled(self, id, response):
        prompt = self.context.prompt
        prompt.render_failure_message('Request Cancelled')


class InstallContent(PollingCommand):

    def __init__(self, context, **options):
        PollingCommand.__init__(
            self,
            'install',
            _('install content units'),
            self.run,
            **options)
        self.context = context

    def run(self, **kwargs):
        consumer_id = kwargs['consumer-id']
        type_id = kwargs['type']
        apply = (not kwargs['no-commit'])
        options = dict(
            apply=apply,)
        units = []
        for name in kwargs['name']:
            unit_key = dict(name=name)
            unit = dict(type_id=type_id, unit_key=unit_key)
            units.append(unit)
        self.install(consumer_id, units, options)

    def install(self, id, units, options):
        prompt = self.context.prompt
        server = self.context.server
        try:
            response = server.consumer_content.install(id, units=units, options=options)
            task = response.response_body
            msg = _('Install task created with id [%s]') % task.task_id
            prompt.render_success_message(msg)
            response = server.tasks.get_task(task.task_id)
            task = response.response_body
            if self.rejected(task):
                return
            if self.postponed(task):
                return
            self.process(id, task)
        except NotFoundException:
            msg = _('Consumer [%s] not found') % id
            prompt.write(msg, tag='not-found')

    def succeeded(self, id, task):
        prompt = self.context.prompt
        # overall status
        if task.result['status']:
            msg = 'Install Succeeded'
            prompt.render_success_message(_(msg))
        else:
            msg = 'Install Failed'
            prompt.render_failure_message(_(msg))
        # detailed status
        prompt.render_title('Report Details')
        details = task.result['details']
        for type_id, report in details.items():
            status = report['status']
            if status:
                d = dict(
                    status=status,
                    details=report['details'])
                order = ['status', 'details']
                prompt.render_document(d, order=order)
            else:
                d = dict(
                    status=status,
                    message=report['details']['message'])
                order = ['status', 'message']
                prompt.render_document(d, order=order)


class UpdateContent(PollingCommand):

    def __init__(self, context, **options):
        PollingCommand.__init__(
            self,
            'update',
            _('update (installed) content units'),
            self.run,
            **options)
        self.context = context

    def run(self, **kwargs):
        consumer_id = kwargs['consumer-id']
        type_id = kwargs['type']
        apply = (not kwargs['no-commit'])
        options = dict(
            apply=apply,)
        units = []
        for name in kwargs['name']:
            unit_key = dict(name=name)
            unit = dict(type_id=type_id, unit_key=unit_key)
            units.append(unit)
        self.update(consumer_id, units, options)

    def update(self, id, units, options):
        prompt = self.context.prompt
        server = self.context.server
        try:
            response = server.consumer_content.update(id, units=units, options=options)
            task = response.response_body
            msg = _('Install task created with id [%s]') % task.task_id
            prompt.render_success_message(msg)
            response = server.tasks.get_task(task.task_id)
            task = response.response_body
            if self.rejected(task):
                return
            if self.postponed(task):
                return
            self.process(id, task)
        except NotFoundException:
            msg = _('Consumer [%s] not found') % id
            prompt.write(msg, tag='not-found')

    def succeeded(self, id, task):
        prompt = self.context.prompt
        # overall status
        if task.result['status']:
            msg = 'Update Succeeded'
            prompt.render_success_message(_(msg))
        else:
            msg = 'Update Failed'
            prompt.render_failure_message(_(msg))
        # detailed status
        prompt.render_title('Report Details')
        details = task.result['details']
        for type_id, report in details.items():
            status = report['status']
            if status:
                d = dict(
                    status=status,
                    details=report['details'])
                order = ['status', 'details']
                prompt.render_document(d, order=order)
            else:
                d = dict(
                    status=status,
                    message=report['details']['message'])
                order = ['status', 'message']
                prompt.render_document(d, order=order)


class UninstallContent(PollingCommand):

    def __init__(self, context, **options):
        PollingCommand.__init__(
            self,
            'uninstall',
            _('uninstall content units'),
            self.run,
            **options)
        self.context = context

    def run(self, **kwargs):
        consumer_id = kwargs['consumer-id']
        type_id = kwargs['type']
        apply = (not kwargs['no-commit'])
        options = dict(
            apply=apply,)
        units = []
        for name in kwargs['name']:
            unit_key = dict(name=name)
            unit = dict(type_id=type_id, unit_key=unit_key)
            units.append(unit)
        self.uninstall(consumer_id, units, options)

    def uninstall(self, id, units, options):
        prompt = self.context.prompt
        server = self.context.server
        try:
            response = server.consumer_content.uninstall(id, units=units, options=options)
            task = response.response_body
            msg = _('Install task created with id [%s]') % task.task_id
            prompt.render_success_message(msg)
            response = server.tasks.get_task(task.task_id)
            task = response.response_body
            if self.rejected(task):
                return
            if self.postponed(task):
                return
            self.process(id, task)
        except NotFoundException:
            msg = _('Consumer [%s] not found') % id
            prompt.write(msg, tag='not-found')

    def succeeded(self, id, task):
        prompt = self.context.prompt
        # overall status
        if task.result['status']:
            msg = 'Uninstall Succeeded'
            prompt.render_success_message(_(msg))
        else:
            msg = 'Uninstall Failed'
            prompt.render_failure_message(_(msg))
        # detailed status
        prompt.render_title('Report Details')
        details = task.result['details']
        for type_id, report in details.items():
            status = report['status']
            if status:
                d = dict(
                    status=status,
                    details=report['details'])
                order = ['status', 'details']
                prompt.render_document(d, order=order)
            else:
                d = dict(
                    status=status,
                    message=report['details']['message'])
                order = ['status', 'message']
                prompt.render_document(d, order=order)

class ConsumerGroupMemberSection(PulpCliSection):
    def __init__(self, context):
        super(ConsumerGroupMemberSection, self).__init__('members', _('manage members of consumer groups'))
        self.context = context
        self.prompt = context.prompt

        id_option = PulpCliOption('--consumer-group-id', _('id of a consumer group'), required=True)

        list_command = PulpCliCommand('list', _('list of consumers in a particular group'), self.list)
        list_command.add_option(id_option)
        self.add_command(list_command)

        add_command = SearchCommand(self.add, name='add', 
            description=_('add consumers based on search parameters'))
        add_command.add_option(id_option)
        self._strip_criteria_options(add_command)
        self.add_command(add_command)

        remove_command = SearchCommand(self.remove, name='remove', 
            description=_('remove consumers based on search parameters'))
        remove_command.add_option(id_option)
        self._strip_criteria_options(remove_command)
        self.add_command(remove_command)

    @staticmethod
    def _strip_criteria_options(command):
        """
        We don't want to expose all of the criteria features here, so we remove
        all of them except for search-related ones.

        :param command: command instance from which we should remove criteria
                        options.
        :type  command: SearchCommand
        """
        OPTION_NAMES = set(('--fields', '--limit', '--skip', '--sort'))
        for option in copy.copy(command.options):
            if option.name in OPTION_NAMES:
                command.options.remove(option)

    def list(self, **kwargs):
        consumer_group_id = kwargs['consumer-group-id']
        criteria = {'fields':('consumer_ids',),
            'filters':{'id':consumer_group_id}}
        consumer_group_list = self.context.server.consumer_group_search.search(**criteria)
        if len(consumer_group_list) != 1:
            self.prompt.write(
                'Consumer group [%s] does not exist on the server' % 
                consumer_group_id, tag='not-found')
        else:
            consumer_ids = consumer_group_list[0].get('consumer_ids')
            if consumer_ids:
                criteria = {'filters':{'id':{'$in':consumer_ids}}}
                consumer_list = self.context.server.consumer_search.search(**criteria)
                for consumer in consumer_list:
                    self.prompt.render_document(consumer)

    def add(self, **kwargs):
        consumer_group_id = kwargs.pop('consumer-group-id')
        self.context.server.consumer_group_actions.associate(consumer_group_id, **kwargs)
        msg = _("Consumer Group [%(c)s] membership updated")
        self.context.prompt.render_success_message(msg % \
            {'c' : consumer_group_id})

    def remove(self, **kwargs):
        consumer_group_id = kwargs.pop('consumer-group-id')
        self.context.server.consumer_group_actions.unassociate(consumer_group_id, **kwargs)
        msg = _("Consumer Group [%(c)s] membership updated")
        self.context.prompt.render_success_message(msg % \
            {'c' : consumer_group_id})

class ConsumerGroupSection(PulpCliSection):
    def __init__(self, context):
        PulpCliSection.__init__(self, 'group', _('consumer group commands'))

        self.context = context
        self.prompt = context.prompt # for easier access

        self.add_subsection(ConsumerGroupMemberSection(context))

        # Common Options
        id_option = PulpCliOption('--consumer-group-id', _('uniquely identifies the consumer group; only alphanumeric, -, and _ allowed'), required=True)
        name_option = PulpCliOption('--display-name', _('user-readable display name for the consumer group'), required=False)
        description_option = PulpCliOption('--description', _('user-readable description for the consumer group'), required=False)

        note_desc =  'adds/updates/deletes notes to programmatically identify the resource; '
        note_desc += 'key-value pairs must be separated by an equal sign (e.g. key=value); multiple notes can '
        note_desc += 'be changed by specifying this option multiple times; notes are deleted by '
        note_desc += 'specifying "" as the value'
        note_option = PulpCliOption('--note', _(note_desc), required=False, allow_multiple=True)

        # Create Command
        create_command = PulpCliCommand('create', _('creates a new consumer group'), self.create)
        create_command.add_option(id_option)
        create_command.add_option(name_option)
        create_command.add_option(description_option)
        create_command.add_option(note_option)
        self.add_command(create_command)

        # Update Command
        update_command = PulpCliCommand('update', _('changes metadata on an existing consumer group'), self.update)
        update_command.add_option(id_option)
        update_command.add_option(name_option)
        update_command.add_option(description_option)
        update_command.add_option(note_option)
        self.add_command(update_command)

        # Delete Command
        delete_command = PulpCliCommand('delete', _('deletes a consumer group'), self.delete)
        delete_command.add_option(id_option)
        self.add_command(delete_command)

        # List Command
        list_command = PulpCliCommand('list', _('lists summary of consumer groups registered to the Pulp server'), self.list)
        list_command.add_option(PulpCliFlag('--details', _('if specified, all the consumer group information is displayed')))
        list_command.add_option(PulpCliOption('--fields', _('comma-separated list of consumer group fields; if specified, only the given fields will displayed'), required=False))
        self.add_command(list_command)

        # Search Command
        self.add_command(SearchCommand(self.search))

        # Bind Command
        bind_command = PulpCliCommand('bind', 
            _('binds each consumer in a consumer group to a repository '
              'distributor for consuming published content'),
            self.bind)
        bind_command.add_option(id_option)
        bind_command.add_option(PulpCliOption('--repo-id', 'repository id', required=True))
        bind_command.add_option(PulpCliOption('--distributor-id', 'distributor id', required=True))
        self.add_command(bind_command)

    def create(self, **kwargs):
        # Collect input
        consumer_group_id = kwargs['consumer-group-id']
        name = consumer_group_id
        if 'display-name' in kwargs:
            name = kwargs['display-name']
        description = kwargs['description']
        notes = kwargs.get('notes', None)
        if notes:
            notes = arg_utils.args_to_notes_dict(notes, include_none=True)

        # Call the server
        self.context.server.consumer_group.create(consumer_group_id, name, description, notes)
        self.prompt.render_success_message(
            'Consumer Group [%s] successfully created' % consumer_group_id)

    def update(self, **kwargs):
        # Assemble the delta for all options that were passed in
        delta = dict([(k, v) for k, v in kwargs.items() if v is not None])
        delta.pop('consumer-group-id') # not needed in the delta

        if delta.pop('note', None) is not None:
            delta['notes'] = arg_utils.args_to_notes_dict(kwargs['note'], include_none=True)
        try:
            self.context.server.consumer_group.update(kwargs['consumer-group-id'], delta)
            self.prompt.render_success_message(
                'Consumer group [%s] successfully updated' %
                kwargs['consumer-group-id'])
        except NotFoundException:
            self.prompt.write(
                'Consumer group [%s] does not exist on the server' %
                kwargs['consumer-group-id'], tag='not-found')

    def delete(self, **kwargs):
        id = kwargs['consumer-group-id']

        try:
            self.context.server.consumer_group.delete(id)
            self.prompt.render_success_message('Consumer group [%s] successfully deleted' % id)
        except NotFoundException:
            self.prompt.write('Consumer group [%s] does not exist on the server' % id, tag='not-found')

    def list(self, **kwargs):
        self.prompt.render_title('Consumer Groups')

        consumer_group_list = self.context.server.consumer_group.consumer_groups().response_body

        # Default flags to render_document_list
        filters = ['id', 'display_name', 'description', 'consumer_ids', 'notes']
        order = filters

        if kwargs['fields'] is not None:
            filters = kwargs['fields'].split(',')
            if 'id' not in filters:
                filters.append('id')
            order = ['id']

        # Manually loop over the consumers so we can interject the plugins
        # manually based on the CLI flags.
        for consumer_group in consumer_group_list:
            self.prompt.render_document(consumer_group, filters=filters, order=order)

    def search(self, **kwargs):
        consumer_group_list = self.context.server.consumer_group_search.search(**kwargs)
        for consumer in consumer_group_list:
            self.prompt.render_document(consumer)

    def bind(self, **kwargs):
        consumer_group_id = kwargs['id']
        repo_id = kwargs['repo-id']
        distributor_id = kwargs['distributor-id']
        try:
            self.context.server.consumer_group_bind.bind(id, repo_id, distributor_id)
            self.prompt.render_success_message('Consumer Group [%s] '
                'successfully bound to repository distributor [%s : %s]' \
                % (consumer_group_id, repo_id, distributor_id))
        except NotFoundException:
            self.prompt.write('Consumer Group [%s] does not exist on the '
                'server' % consumer_group_id, tag='not-found')

