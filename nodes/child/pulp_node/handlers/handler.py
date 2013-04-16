# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

from logging import getLogger

from pulp.agent.lib.handler import ContentHandler
from pulp.agent.lib.report import ContentReport

from pulp_node import constants
from pulp_node.handlers.strategies import find_strategy
from pulp_node.handlers.reports import HandlerProgress, SummaryReport
from pulp_node.handlers.model import ParentBinding


log = getLogger(__name__)


class NodeHandler(ContentHandler):

    def update(self, conduit, units, options):
        """
        Update the specified content units.  Each unit must be of
        type 'node'.  Updates the entire child node.

        Report format:
          succeeded: <bool>
          details: {
            errors: [
              { error_id: <str>,
                details: {}
              },
            ]
            repositories: [
              { repo_id: <str>,
                action: <str>,
                units: {
                  added: <int>,
                  updated: <int>,
                  removed: <int>
                }
              },
            ]
          }

        :param conduit: A handler conduit.
        :type conduit: pulp.agent.lib.conduit.Conduit
        :param units: A list of content unit_keys.
        :type units: list
        :param options: Unit update options.
        :type options: dict
        :return: An update report.
        :rtype: ContentReport
        """
        summary_report = SummaryReport()
        progress_report = HandlerProgress(conduit)
        bindings = ParentBinding.fetch_all()

        strategy_name = options.setdefault(constants.STRATEGY_KEYWORD, constants.MIRROR_STRATEGY)
        strategy_class = find_strategy(strategy_name)
        strategy = strategy_class(progress_report, summary_report)
        strategy.synchronize(bindings, options)

        for ne in summary_report.errors:
            log.error(ne)

        handler_report = ContentReport()
        if summary_report.succeeded():
            handler_report.set_succeeded(summary_report.dict())
        else:
            handler_report.set_failed(summary_report.dict())
        return handler_report


class RepositoryHandler(ContentHandler):

    def update(self, conduit, units, options):
        """
        Update the specified content units.  Each unit must be
        of type 'repository'.  Updates only the repositories specified in
        the unit_key by repo_id.
        :param conduit: A handler conduit.
        :type conduit: pulp.agent.lib.conduit.Conduit
        :param units: A list of content unit_keys.
        :type units: list
        :param options: Unit update options.
        :type options: dict
        :return: An update report.
        :rtype: ContentReport
        """
        report = SummaryReport()
        progress = HandlerProgress(conduit)
        repo_ids = [key['repo_id'] for key in units if key]
        bindings = ParentBinding.fetch(repo_ids)

        strategy_class = find_strategy(constants.ADDITIVE_STRATEGY)
        strategy = strategy_class(progress, report)
        progress.started(bindings)
        strategy.synchronize(bindings, options)

        handler_report = ContentReport()
        if report.succeeded():
            handler_report.set_succeeded(report.dict())
        else:
            handler_report.set_failed(report.dict())
        return handler_report