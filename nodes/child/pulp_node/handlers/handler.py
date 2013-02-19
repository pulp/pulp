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

from pulp_node.handlers.strategies import find_strategy
from pulp_node.handlers.reports import HandlerProgress
from pulp_node.handlers.model import ParentBinding


log = getLogger(__name__)


class NodeHandler(ContentHandler):

    def update(self, conduit, units, options):
        """
        Update the specified content units.  Each unit must be of
        type 'node'.  Updates the entire child node.
        :param conduit: A handler conduit.
        :type conduit: pulp.agent.lib.conduit.Conduit
        :param units: A list of content unit_keys.
        :type units: list
        :param options: Unit update options.
        :type options: dict
        :return: An update report.
        :rtype: ContentReport
        """
        report = ContentReport()
        progress = HandlerProgress(conduit)
        progress.push_step('fetch_bindings')
        bindings = ParentBinding.fetch_all()

        strategy_name = options.setdefault('strategy', 'mirror')
        strategy_class = find_strategy(strategy_name)
        strategy = strategy_class(progress)
        strategy_report = strategy.synchronize(bindings, options)

        progress.end()
        details = strategy_report.dict()
        if strategy_report.errors:
            report.set_failed(details)
        else:
            report.set_succeeded(details)
        return report


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
        report = ContentReport()
        progress = HandlerProgress(conduit)
        progress.push_step('fetch_bindings')
        repo_ids = [key['repo_id'] for key in units if key]
        bindings = ParentBinding.fetch(repo_ids)

        strategy_class = find_strategy('additive')
        strategy = strategy_class(progress)
        strategy_report = strategy.synchronize(bindings, options)

        progress.end()
        details = strategy_report.dict()
        if strategy_report.errors:
            report.set_failed(details)
        else:
            report.set_succeeded(details)
        return report