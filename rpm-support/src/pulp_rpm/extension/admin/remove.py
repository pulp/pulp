# Copyright (c) 2012 Red Hat, Inc.
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

from pulp.client.commands.options import OPTION_REPO_ID
from pulp.client.commands.unit import UnitRemoveCommand

from pulp_rpm.common.ids import (TYPE_ID_RPM, TYPE_ID_SRPM, TYPE_ID_DRPM,
                                 TYPE_ID_ERRATA, TYPE_ID_PKG_GROUP,
                                 TYPE_ID_PKG_CATEGORY)

# -- constants ----------------------------------------------------------------

DESC_RPM = _('remove RPMs from a repository')
DESC_SRPM = _('remove SRPMs from a repository')
DESC_DRPM = _('remove DRPMs from a repository')
DESC_ERRATA = _('remove errata from a repository')
DESC_GROUP = _('remove package groups from a repository')
DESC_CATEGORY = _('remove package categories from a repository')

# -- commands -----------------------------------------------------------------

class _BaseRemoveCommand(UnitRemoveCommand):

    def __init__(self, context, name, description, type_id):
        super(_BaseRemoveCommand, self).__init__(name=name, description=description,
                                                 method=self.remove)
        self.context = context
        self.type_id = type_id

    def remove(self, **kwargs):
        """
        Handles the remove operation for units of the given type.

        :param type_id: type of unit being removed
        :type  type_id: str
        :param kwargs: CLI options as input by the user and parsed by the framework
        :type  kwargs: dict
        """
        UnitRemoveCommand.ensure_criteria(kwargs)

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


class RpmRemoveCommand(_BaseRemoveCommand):

    def __init__(self, context):
        super(RpmRemoveCommand, self).__init__(context, 'rpm', DESC_RPM, TYPE_ID_RPM)


class SrpmRemoveCommand(_BaseRemoveCommand):

    def __init__(self, context):
        super(SrpmRemoveCommand, self).__init__(context, 'srpm', DESC_SRPM, TYPE_ID_SRPM)


class DrpmRemoveCommand(_BaseRemoveCommand):

    def __init__(self, context):
        super(DrpmRemoveCommand, self).__init__(context, 'drpm', DESC_DRPM, TYPE_ID_DRPM)


class ErrataRemoveCommand(_BaseRemoveCommand):

    def __init__(self, context):
        super(ErrataRemoveCommand, self).__init__(context, 'errata', DESC_ERRATA, TYPE_ID_ERRATA)


class PackageGroupRemoveCommand(_BaseRemoveCommand):

    def __init__(self, context):
        super(PackageGroupRemoveCommand, self).__init__(context, 'group', DESC_GROUP, TYPE_ID_PKG_GROUP)


class PackageCategoryRemoveCommand(_BaseRemoveCommand):

    def __init__(self, context):
        super(PackageCategoryRemoveCommand, self).__init__(context, 'category',
                                                           DESC_CATEGORY, TYPE_ID_PKG_CATEGORY)
