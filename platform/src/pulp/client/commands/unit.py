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

from pulp.client.commands.criteria import UnitAssociationCriteriaCommand
from pulp.client.extensions.extensions import PulpCliCommand, PulpCliOption, PulpCliFlag


class UnitCopyCommand(UnitAssociationCriteriaCommand):
    def __init__(self, method, *args, **kwargs):
        kwargs['include_search'] = False
        super(UnitCopyCommand, self).__init__(method, *args, **kwargs)
        self.options = [opt for opt in self.options if opt.name != '--repo-id']

        m = 'source repository from which units will be copied'
        self.create_option('--from-repo-id', _(m), ['-f'], required=True)

        m = 'destination repository to copy units into'
        self.create_option('--to-repo-id', _(m), ['-t'], required=True)


class UnitRemoveCommand(UnitAssociationCriteriaCommand):
    def __init__(self, *args, **kwargs):
        kwargs['include_search'] = False
        super(UnitRemoveCommand, self).__init__(*args, **kwargs)


type_option = PulpCliOption('--type',
    _('restrict to one content type such as "rpm", "errata", etc.'),
    required=False)
unit_id_option = PulpCliOption('--unit-id',
    _('ID of a content unit. If specified, you must also specify a type'),
    required=False)


class OrphanUnitListCommand(PulpCliCommand):
    def __init__(self, context):
        self.context = context
        self.prompt = context.prompt

        m = _('display a list of orphaned units')
        super(OrphanUnitListCommand, self).__init__('list', m, self.run)

        self.add_option(type_option)

        m = _('include a count of how many orphaned units exist of each type')
        summary_flag = PulpCliFlag('--summary', m, ('-s',))
        self.add_flag(summary_flag)

    def run(self, **kwargs):
        content_type = kwargs.get('type')
        if content_type:
            orphans = self.context.server.content_orphan.orphans_by_type(content_type).response_body
        else:
            orphans = self.context.server.content_orphan.orphans().response_body
        summary = {}
        for orphan in orphans:
            orphan_type = orphan['_content_type_id']
            summary[orphan_type] = summary.get(orphan_type, 0) + 1
            orphan['id'] = orphan.get('_id', None)
            self.prompt.render_document(orphan)

        if kwargs.get('summary'):
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

        self.add_option(type_option)
        self.add_option(unit_id_option)

        m = _('remove all orphaned units, ignoring other options')
        self.add_flag(PulpCliFlag('--all', m))

    def run(self, **kwargs):
        content_type = kwargs.get('type')
        unit_id = kwargs.get('unit-id')
        if unit_id and not content_type:
            raise CommandUsage([type_option])

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
