# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License
# (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied, including the
# implied warranties of MERCHANTABILITY, NON-INFRINGEMENT, or FITNESS FOR A
# PARTICULAR PURPOSE.
# You should have received a copy of GPLv2 along with this software; if not,
# see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

from gettext import gettext as _

from pulp.bindings.exceptions import NotFoundException
from pulp.client.arg_utils import args_to_notes_dict
from pulp.client.commands.options import (
    OPTION_CONSUMER_ID, OPTION_NAME, OPTION_DESCRIPTION, OPTION_NOTES)
from pulp.client.extensions.extensions import (
    PulpCliCommand, PulpCliFlag, PulpCliOption)


CONSUMER_REGISTER_DESCRIPTION = _('')
CONSUMER_UNREGISTER_DESCRIPTION = _('unregisters a consumer')
CONSUMER_UPDATE_DESCRIPTION = _('changes metadata on an existing consumer')


class ConsumerRegisterCommand(PulpCliCommand):
    pass


class ConsumerUnregisterCommand(PulpCliCommand):

    def __init__(self, context, name='unregister', description=CONSUMER_UNREGISTER_DESCRIPTION):
        super(self.__class__, self).__init__(name, description, self.unregister)
        self.context = context
        self.add_option(OPTION_CONSUMER_ID)

    def unregister(self, **kwargs):
        consumer_id = kwargs[OPTION_CONSUMER_ID.keyword]
        try:
            self.context.server.consumer.unregister(consumer_id)
        except NotFoundException:
            self.context.prompt.write(_('Consumer [%(c)s] does not exist on the server') % {'c': consumer_id})
        else:
            self.context.prompt.write(_('Consumer [%(c)s] successfully unregistered') % {'c': consumer_id})


class ConsumerUpdateCommand(PulpCliCommand):

    def __init__(self, context, name='update', description=CONSUMER_UPDATE_DESCRIPTION):
        super(self.__class__, self).__init__(name, description, self.update)
        self.context = context
        self.add_option(OPTION_CONSUMER_ID)
        self.add_option(OPTION_NAME)
        self.add_option(OPTION_DESCRIPTION)
        self.add_option(OPTION_NOTES)

    def update(self, **kwargs):
        delta = dict((k, v) for k, v in kwargs.items() if v is not None)
        consumer_id = delta.pop(OPTION_CONSUMER_ID.keyword)

        if OPTION_NOTES.keyword in delta:
            notes_args = delta.pop(OPTION_NOTES.keyword)
            delta['notes'] = args_to_notes_dict(notes_args)

        if OPTION_NAME.keyword in delta:
            name = delta.pop(OPTION_NAME.keyword)
            delta[OPTION_NAME.keyword.replace('-', '_')] = name

        try:
            self.context.server.consumer.update(consumer_id, delta)
        except NotFoundException:
            self.context.prompt.write(_('Consumer [%(c)s] does not exist on server') % {'c': consumer_id})
        else:
            self.context.prompt.write(_('Consumer [%(c)s] successfully updated') % {'c': consumer_id})


