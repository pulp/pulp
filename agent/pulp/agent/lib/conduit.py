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

    @property
    def consumer_id(self):
        """
        Get the current consumer ID
        :return: The unique consumer ID of the currently running agent
        :rtype:  str
        """
        raise NotImplementedError()

    def get_consumer_config(self):
        """
        Get the consumer configuration.
        @return: The consumer configuration object.
        @rtype: L{pulp.common.config.Config}
        """
        raise NotImplementedError()

    def update_progress(self, report):
        """
        Report a progress update.
        The content of the progress report is at the discretion of
        the handler.  However, it must be json serializable.
        @param report: A progress report.
        @type report: object
        """
        log.info('Progress reported:%s', report)

    def cancelled(self):
        """
        Get whether the current operation has been cancelled.
        :return: True if cancelled, else False
        :rtype: bool
        """
        return False