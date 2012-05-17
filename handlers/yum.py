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

from pulp.gc_client.agent.lib.handler import Handler
from pulp.gc_client.agent.lib.report import BindReport, CleanReport
from logging import getLogger, Logger

log = getLogger(__name__)


class BindHandler(Handler):
    """
    The bind request handler.
    Manages the /etc/yum.repos.d/pulp.repo based on bind requests.
    """

    def bind(self, definitions):
        """
        Bind a repository.
        @param definitions: A list of bind definitions.
        Definition:
            {consumer_id:<str>,
             repo_id:<str>,
             distributor_id:<str>,
             href:<str>,
             type_id:<str>,
             details:<dict>}
        @type definitions: list
        @return: A dispatch report.
        @rtype: L{BindReport}
        """
        log.info('bind: %s', definitions)
        report = BindReport()
        report.succeeded({}, 1)
        return report

    def rebind(self, definitions):
        """
        (Re)bind a repository.
        @param definitions: A list of bind definitions.
        Definition:
            {consumer_id:<str>,
             repo_id:<str>,
             distributor_id:<str>,
             href:<str>,
             type_id:<str>,
             details:<dict>}
        @type definitions: list
        @return: A dispatch report.
        @rtype: L{BindReport}
        """
        log.info('(re)bind: %s', definitions)
        report = BindReport()
        report.succeeded({}, 1)
        return report

    def unbind(self, repoid):
        """
        Bind a repository.
        @param repoid: A repository ID.
        @type repoid: str
        @return: A dispatch report.
        @rtype: L{BindReport}
        """
        log.info('unbind: %s', repoid)
        report = BindReport()
        report.succeeded({}, 1)
        return report

    def clean(self):
        """
        Bind a repository.
        @return: A dispatch report.
        @rtype: L{BindReport}
        """
        log.info('clean')
        report = CleanReport()
        report.succeeded({}, 1)
        return report
