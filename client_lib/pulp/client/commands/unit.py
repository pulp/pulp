# -*- coding: utf-8 -*-

from gettext import gettext as _
import sys

from okaara.cli import CommandUsage

from pulp.client.extensions.core import COLOR_FAILURE
from pulp.common import util
from pulp.common.constants import DISPLAY_UNITS_DEFAULT_MAXIMUM
from pulp.bindings.exceptions import BadRequestException
from pulp.client.commands.criteria import UnitAssociationCriteriaCommand
from pulp.client.commands.options import OPTION_REPO_ID
from pulp.client.commands.polling import PollingCommand
from pulp.client.extensions.extensions import PulpCliCommand, PulpCliOption, PulpCliFlag


DESC_COPY = _('copies modules from one repository into another')
DESC_REMOVE = _('remove copied or uploaded units from a repository')

DESC_FROM_REPO = _('source repository from which units will be copied')
OPTION_FROM_REPO = PulpCliOption('--from-repo-id', DESC_FROM_REPO, aliases=['-f'], required=True)

DESC_TO_REPO = _('destination repository to copy units into')
OPTION_TO_REPO = PulpCliOption('--to-repo-id', DESC_TO_REPO, aliases=['-t'], required=True)

OPTION_TYPE = PulpCliOption('--type',
                            _('restrict to one content type such as "rpm", "errata", '
                              '"puppet_module", etc.'),
                            required=False)
OPTION_UNIT_ID = \
    PulpCliOption('--unit-id',
                  _('ID of a content unit; if specified, you must also specify a type'),
                  required=False)

RETURN_REMOVE_SUCCESS_STRING = _('Units Removed:')
RETURN_REMOVE_ERROR_STRING = _('Error Removing Units. This could because the units were created '
                               'by a different user or were imported via a feed. You do not have '
                               'permissions to remove the following units:')

RETURN_COPY_SUCCESS_STRING = _('Copied:')
RETURN_COPY_ERROR_STRING = _('Error Copying Units:')


class UnitRemoveCommand(UnitAssociationCriteriaCommand, PollingCommand):
    """
    Generic command for removing units from a repository.  This provides the basis for
    the remove actions that are performed by each repository type.
    """

    def __init__(self, context, name='remove', description=DESC_REMOVE, method=None,
                 type_id=None, **kwargs):
        """
        :param context: client context
        :type  context: pulp.client.extensions.core.ClientContext
        :param name: The name of the command
        :type name: str
        :param description: the textual discription that will be displayed in the shell
        :type description: str
        :param method: method that will be fun when the command is invoked
        :type  method: function
        :param type_id: The type of units that this remove command supports
        :type type_id: str
        """

        # Handle odd constructor in UnitAssociationCriteriaCommand
        kwargs['name'] = name
        kwargs['description'] = description

        # We're not searching, we're using it to specify units
        kwargs['include_search'] = False

        method = method or self.run

        PollingCommand.__init__(self, name, description, method, context)
        UnitAssociationCriteriaCommand.__init__(self, method, **kwargs)

        self.type_id = type_id
        self.max_units_displayed = DISPLAY_UNITS_DEFAULT_MAXIMUM

    def run(self, **kwargs):
        """
        Hook used to run the command.
        """
        self.ensure_criteria(kwargs)

        repo_id = kwargs.pop(OPTION_REPO_ID.keyword)
        self.modify_user_input(kwargs)

        response = self.context.server.repo_unit.remove(repo_id, **kwargs)
        task = response.response_body
        self.poll([task], kwargs)

    def modify_user_input(self, user_input):
        """
        Hook to modify the user entered values that are passed to the remove call. The remove
        bindings call will take care of translating the contents of this dict into a Pulp criteria
        document. Overridden implementations may use this opportunity to add in fields that
        the user is not prompted for but still need to be in the criteria. In most cases,
        this method need not be overridden.

        By default, this call will add in the type_id value specified at instantiation time
        (if one was set). See RepositoryUnitAPI._generate_search_criteria for more information
        on what keys are utilitized.

        This call must modify the specified dict; its return value is ignored.

        :param user_input: dict of command option keywords to user inputted values
        :type  user_input: dict

        :return:
        """
        if self.type_id is not None:
            user_input['type_ids'] = [self.type_id]

    def succeeded(self, task):
        """
        Hook that is called when a task completes successfully.
        :param task: The task that was executing
        :type task: task
        """
        self.display_task_results(task, RETURN_REMOVE_SUCCESS_STRING, RETURN_REMOVE_ERROR_STRING)

    def display_task_results(self, task, success_string, error_string):
        """
        :param task: the task that was run
        :type task: task
        :param success_string: The string to display before showing the successfully processed units
        :type success_string: str
        :param error_string: The string to display before showing the units that failed processing
        :type error_string: str
        """
        result = task.result  # entries are a dict containing unit_key and type_id
        units_successful = result.get('units_successful', [])
        units_failed = result.get('units_failed', [])
        total_units = len(units_successful) + len(units_failed)
        unit_threshold_reached = self.max_units_displayed < (len(units_successful) +
                                                             len(units_failed))

        if total_units == 0:
            self.prompt.write(_('Nothing found that matches the given criteria.'), tag='too-few')
        else:
            # Display the successfully processed units
            self.prompt.write(success_string)
            if len(units_successful) == 0:
                self.prompt.write(_('  None'), tag="none")
            elif unit_threshold_reached:
                self._summary(self.prompt.write, units_successful)
            else:
                self._details(self.prompt.write, units_successful)

            if len(units_failed) > 0:
                func_args = []
                func_kwargs = {'color': COLOR_FAILURE}
                error_prompt = util.partial(self.prompt.write, *func_args, **func_kwargs)
                error_prompt(error_string)
                # Display the units we were unable to remove
                if unit_threshold_reached:
                    self._summary(self.prompt.write, units_failed)
                else:
                    self._details(error_prompt, units_failed)

    def _summary(self, prompt_writer, units):
        """
        Displays a shortened view of the units. This implementation will display a count of units
        by type.
        """
        # Create count by each by type
        unit_count_by_type = {}
        for u in units:
            count = unit_count_by_type.setdefault(u['type_id'], 0)
            unit_count_by_type[u['type_id']] = count + 1

        for type_id, count in unit_count_by_type.items():
            entry = '  %s: %s' % (type_id, count)
            prompt_writer(entry)

    def _details(self, prompt_writer, units):
        """
        Displays information about each unit. If multiple types are present, the
        list will be broken down by type. As each unit is rendered, care should be taken to not call
        this with a large amount of units as it will flood the user's terminal.
        """

        # Restructure into a list of unit keys by type
        units_by_type = {}
        map(lambda u: units_by_type.setdefault(u['type_id'], []).append(u['unit_key']), units)

        # Each unit is formatted to accommodate its unit key and displayed
        sorted_type_ids = sorted(units_by_type.keys())
        for type_id in sorted_type_ids:
            unit_list = units_by_type[type_id]
            formatter = self.get_formatter_for_type(type_id)

            # Only display the type header if there's more than one type present
            if len(units_by_type) > 1:
                prompt_writer(' %s:' % type_id)

            # Preformat so we can apply the same alpha sort to each type instead of having a
            # custom comparator function per type
            formatted_units = map(lambda u: formatter(u), unit_list)
            formatted_units.sort()
            for u in formatted_units:
                prompt_writer('  %s' % u)

    def get_formatter_for_type(self, type_id):
        """
        Return a method that takes one argument (a unit key) and formats a short display string
        to be used as the output for the unit_remove command

        :param type_id: The type of the unit for which a formatter is needed
        :type type_id: str
        """
        raise NotImplementedError()


class UnitCopyCommand(UnitRemoveCommand):
    """
    Generic command for copying units from one repository to another
    """

    def __init__(self, context, name='copy', description=DESC_COPY, method=None,
                 type_id=None, **kwargs):
        """
        :param context: client context
        :type  context: pulp.client.extensions.core.ClientContext
        :param name: The name of the command
        :type name: str
        :param description: the textual discription that will be displayed in the shell
        :type description: str
        :param method: method that will be fun when the command is invoked
        :type  method: function
        :param type_id: The type of units that this remove command supports
        :type type_id: str
        """
        UnitRemoveCommand.__init__(self, context, name, description, method, type_id, **kwargs)

        self.add_option(OPTION_FROM_REPO)
        self.add_option(OPTION_TO_REPO)

    def add_repo_id_option(self):
        """
        Override the method from the criteria command so that we can prevent the
        --repo-id option from being displayed as it is not relevant to this command
        """
        pass  # use from-repo-id and to-repo-id instead

    def run(self, **kwargs):
        """
        Hook used to run the command.
        """
        from_repo = kwargs['from-repo-id']
        to_repo = kwargs['to-repo-id']

        # If rejected an exception will bubble up and be handled by middleware.
        # The only caveat is if the source repo ID is invalid, it will come back
        # from the server as source_repo_id. The client-side name for this value
        # is from-repo-id, so do a quick substitution in the exception and then
        # reraise it for the middleware to handle like normal.
        try:
            self.modify_user_input(kwargs)
            override_config = self.generate_override_config(**kwargs)
            response = self.context.server.repo_unit.copy(from_repo, to_repo,
                                                          override_config=override_config, **kwargs)
            task = response.response_body
            self.poll([task], kwargs)
        except BadRequestException, e:
            if 'source_repo_id' in e.extra_data.get('property_names', []):
                e.extra_data['property_names'].remove('source_repo_id')
                e.extra_data['property_names'].append('from-repo-id')
            raise e, None, sys.exc_info()[2]

    def succeeded(self, task):
        """
        Hook that is called when a task completes successfully.

        :param task: The task that was executing
        :type task: task
        """
        self.display_task_results(task, RETURN_COPY_SUCCESS_STRING, RETURN_COPY_ERROR_STRING)

    def generate_override_config(self, **kwargs):
        """
        Subclasses may override this to introduce an override config value to the copy
        command. If not overridden, an empty override config will be specified.

        :param kwargs: parsed from the user input

        :return: value to pass the copy call as its override_config parameter
        """
        return {}


class OrphanUnitListCommand(PulpCliCommand):
    def __init__(self, context):
        self.context = context
        self.prompt = context.prompt

        m = _('display a list of orphaned units')
        super(OrphanUnitListCommand, self).__init__('list', m, self.run)

        self.add_option(OPTION_TYPE)

        m = _('include a detailed list of the individual orphaned units, ignored when content '
              'type is not specified')
        details_flag = PulpCliFlag('--details', m)
        self.add_flag(details_flag)

    def run(self, **kwargs):
        content_type = kwargs.get('type', None)
        show_details = kwargs.get('details', False)

        summary = {}

        if content_type is not None:
            orphans = self.context.server.content_orphan.orphans_by_type(content_type).response_body

            for orphan in orphans:
                orphan_type = orphan['_content_type_id']
                summary[orphan_type] = summary.get(orphan_type, 0) + 1

                if show_details:
                    # set the 'id' if it's not already there
                    orphan.setdefault('id', orphan.get('_id', None))
                    self.prompt.render_document(orphan)

        else:
            if show_details:
                self.prompt.write(_('no content type specified; details flag ignored'))

            rest_summary = self.context.server.content_orphan.orphans().response_body

            for key, value in rest_summary.items():
                summary[key] = value['count']

        order = summary.keys()
        order.sort()
        order.append('Total')

        summary['Total'] = sum(summary.values())

        self.prompt.render_title(_('Summary'))
        self.prompt.render_document(summary, order=order)


class OrphanUnitRemoveCommand(PollingCommand):
    def __init__(self, context):
        self.context = context
        self.prompt = context.prompt

        m = _('remove one or more orphaned units')
        super(OrphanUnitRemoveCommand, self).__init__('remove', m, self.run, context)

        self.add_option(OPTION_TYPE)
        self.add_option(OPTION_UNIT_ID)

        m = _('remove all orphaned units, ignoring other options')
        self.add_flag(PulpCliFlag('--all', m))

    def run(self, **kwargs):
        content_type = kwargs.get('type')
        unit_id = kwargs.get('unit-id')
        if unit_id and not content_type:
            raise CommandUsage([OPTION_TYPE])

        if kwargs.get('all'):
            response = self.context.server.content_orphan.remove_all()
        elif content_type and unit_id:
            response = self.context.server.content_orphan.remove(content_type, unit_id)
        elif content_type:
            response = self.context.server.content_orphan.remove_by_type(content_type)
        else:
            raise CommandUsage

        self.poll(response.response_body, kwargs)
