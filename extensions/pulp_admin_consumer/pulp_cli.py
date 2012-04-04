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

from pulp.gc_client.framework.extensions import PulpCliSection, PulpCliCommand, PulpCliOption, PulpCliFlag, UnknownArgsParser
from pulp.gc_client.api.exceptions import NotFoundException

# -- framework hook -----------------------------------------------------------

def initialize(context):
    context.cli.add_section(AdminConsumerSection(context))

# -- sections -----------------------------------------------------------------

class AdminConsumerSection(PulpCliSection):

    def __init__(self, context):
        PulpCliSection.__init__(self, 'consumer', 'consumer lifecycle (list, update, etc.) commands')

        self.context = context
        self.prompt = context.prompt # for easier access

        # Common Options
        id_option = PulpCliOption('--id', 'uniquely identifies the consumer; only alphanumeric, -, and _ allowed', required=True)
        name_option = PulpCliOption('--display_name', '(optional) user-readable display name for the consumer', required=False)
        description_option = PulpCliOption('--description', '(optional) user-readable description for the consumer', required=False)

        # Update Command
        update_command = PulpCliCommand('update', 'changes metadata on an existing consumer', self.update)
        update_command.add_option(id_option)
        update_command.add_option(name_option)
        update_command.add_option(description_option)
        self.add_command(update_command)

        # Delete Command
        unregister_command = PulpCliCommand('unregister', 'unregisters a consumer', self.unregister)
        unregister_command.add_option(PulpCliOption('--id', 'identifies the consumer to be unregistered', required=True))
        self.add_command(unregister_command)

        # List Command
        list_command = PulpCliCommand('list', 'lists consumers registered to the Pulp server', self.list)
        list_command.add_option(PulpCliFlag('--summary', 'if specified, only a minimal amount of consumer information is displayed'))
        list_command.add_option(PulpCliOption('--fields', 'comma-separated list of consumer fields; if specified, only the given fields will displayed', required=False))
        self.add_command(list_command)

    def update(self, **kwargs):

        # Assemble the delta for all options that were passed in
        delta = dict([(k, v) for k, v in kwargs.items() if v is not None])
        delta.pop('id') # not needed in the delta
        try:
            self.context.server.consumer.update(kwargs['id'], delta)
            self.prompt.render_success_message('Consumer [%s] successfully updated' % kwargs['id'])
        except NotFoundException:
            self.prompt.write('Consumer [%s] does not exist on the server' % kwargs['id'], tag='not-found')


    def unregister(self, **kwargs):
        id = kwargs['id']

        try:
            self.context.server.consumer.unregister(id)
            self.prompt.render_success_message('Consumer [%s] successfully unregistered' % id)
        except NotFoundException:
            self.prompt.write('Consumer [%s] does not exist on the server' % id, tag='not-found')

    def list(self, **kwargs):

        self.prompt.render_title('Consumers')

        consumer_list = self.context.server.consumer.consumers().response_body

        # Default flags to render_document_list
        filters = None
        order = ['id', 'display_name', 'description', 'notes']

        if kwargs['summary'] is True:
            filters = ['id', 'display_name']
            order = filters
        elif kwargs['fields'] is not None:
            filters = kwargs['fields'].split(',')
            if 'id' not in filters:
                filters.append('id')
            order = ['id']

        # Manually loop over the repositories so we can interject the plugins
        # manually based on the CLI flags.
        for c in consumer_list:
            self.prompt.render_document(c, filters=filters, order=order)
