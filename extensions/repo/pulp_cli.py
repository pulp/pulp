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

from optparse import Values
import os
import sys

from pulp.gc_client.framework.extensions import PulpCliSection, PulpCliCommand, PulpCliOption, PulpCliFlag
from pulp.gc_client.api.server import NotFoundException

# -- framework hook -----------------------------------------------------------

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

        # List Units Command
        units_command = PulpCliCommand('units', 'lists content units in the repository', self.units)
        units_command.add_option(id_option)
        self.add_command(units_command)

        # Subsections
        self.add_subsection(ImporterSection(context))
        self.add_subsection(SyncSection(context))

    def create(self, **kwargs):

        # Collect input
        id = kwargs['id']
        name = id
        if 'name' in kwargs:
            name = kwargs['name']
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

    def units(self, **kwargs):
        repo_id = kwargs['id']
        self.prompt.render_title('Units in Repository [%s]' % repo_id)

        query = {}
        units = self.context.server.repo_search.search(repo_id, query)

        self.prompt.render_document_list(units.response_body)

class ImporterSection(PulpCliSection):

    def __init__(self, context):
        PulpCliSection.__init__(self, 'importer', 'manage importers for existing repositories')
        self.context = context
        self.prompt = context.prompt

        # Add Importer Command
        required_options = [
            ('--id', 'identifies the repository'),
            ('--type_id', 'identifies the type of importer being added'),
        ]
        add_parser = UnknownArgsParser(self.prompt, 'repo add', required_options)
        self.add_command(PulpCliCommand('add', 'adds an importer to a repository', self.add_importer, parser=add_parser))

    def add_importer(self, **kwargs):
        repo_id = kwargs.pop('id')
        importer_type_id = kwargs.pop('type_id')

        # Everything left in kwargs is considered part of the importer config
        self.context.server.repo_importer.create(repo_id, importer_type_id, kwargs)
        self.prompt.render_success_message('Successfully added importer of type [%s] to repository [%s]' % (importer_type_id, repo_id))

class SyncSection(PulpCliSection):

    def __init__(self, context):
        PulpCliSection.__init__(self, 'sync', 'run, schedule, or view the status of sync operations')
        self.context = context
        self.prompt = context.prompt

        # Run an Immediate Sync
        run_command = PulpCliCommand('run', 'triggers an immediate sync of a specific repository', self.run)
        run_command.add_option(PulpCliOption('--id', 'identifies the repository to sync', required=True))
        self.add_command(run_command)

        # TODO: Add sync schedule and status commands

    def run(self, **kwargs):

        repo_id = kwargs['id']
        self.prompt.render_paragraph('Synchronizing repository [%s]' % repo_id)

        spinner = self.prompt.create_threaded_spinner()
        spinner.start()
        try:
            # TODO: Replace with unknown arg parsing and allow for sync override config
            self.context.server.repo_actions.sync(repo_id, None)
        finally:
            spinner.stop()

        self.prompt.render_success_message('Repository sync completed for repository [%s]' % repo_id)

# -- utility ------------------------------------------------------------------

class UnknownArgsParser:
    """
    Duck-typed parser that can be passed to a Command. This implementation won't
    expect all of the possible options to be enumerated ahead of time. This is
    useful for any server-plugin-related call where the arguments will vary
    based on the type of plugin being manipulated.

    While this instance will support undefined options and flags, it is possible
    to provide a list of required options. These will factor into the usage
    display and be validated
    """

    class Unparsable(Exception): pass
    class MissingRequired(Exception): pass

    def __init__(self, prompt, path, required_options=None, exit_on_abort=True):
        """
        @param prompt: prompt instance to write the usage to
        @type  prompt: PulpPrompt

        @param path: section/command path to reach the command currently executing
        @type  path: str

        @param required_options: list of tuples of option name to description
        @type  required_options: list

        @param exit_on_abort: flag that indicates how to proceed if the argument
               list cannot be parsed or is missing required values; if true,
               sys.exit will be called with the appropriate exit code; set to
               false during unit tests to cause an exception to raise instead
        @type  exit_on_abort: bool
        """

        self.prompt = prompt
        self.path = path
        self.required_options = required_options or []
        self.exit_on_abort = exit_on_abort

    def parse_args(self, args):
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

        @param args: tuple of arguments passed to the command
        @type  args: tuple

        @return: dictionary of argument name to value(s); see above for details
        @rtype:  dict
        """
        def arg_name(arg):
            if arg.startswith('--'):
                return arg[2:]
            elif arg.startswith('-'):
                return arg[1:]
            else:
                return None

        parsed = {}
        required_names = [r[0] for r in self.required_options]

        index = 0 # this won't necessarily step by 1 each time, so dont' use something like enumerate
        while index < len(args):
            item = args[index]

            # The required names use the option name directly (with the hyphens)
            # so do the check here
            if item in required_names:
                required_names.remove(item)

            name = arg_name(item)

            if name is None or name in ('h', 'help'):
                self.usage()
                self.abort(exception_class=self.Unparsable)

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

        # If all of the required options haven't been removed yet, we're
        # missing at least one.
        if len(required_names) > 0:
            self.usage()
            self.abort(exception_class=self.MissingRequired)

        # The CLI is expecting the return result of OptionParser, which wraps
        # the dict in Values, so we do that here.
        return Values(parsed), []

    def usage(self):
        launch_script = os.path.basename(sys.argv[0])
        self.prompt.write('Usage: %s %s OPTION [OPTION, ..]' % (launch_script, self.path))
        self.prompt.render_spacer()

        m  = 'Options will vary based on the type of server-side plugin being used. '
        m += 'Valid options follow one of the following formats:'
        self.prompt.write(m)

        self.prompt.write('  --<option> <value>')
        self.prompt.write('  --<flag>')
        self.prompt.render_spacer()

        if len(self.required_options) > 0:
            self.prompt.write('The following options are required:')

            max_width = reduce(lambda x, y: max(x, len(y[0])), self.required_options, 0)
            template = '  %-' + str(max_width) + 's - %s'
            for r, d in self.required_options:
                self.prompt.write(template % (r, d))

    def abort(self, exception_class=None):
        """
        Called when the arguments are unparsable or missing. The actual
        OptionParser implementation calls sys.exit on a failed parse, so
        this method, by default, does the same (this is actually a cleaner
        implementation since it uses the EX_USAGE code where as OptionParser
        just exits with 2, but I digress).

        The instance variable exit_on_abort controls the behavior of this call.
        That variable should be set to false to avoid the sys.exit call in the
        case of a unit test.
        """
        if self.exit_on_abort:
            sys.exit(os.EX_USAGE)
        else:
            raise exception_class('Parsing aborted')
