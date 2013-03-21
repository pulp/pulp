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

from gettext import gettext as _
from okaara.cli import CommandUsage
import sys

from pulp.bindings.exceptions import BadRequestException
from pulp.client.commands.criteria import UnitAssociationCriteriaCommand
from pulp.client.commands.options import OPTION_REPO_ID
from pulp.client.commands.polling import PollingCommand
from pulp.client.extensions.extensions import PulpCliCommand, PulpCliOption, PulpCliFlag


DESC_COPY = _('copies modules from one repository into another')

DESC_FROM_REPO = _('source repository from which units will be copied')
OPTION_FROM_REPO = PulpCliOption('--from-repo-id', DESC_FROM_REPO, aliases=['-f'], required=True)

DESC_TO_REPO = _('destination repository to copy units into')
OPTION_TO_REPO = PulpCliOption('--to-repo-id', DESC_TO_REPO, aliases=['-t'], required=True)

OPTION_TYPE = PulpCliOption('--type',
                            _('restrict to one content type such as "rpm", "errata", "puppet_module", etc.'),
                            required=False)
OPTION_UNIT_ID = PulpCliOption('--unit-id',
                               _('ID of a content unit; if specified, you must also specify a type'),
                               required=False)


class UnitCopyCommand(UnitAssociationCriteriaCommand, PollingCommand):

    def __init__(self, context, name='copy', description=DESC_COPY, method=None,
                 type_id=None, *args, **kwargs):

        # Handle odd constructor in UnitAssociationCriteriaCommand
        kwargs['name'] = name
        kwargs['description'] = description

        # We're not searching, we're using it to specify units
        kwargs['include_search'] = False

        if method is None:
            method = self.run

        PollingCommand.__init__(self, name, description, method, context)
        UnitAssociationCriteriaCommand.__init__(self, method, *args, **kwargs)

        self.type_id = type_id
        self.context = context
        self.prompt = context.prompt

        # Remove the default repo-id option that's added by the criteria, we have
        # specific variations on it
        self.options = [opt for opt in self.options if opt.name != '--repo-id']

        self.add_option(OPTION_FROM_REPO)
        self.add_option(OPTION_TO_REPO)

    def run(self, **kwargs):
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
            self.poll([task])
        except BadRequestException, e:
            if 'source_repo_id' in e.extra_data.get('property_names', []):
                e.extra_data['property_names'].remove('source_repo_id')
                e.extra_data['property_names'].append('from-repo-id')
            raise e, None, sys.exc_info()[2]

    def modify_user_input(self, user_input):
        """
        Hook to modify the user inputted values that are passed to the copy call. The copy
        call will take care of translating the contents of this dict into a Pulp criteria
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
        if 'type_ids' not in user_input and self.type_id is not None:
            user_input['type_ids'] = [self.type_id]

    def generate_override_config(self, **kwargs):
        """
        Subclasses may override this to introduce an override config value to the copy
        command. If not overridden, an empty override config will be specified.

        :param kwargs: parsed from the user input

        :return: value to pass the copy call as its override_config parameter
        """
        return {}


class UnitRemoveCommand(UnitAssociationCriteriaCommand):
    def __init__(self, context, type_id, *args, **kwargs):
        self.context = context
        self.type_id = type_id
        kwargs['include_search'] = False
        if not kwargs.get('method'):
            kwargs['method'] = self.remove

        super(UnitRemoveCommand, self).__init__(*args, **kwargs)

    def remove(self, **kwargs):
        """
        Handles the remove operation for units of the given type.

        :param type_id: type of unit being removed
        :type  type_id: str
        :param kwargs: CLI options as input by the user and parsed by the framework
        :type  kwargs: dict
        """
        super(UnitRemoveCommand, self).ensure_criteria(kwargs)

        repo_id = kwargs.pop(OPTION_REPO_ID.keyword)
        kwargs['type_ids'] = [self.type_id] # so it will be added to the criteria

        response = self.context.server.repo_unit.remove(repo_id, **kwargs)

        progress_msg = _('Progress on this task can be viewed using the '
                         'commands under "repo tasks".')

        if response.response_body.is_postponed():
            d = _('Unit removal postponed due to another operation on the destination '
                  'repository. ')
            d += progress_msg
            self.context.prompt.render_paragraph(d)
            self.context.prompt.render_reasons(response.response_body.reasons)
        else:
            self.context.prompt.render_paragraph(progress_msg)


class OrphanUnitListCommand(PulpCliCommand):
    def __init__(self, context):
        self.context = context
        self.prompt = context.prompt

        m = _('display a list of orphaned units')
        super(OrphanUnitListCommand, self).__init__('list', m, self.run)

        self.add_option(OPTION_TYPE)

        m = _('include a detailed list of the individual orphaned units')
        details_flag = PulpCliFlag('--details', m)
        self.add_flag(details_flag)

    def run(self, **kwargs):
        content_type = kwargs.get('type', None)
        show_details = kwargs.get('details', False)

        if content_type is not None:
            orphans = self.context.server.content_orphan.orphans_by_type(content_type).response_body
        else:
            orphans = self.context.server.content_orphan.orphans().response_body

        summary = {}

        for orphan in orphans:
            orphan_type = orphan['_content_type_id']
            summary[orphan_type] = summary.get(orphan_type, 0) + 1

            if show_details:
                # set the 'id' if it's not already there
                orphan.setdefault('id', orphan.get('_id', None))
                self.prompt.render_document(orphan)

        order = summary.keys()
        order.sort()
        order.append('Total')

        summary['Total'] = sum(summary.values())

        self.prompt.render_title(_('Summary'))
        self.prompt.render_document(summary, order=order)


class OrphanUnitRemoveCommand(PulpCliCommand):
    def __init__(self, context):
        self.context = context
        self.prompt = context.prompt

        m = _('remove one or more orphaned units')
        super(OrphanUnitRemoveCommand, self).__init__('remove', m, self.run)

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

        self.check_task_status(response.response_body)

    def check_task_status(self, task):
        """
        Check the status of a task response and make appropriate CLI output

        :param task: Task as returned by the API call
        """
        response = task.response
        if response == 'rejected':
            self.prompt.render_failure_message(_('Request was rejected'))
            self.prompt.render_reasons(task.reasons)
        else:
            self.prompt.render_success_message(_('Request accepted'))
            self.prompt.write(
                _('check status of task %(t)s with "pulp-admin tasks details"')
                % {'t' : task.task_id})
