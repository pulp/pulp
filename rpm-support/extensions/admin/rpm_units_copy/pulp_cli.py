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
from pulp.client.search import UnitCopyCommand

# -- constants ----------------------------------------------------------------

TYPE_RPM = 'rpm'
TYPE_SRPM = 'srpm'
TYPE_DRPM = 'drpm'

LOG = None # set by context

RPM_USAGE_DESC = 'Packages to copy from the source repository are determined by '\
                 'applying regular expressions for inclusion (match) and exclusion (not). '\
                 'Criteria are specified in the format "field=regex", for example "name=python.*". '\
                 'Except for the date checks, all arguments may be specified multiple times to further '\
                 'refine the matching criteria. '\
                 'Valid fields are: name, epoch, version, release, arch, buildhost, checksum, '\
                 'description, filename, license, and vendor.'
RPM_USAGE_DESC = _(RPM_USAGE_DESC)

# -- plugin hook --------------------------------------------------------------

def initialize(context):

    global LOG
    LOG = context.logger

    repo_section = context.cli.find_section('repo')
    repo_section.add_subsection(CopySection(context))


class CopySection(PulpCliSection):
    def __init__(self, context):
        super(CopySection, self).__init__('copy', _('copy units between repositories'))
        self.context = context

        m = _('copy RPMs from one repository to another')
        self.add_command(UnitCopyCommand(self.rpm, name='rpm', description=m))

        m = _('copy SRPMs from one repository to another')
        self.add_command(UnitCopyCommand(self.srpm, name='srpm', description=m))

        m = _('copy DRPMs from one repository to another')
        self.add_command(UnitCopyCommand(self.drpm, name='drpm', description=m))

    def rpm(self, **kwargs):
        self._copy(TYPE_RPM, **kwargs)

    def srpm(self, **kwargs):
        self._copy(TYPE_SRPM, **kwargs)

    def drpm(self, **kwargs):
        self._copy(TYPE_DRPM, **kwargs)

    def _copy(self, type_id, **kwargs):
        """
        This is a generic command that will perform a search for any type of
        content and copy it from one repository to another

        :param type_ids:    list of type IDs that the command should operate on
        :type  type_ids:    list

        :param kwargs:  CLI options as input by the user and passed in by
                        okaara. These are search options defined elsewhere that
                        also
        :type  kwargs:  dict
        """
        from_repo = kwargs['from-repo-id']
        to_repo = kwargs['to-repo-id']
        kwargs['type_ids'] = [type_id]

        # If rejected an exception will bubble up and be handled by middleware
        response = self.context.server.repo_unit.copy(from_repo, to_repo, **kwargs)

        progress_msg = 'Progress on this task can be viewed using the '\
                       'commands under "repo tasks".'
        progress_msg = _(progress_msg)
        if response.response_body.is_postponed():
            d = 'Unit copy postponed due to another operation on the destination '\
                'repository. '
            d = _(d) + progress_msg
            self.context.prompt.render_paragraph(d)
            self.context.prompt.render_reasons(response.response_body.reasons)
        else:
            self.context.prompt.render_paragraph(progress_msg)
