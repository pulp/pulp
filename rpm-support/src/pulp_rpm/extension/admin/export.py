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

from pulp.client.commands.repo.status import status, tasks
from pulp.client.commands.repo.sync_publish import RunPublishRepositoryCommand, PublishStatusCommand

from pulp_rpm.common import ids
from pulp_rpm.extension.admin.status import RpmIsoStatusRenderer

from pulp.client.extensions.extensions import PulpCliCommand, PulpCliOption

# -- commands -----------------------------------------------------------------

DESC_EXPORT_RUN = _('triggers an immediate ISO export of a repository')
DESC_EXPORT_STATUS = _('displays the status of a running ISO export of a repository')

DESC_ISO_PREFIX = _('prefix to use in the generated iso naming, default: <repoid>-<current_date>.iso')
OPTION_ISO_PREFIX = PulpCliOption('--iso-prefix', DESC_ISO_PREFIX, required=False)

DESC_START_DATE = _('start date for errata export')
OPTION_START_DATE = PulpCliOption('--start-date', DESC_START_DATE, required=False)

DESC_END_DATE = _('end date for errata export')
OPTION_END_DATE = PulpCliOption('--end-date', DESC_END_DATE, required=False)

class RpmIsoExportCommand(RunPublishRepositoryCommand):
    def __init__(self, context):
        super(RpmIsoExportCommand, self).__init__(context=context, 
                                                  renderer=RpmIsoStatusRenderer(context),
                                                  distributor_id=ids.TYPE_ID_DISTRIBUTOR_ISO, 
                                                  description=DESC_EXPORT_RUN)
        self.add_option(OPTION_ISO_PREFIX)
        self.add_option(OPTION_START_DATE)
        self.add_option(OPTION_END_DATE)
    
    # Still need to overload run method to pass these options to iso distributor
      

class RpmIsoStatusCommand(PublishStatusCommand):
    def __init__(self, context):
        super(RpmIsoStatusCommand, self).__init__(context=context, 
                                                  renderer=RpmIsoStatusRenderer(context),
                                                  description=DESC_EXPORT_STATUS)

        