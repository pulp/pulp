# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

import os
from pulp.agent.lib.handler import SystemHandler
from pulp.agent.lib.report import RebootReport
from logging import getLogger

log = getLogger(__name__)


class LinuxHandler(SystemHandler):
    """
    Linux system handler
    """

    def reboot(self, options={}):
        """
        Schedule a system reboot.
        """
        report = RebootReport()
        apply = options.get('apply', True)
        if apply:
            minutes = options.get('minutes', 10)
            command = 'shutdown -r +%d' % minutes
            log.info(command)
            os.system(command)
        report.succeeded()
        return report
