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

from logging import getLogger

from pulp.agent.lib.handler import ContentHandler
from pulp.agent.lib.report import ContentReport
from pulp.citrus.handler import Mirror
from pulp.citrus.model import RemoteBinding
from pulp.citrus.progress import ProgressReport


log = getLogger(__name__)


class CitrusHandler(ContentHandler):

    def update(self, conduit, units, options):
        """
        Update the specified content units.  In citrus, the update of a
        'repository' unit triggers repository synchronization.  The definition
        of what synchronization means, depends on the strategy option passed.
        The synchronization itself, is delegated to the strategy object.
        Unit key of {} or None indicates updates update all but only if
        (all) option is True.
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
        progress = Progress(conduit)
        progress.push_step('fetch_bindings')
        all = options.get('all', False)
        repo_ids = [key['repo_id'] for key in units if key]
        if all:
            bindings = RemoteBinding.fetch_all()
        else:
            bindings = RemoteBinding.fetch(repo_ids)
        strategy = Mirror(progress)
        strategy_report = strategy.synchronize(bindings, options)
        progress.end()
        details = strategy_report.dict()
        if strategy_report.errors:
            report.set_failed(details)
        else:
            report.set_succeeded(details)
        return report


# --- supporting objects ----------------------------------------------------------------

class Progress(ProgressReport):
    """
    Citrus synchronization progress reporting object.
    """

    def __init__(self, conduit):
        """
        :param conduit: A handler conduit.
        :type conduit: pulp.agent.lib.conduit.Conduit
        """
        self.conduit = conduit
        ProgressReport.__init__(self)

    def _updated(self):
        """
        Notification that the report has been updated.
        Reported using the conduit.
        """
        ProgressReport._updated(self)
        self.conduit.update_progress(self.dict())