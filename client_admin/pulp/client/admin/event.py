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
from gettext import gettext as _

from okaara.cli import CommandUsage

from pulp.client import parsers
from pulp.client.extensions.extensions import PulpCliSection, PulpCliCommand, PulpCliOption

# -- framework hook -----------------------------------------------------------

def initialize(context):
    context.cli.add_section(EventSection(context))


class GenericSection(PulpCliSection):
    def __init__(self, context, *args, **kwargs):
        """
        @param context:
        @type  context: pulp.client.extensions.core.ClientContext
        """
        super(GenericSection, self).__init__(*args, **kwargs)

        self.context = context

        m = _('id of the event listener')
        self.id_option = PulpCliOption('--listener-id', m, required=True)

        m = _('one of "repo.sync.start", "repo.sync.finish", '
              '"repo.publish.start", "repo.publish.finish". May be '
              'specified multiple times. To match all types, use value "*"')
        self.event_types_option = PulpCliOption('--event-type', m,
            required=True, allow_multiple=True)

    @staticmethod
    def _copy_flip_required(option):
        """
        Return a new PulpCliOption with identical values, except the opposite
        value for the 'required' boolean attribute.

        :param option: a PulpCliOption instance to copy
        :type  option: PulpCliOption
        :return: new PulpCliOption
        """
        ret = copy.copy(option)
        ret.required = not option.required
        return ret

    def _create(self, notifier_type, config, event_types):
        """
        Generic method for creating an event listener

        :param notifier_type: type of notifier to use,
                              defined in pulp.server.event.notifiers
        :type notifier_type:  basestring
        :param config: dict with config values required by the notifier type
        :type  config: dict
        :param event_types: list of event types as defined in pulp.server.event.data
        :type  event_types: list
        """
        try:
            self.context.server.event_listener.create(notifier_type, config,
                event_types)
        except TypeError:
            raise CommandUsage
        self.context.prompt.render_success_message('Event listener successfully created')

    def _update(self, listener_id, delta):
        """
        Generic method for updating an event listener

        :param listener_id: id of an event listener
        :type  listener_id: str
        :param delta: dict where keys are event listener attributes and values
                      are the new values those attributes should have.
        :type  delta: dict
        """
        if delta:
            try:
                self.context.server.event_listener.update(listener_id, **delta)
            except TypeError:
                raise CommandUsage
            self.context.prompt.render_success_message('Event listener successfully updated')
        else:
            self.context.prompt.render_failure_message('No changes were made')


class EventSection(PulpCliSection):
    def __init__(self, context):
        """
        @param context:
        @type  context: pulp.client.extensions.core.ClientContext
        """
        super(EventSection, self).__init__('event', _('subscribe to event notifications'))
        self.add_subsection(ListenerSection(context))


class ListenerSection(GenericSection):
    def __init__(self, context):
        """
        @param context:
        @type  context: pulp.client.extensions.core.ClientContext
        """
        super(ListenerSection, self).__init__(context, 'listener',
            _('manage server-side event listeners'))
        self.add_subsection(EmailSection(context))
        self.add_subsection(RestApiSection(context))
        self.add_subsection(AMQPSection(context))

        m = _('list all of the event listeners in the system')
        self.add_command(PulpCliCommand('list', m, self.list))

        m = _('delete an event listener')
        delete_command = PulpCliCommand('delete', m, self.delete)
        delete_command.add_option(self.id_option)
        self.add_command(delete_command)

    def delete(self, **kwargs):
        """
        Delete an event listener.

        :param kwargs: dict containing only the key "listener-id"
        """
        self.context.server.event_listener.delete(kwargs['listener-id'])
        self.context.prompt.render_success_message('Event listener successfully deleted')

    def list(self, **kwargs):
        """
        List all event listeners
        """
        results = self.context.server.event_listener.list()
        for result in results:
            self.context.prompt.render_document(result)


class RestApiSection(GenericSection):
    def __init__(self, context):
        """
        @param context:
        @type  context: pulp.client.extensions.core.ClientContext
        """
        super(RestApiSection, self).__init__(context, 'http',
            _('manage http listeners'))

        m = _('full URL to invoke to send the event info')
        url_option = PulpCliOption('--url', m, required=True)

        m = _('optional username to be passed as basic auth credentials when '
              'the HTTP call is invoked.')
        username_option = PulpCliOption('--username', m, required=False)

        m = _('optional password to be passed as basic auth credentials when '
              'the HTTP call is invoked.')
        password_option = PulpCliOption('--password', m, required=False)

        create_command = PulpCliCommand('create', _('create a listener'),
            self.create)
        create_command.add_option(self.event_types_option)
        create_command.add_option(url_option)
        create_command.add_option(username_option)
        create_command.add_option(password_option)
        self.add_command(create_command)

        update_command = PulpCliCommand('update', _('update a listener'),
            self.update)
        update_command.add_option(self.id_option)
        update_command.add_option(self._copy_flip_required(self.event_types_option))
        update_command.add_option(self._copy_flip_required(url_option))
        update_command.add_option(username_option)
        update_command.add_option(password_option)
        self.add_command(update_command)

    def create(self, **kwargs):
        """
        Create an event listener.

        :param kwargs: dict containing keys "event-type", "url",
                       "username" and "password"
        """
        config = {}
        if kwargs.get('url') is None:
            raise CommandUsage
        else:
            config['url'] = kwargs['url']

        for attr in ('username', 'password'):
            if kwargs.get(attr) is not None:
                config[attr] = kwargs[attr]
        self._create('http', config, kwargs['event-type'])

    def update(self, **kwargs):
        """
        Update an event listener.

        :param kwargs: dict containing key "listener-id", and optionally
                       "url", "username", "password", and "event-type"
        """
        config = {}
        for attr in ('url', 'username', 'password'):
            if kwargs.get(attr) is not None:
                config[attr] = kwargs[attr]

        delta = {}
        if config:
            delta['notifier_config'] = config
        if kwargs['event-type'] is not None:
            delta['event_types'] = kwargs['event-type']

        self._update(kwargs['listener-id'], delta)


class AMQPSection(GenericSection):
    def __init__(self, context):
        super(AMQPSection, self).__init__(context, 'amqp',
            _('manage amqp listeners'))

        m = _('optional name of an exchange that overrides the setting from '
              'server.conf')
        self.exchange_option = PulpCliOption('--exchange', m, required=False)

        create_command = PulpCliCommand('create', _('create a listener'),
            self.create)
        create_command.add_option(self.event_types_option)
        create_command.add_option(self.exchange_option)
        self.add_command(create_command)

        m = _('update an event listener')
        update_command = PulpCliCommand('update', m, self.update)
        update_command.add_option(self.id_option)
        update_command.add_option(self._copy_flip_required(self.event_types_option))
        update_command.add_option(self.exchange_option)
        self.add_command(update_command)

    def create(self, **kwargs):
        """
        Create an event listener.

        :param kwargs: dict containing keys "event-type" and optionally 'exchange'

        """
        config = {}
        if kwargs[self.exchange_option.keyword]:
            config[self.exchange_option.keyword] = kwargs[self.exchange_option.keyword]
        self._create('amqp', config, kwargs['event-type'])

    def update(self, **kwargs):
        """
        Update an event listener.

        :param kwargs: dict containing key "listener-id", and optionally
                       "subject", "addresses", and "event-type"
        """
        config = {}
        if kwargs.get(self.exchange_option.keyword) is not None:
            config[self.exchange_option.keyword] = kwargs[self.exchange_option.keyword]

        delta = {}
        if config:
            delta['notifier_config'] = config
        if kwargs['event-type'] is not None:
            delta['event_types'] = kwargs['event-type']

        self._update(kwargs['listener-id'], delta)


class EmailSection(GenericSection):
    def __init__(self, context):
        """
        @param context:
        @type  context: pulp.client.extensions.core.ClientContext
        """
        super(EmailSection, self).__init__(context, 'email',
            _('manage email listeners'))

        m = _("text of the email's subject")
        subject_option = PulpCliOption('--subject', m, required=True)

        m = _('this is a comma separated list of email addresses that should '
              'receive these notifications. Do not include spaces.')
        addresses_option = PulpCliOption('--addresses', m, required=True,
            parse_func=parsers.csv)

        create_command = PulpCliCommand('create', _('create a listener'),
            self.create)
        create_command.add_option(self.event_types_option)
        create_command.add_option(subject_option)
        create_command.add_option(addresses_option)
        self.add_command(create_command)

        m = _('update an event listener')
        update_command = PulpCliCommand('update', m, self.update)
        update_command.add_option(self.id_option)
        update_command.add_option(self._copy_flip_required(subject_option))
        update_command.add_option(self._copy_flip_required(addresses_option))
        update_command.add_option(self._copy_flip_required(self.event_types_option))
        self.add_command(update_command)

    def create(self, **kwargs):
        """
        Create an event listener.

        :param kwargs: dict containing keys "event-type",
                       "subject" and "addresses".
        """
        config = {}
        for attr in ('subject', 'addresses'):
            if kwargs[attr] is None:
                raise CommandUsage
            else:
                config[attr] = kwargs[attr]
        self._create('email', config, kwargs['event-type'])

    def update(self, **kwargs):
        """
        Update an event listener.

        :param kwargs: dict containing key "listener-id", and optionally
                       "subject", "addresses", and "event-type"
        """
        config = {}
        for attr in ('subject', 'addresses'):
            if kwargs.get(attr) is not None:
                config[attr] = kwargs[attr]

        delta = {}
        if config:
            delta['notifier_config'] = config
        if kwargs['event-type'] is not None:
            delta['event_types'] = kwargs['event-type']

        self._update(kwargs['listener-id'], delta)
