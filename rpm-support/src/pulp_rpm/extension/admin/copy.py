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

from pulp.client.commands.unit import UnitCopyCommand
from pulp_rpm.common.ids import TYPE_ID_RPM, TYPE_ID_SRPM, TYPE_ID_DRPM

# -- constants ----------------------------------------------------------------

DESC_RPM = _('copy RPMs from one repository to another')
DESC_SRPM = _('copy SRPMs from one repository to another')
DESC_DRPM = _('copy DRPMs from one repository to another')


# -- commands -----------------------------------------------------------------

class RpmCopyCommand(UnitCopyCommand):

    def __init__(self, context):
        self.context = context
        def rpm_copy(**kwargs):
            return _copy(self.context, TYPE_ID_RPM, **kwargs)
        super(RpmCopyCommand, self).__init__(rpm_copy, name='rpm', description=DESC_RPM)


class SrpmCopyCommand(UnitCopyCommand):

    def __init__(self, context):
        self.context = context
        def srpm_copy(**kwargs):
            return _copy(self.context, TYPE_ID_SRPM, **kwargs)
        super(SrpmCopyCommand, self).__init__(srpm_copy, name='srpm', description=DESC_SRPM)


class DrpmCopyCommand(UnitCopyCommand):

    def __init__(self, context):
        self.context = context
        def drpm_copy(**kwargs):
            return _copy(self.context, TYPE_ID_DRPM, **kwargs)
        super(DrpmCopyCommand, self).__init__(drpm_copy, name='drpm', description=DESC_DRPM)


def _copy(context, type_id, **kwargs):
    """
    This is a generic command that will perform a search for any type of
    content and copy it from one repository to another

    :param type_id: type of unit being copied
    :type  type_id: str

    :param kwargs:  CLI options as input by the user and passed in by
                    okaara. These are search options defined elsewhere that
                    also
    :type  kwargs:  dict
    """
    from_repo = kwargs['from-repo-id']
    to_repo = kwargs['to-repo-id']
    kwargs['type_ids'] = [type_id]

    # If rejected an exception will bubble up and be handled by middleware
    response = context.server.repo_unit.copy(from_repo, to_repo, **kwargs)

    progress_msg = _('Progress on this task can be viewed using the '
                     'commands under "repo tasks".')

    if response.response_body.is_postponed():
        d = _('Unit copy postponed due to another operation on the destination '
              'repository.')
        d += progress_msg
        context.prompt.render_paragraph(d)
        context.prompt.render_reasons(response.response_body.reasons)
    else:
        context.prompt.render_paragraph(progress_msg)
