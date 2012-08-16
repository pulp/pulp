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

from pulp.client.extensions.extensions import PulpCliSection
from pulp.client.search import UnitRemoveCommand
from pulp_rpm.common.ids import TYPE_ID_RPM, TYPE_ID_SRPM, TYPE_ID_DRPM, TYPE_ID_ERRATA, TYPE_ID_PKG_GROUP, TYPE_ID_PKG_CATEGORY

# -- plugin hook --------------------------------------------------------------

def initialize(context):
    repo_section = context.cli.find_section('repo')
    repo_section.add_subsection(RemoveSection(context))

class RemoveSection(PulpCliSection):
    def __init__(self, context):
        super(RemoveSection, self).__init__('remove', _('remove units from a repository'))
        self.context = context

        # Tuples of data to ease the creation of the individual commands. Tuples contain:
        #   Type ID, Function, Display Name (pluralized), Command Name
        type_bundles = [
            (TYPE_ID_RPM, self.rpm, _('RPMs'), 'rpm'),
            (TYPE_ID_SRPM, self.srpm, _('SRPMs'), 'srpm'),
            (TYPE_ID_DRPM, self.drpm, _('DRPMs'), 'drpm'),
            (TYPE_ID_ERRATA, self.errata, _('errata'), 'errata'),
            (TYPE_ID_PKG_GROUP, self.pkg_group, _('package groups'), 'package-group'),
            (TYPE_ID_PKG_CATEGORY, self.pkg_category, _('package categories'), 'package-category'),
        ]

        for type_id, func, display, name in type_bundles:
            m = _('remove %(d)s from a repository') % {'d' : display}
            self.add_command(UnitRemoveCommand(func, name=name, description=m))

    def rpm(self, **kwargs):
        self._remove(TYPE_ID_RPM, **kwargs)

    def srpm(self, **kwargs):
        self._remove(TYPE_ID_SRPM, **kwargs)

    def drpm(self, **kwargs):
        self._remove(TYPE_ID_DRPM, **kwargs)

    def errata(self, **kwargs):
        self._remove(TYPE_ID_ERRATA, **kwargs)

    def pkg_group(self, **kwargs):
        self._remove(TYPE_ID_PKG_GROUP, **kwargs)

    def pkg_category(self, **kwargs):
        self._remove(TYPE_ID_PKG_CATEGORY, **kwargs)

    def _remove(self, type_id, **kwargs):
        """
        Handles the remove operation for units of the given type.

        :param type_id: type of unit being removed
        :type  type_id: str
        :param kwargs: CLI options as input by the user and parsed by the framework
        :type  kwargs: dict
        """
        UnitRemoveCommand.ensure_criteria(kwargs)

        repo_id = kwargs.pop('repo-id')
        kwargs['type_ids'] = [type_id] # so it will be added to the criteria

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
