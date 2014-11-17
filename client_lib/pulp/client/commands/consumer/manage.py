import os
from gettext import gettext as _

from pulp.bindings.exceptions import NotFoundException
from pulp.client.commands.options import (OPTION_CONSUMER_ID, OPTION_NAME,
                                          OPTION_DESCRIPTION, OPTION_NOTES)
from pulp.client.consumer_utils import load_consumer_id
from pulp.client.extensions.extensions import PulpCliCommand


class ConsumerRegisterCommand(PulpCliCommand):
    """
    Command to register a new consumer to a Pulp server.
    """

    def __init__(self, context, name=None, description=None):
        name = name or 'register'
        description = description or ''
        super(ConsumerRegisterCommand, self).__init__(name, description, self.run)

        self.add_option(OPTION_CONSUMER_ID)
        self.add_option(OPTION_NAME)
        self.add_option(OPTION_DESCRIPTION)
        self.add_option(OPTION_NOTES)

        self.context = context

    def run(self, **kwargs):
        """
        Currently there is no implementation of this command as there seems to
        be too much client-side work that needs to get done.
        """
        pass


class ConsumerUnregisterCommand(PulpCliCommand):
    """
    Command to unregister a consumer from a Pulp server.
    """

    def __init__(self, context, name=None, description=None):
        name = name or 'unregister'
        description = description or _('unregisters a consumer')
        super(ConsumerUnregisterCommand, self).__init__(name, description, self.run)

        self.add_consumer_option()

        self.context = context

    def add_consumer_option(self):
        """
        Override this method to a no-op to skip adding the consumer id option.
        This allows commands (such as the consumer command) to find the consumer
        id via other means than a command line option.
        """
        self.add_option(OPTION_CONSUMER_ID)

    def run(self, **kwargs):
        consumer_id = self.get_consumer_id(kwargs)

        try:
            self.context.server.consumer.unregister(consumer_id)

        except NotFoundException:
            msg = _('Consumer [ %(c)s ] does not exist on the server') % {'c': consumer_id}
            self.context.prompt.write(msg)

        else:
            msg = _('Consumer [ %(c)s ] successfully unregistered') % {'c': consumer_id}
            self.context.prompt.render_success_message(msg)

    def get_consumer_id(self, kwargs):
        """
        Override this method to provide the consumer id to the run method.
        """
        return kwargs.get(OPTION_CONSUMER_ID.keyword, load_consumer_id(self.context))


class ConsumerUpdateCommand(PulpCliCommand):
    """
    Command to update a registered consumer's metadata with the Pulp server.
    """

    def __init__(self, context, name=None, description=None):
        name = name or 'update'
        description = description or _('changes metadata on an existing consumer')
        super(ConsumerUpdateCommand, self).__init__(name, description, self.run)

        self.add_option(OPTION_NAME)
        self.add_option(OPTION_DESCRIPTION)
        self.add_option(OPTION_NOTES)
        self.add_consumer_option()

        self.context = context

    def add_consumer_option(self):
        """
        Override this method to a no-op to skip adding the consumer id option.
        This allows commands (such as the consumer command) to find the consumer
        id via other means than a command line option.
        """
        self.add_option(OPTION_CONSUMER_ID)

    def run(self, **kwargs):
        consumer_id = self.get_consumer_id(kwargs)
        delta = dict((k, v) for k, v in kwargs.items() if v is not None)

        if OPTION_NOTES.keyword in delta:
            delta['notes'] = delta.pop(OPTION_NOTES.keyword)

        if OPTION_NAME.keyword in delta:
            name = delta.pop(OPTION_NAME.keyword)
            delta[OPTION_NAME.keyword.replace('-', '_')] = name

        try:
            self.context.server.consumer.update(consumer_id, delta)

        except NotFoundException:
            msg = _('Consumer [ %(c)s ] does not exist on server') % {'c': consumer_id}
            self.context.prompt.render_failure_message(msg)
            return os.EX_DATAERR

        else:
            msg = _('Consumer [ %(c)s ] successfully updated') % {'c': consumer_id}
            self.context.prompt.render_success_message(msg)

    def get_consumer_id(self, kwargs):
        """
        Override this method to provide the consumer id to the run method.
        """
        return kwargs.pop(OPTION_CONSUMER_ID.keyword, load_consumer_id(self.context))
