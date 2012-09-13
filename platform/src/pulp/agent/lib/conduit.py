# Copyright (c) 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import logging


log = logging.getLogger(__name__)


class Conduit:
    """
    The handler conduit provides handlers to call back
    into the handler framework.
    """

    def update_progress(self, report):
        """
        Report a progress update.
        The content of the progress report is at the discretion of
        the handler.  However, it must be json serializable.
        @param report: A progress report.
        @type report: object
        """
        log.info('Progress reported:%s', report)