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


from pulp.agent.lib.handler import ContentHandler
from pulp.agent.lib.report import HandlerReport
from logging import getLogger

log = getLogger(__name__)


class RepositoryHandler(ContentHandler):

    def update(self, units, options):
        """
        Update content unit(s).
        Unit key of {} or None indicates updates update all
        but only if (all) option is True.
        @param units: A list of content unit_keys.
        @type units: list
        @param options: Unit update options.
        @type options: dict
        @return: An update report.  See: L{Package.update}
        @rtype: L{HandlerReport}
        """
        report = HandlerReport()
        all = options.get('all', False)
        repo_ids = [key['repo_id'] for key in units if key]
        if repo_ids or all:
            report.succeeded(repo_ids or all)
        return report