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

from pulp.gc_client.framework.extensions import PulpCliSection, PulpCliCommand, PulpCliOption, PulpCliFlag
from pulp.gc_client.api.server import NotFoundException

def initialize(context):
    context.cli.add_section(RepoSection(context))

# -- sections -----------------------------------------------------------------

class RepoSection(PulpCliSection):

    def __init__(self, context):
        PulpCliSection.__init__(self, 'repo', 'repository lifecycle (create, delete, configure, etc.) commands')

        self.context = context
        self.prompt = context.prompt # for easier access

        # Common Options
        id_option = PulpCliOption('--id', 'uniquely identifies the repository; only alphanumeric, -, and _ allowed', required=True)
        name_option = PulpCliOption('--display_name', '(optional) user-readable display name for the repository', required=False)
        description_option = PulpCliOption('--description', '(optional) user-readable description for the repository', required=False)

        # Create Command
        create_command = PulpCliCommand('create', 'creates a new repository', self.create)
        create_command.add_option(id_option)
        create_command.add_option(name_option)
        create_command.add_option(description_option)
        self.add_command(create_command)

        # Update Command
        update_command = PulpCliCommand('update', 'changes metadata on an existing repository', self.update)
        update_command.add_option(id_option)
        update_command.add_option(name_option)
        update_command.add_option(description_option)
        self.add_command(update_command)

        # Delete Command
        delete_command = PulpCliCommand('delete', 'deletes a repository', self.delete)
        delete_command.add_option(PulpCliOption('--id', 'identifies the repository to be deleted', required=True))
        self.add_command(delete_command)

        # List Command
        list_command = PulpCliCommand('list', 'lists repositories on the Pulp server', self.list)
        list_command.add_option(PulpCliFlag('--summary', 'if specified, only a minimal amount of repository information is displayed'))
        list_command.add_option(PulpCliOption('--fields', 'comma-separated list of repository fields; if specified, only the given fields will displayed', required=False))
        self.add_command(list_command)

    def create(self, **kwargs):

        # Collect input
        id = kwargs['id']
        name = kwargs['name'] or id
        description = kwargs['description']
        notes = None # TODO: add support later

        # Call the server
        self.context.server.repo.create(id, name, description, notes)
        self.prompt.render_success_message('Repository [%s] successfully created' % id)

    def update(self, **kwargs):

        # Assemble the delta for all options that were passed in
        delta = dict([(k, v) for k, v in kwargs.items() if v is not None])
        delta.pop('id') # not needed in the delta

        try:
            self.context.server.repo.update(kwargs['id'], {'delta' : delta})
            self.prompt.render_success_message('Repository [%s] successfully updated' % kwargs['id'])
        except NotFoundException:
            self.prompt.write('Repository [%s] does not exist on the server' % kwargs['id'], tag='not-found')


    def delete(self, **kwargs):
        id = kwargs['id']

        try:
            self.context.server.repo.delete(id)
            self.prompt.render_success_message('Repository [%s] successfully deleted' % id)
            self.prompt.render_spacer()
        except NotFoundException:
            self.prompt.write('Repository [%s] does not exist on the server' % id, tag='not-found')

    def list(self, **kwargs):
        self.prompt.render_title('Repositories')

        repo_list = self.context.server.repo.repositories()

        # Default flags to render_document_list
        filters = None
        order = ['id', 'display_name', 'description', 'content_unit_count']

        if kwargs['summary'] is True:
            filters = ['id', 'display_name']
            order = filters
        elif kwargs['fields'] is not None:
            filters = kwargs['fields'].split(',')
            if 'id' not in filters:
                filters.append('id')
            order = ['id']

        self.prompt.render_document_list(repo_list.response_body, filters=filters, order=order)

# -- utility ------------------------------------------------------------------

class Unparsable(Exception):
    """
    Raised by parse_unknown_args to indicate the argument string is invalid.
    """
    pass

def parse_unknown_args(args):
    """
    Parses arguments to add/update importer/distributor. Since the possible
    arguments are contingent on the type of plugin and thus not statically
    defined, we can't simply use optparse to gather them. This method will
    parse through the argument list and attempt to resolve the arguments into
    key/value pairs.

    The keys will be the name of the argument with any leading hyphens removed.
    The value will be one of three possibilties:
    * The string representation of the value immediately following it (common case)
    * The boolean True if no value or another argument definition follows it
    * A list of strings if the argument is specified more than once

    The argument/value pairs are returned as a dictionary. In the event an empty
    list of arguments is supplied, an empty dictionary is returned.

    @param args: list of arguments passed to the command
    @type  args: list

    @return: dictionary of argument name to value(s); see above for details
    @rtype:  dict
    """
    parsed = {}

    def arg_name(arg):
        if arg.startswith('--'):
            return arg[2:]
        elif arg.startswith('-'):
            return arg[1:]
        else:
            raise Unparsable()

    index = 0 # this won't necessarily step by 1 each time, so dont' use something like enumerate
    while index < len(args):
        item = args[index]
        name = arg_name(item)

        # If we're at the end there is nothing after it, it's also a flag.
        if (index + 1) == len(args):
            parsed[name] = True
            index += 1
            continue

        # If the next value is another argument, the current is a flag.
        if args[index + 1].startswith('-'):
            parsed[name] = True
            index += 1
            continue

        # If we're here, the next in the list is the value for the argument.
        value = args[index + 1]

        # If the argument already has a value, convert the value to a list and
        # add in the new one (preserving order).
        if name in parsed:
            if not isinstance(parsed[name], list):
                parsed[name] = [parsed[name]]
            parsed[name].append(value)
        else:
            parsed[name] = value

        index += 2 # to take into account the value we read

    return parsed