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


import httplib

from pulp.agent.lib.handler import ContentHandler
from pulp.agent.lib.report import ContentReport
from pulp.citrus.progress import ProgressReport
from pulp.citrus.model import *
from logging import getLogger

log = getLogger(__name__)


class HandlerProgress(ProgressReport):
    """
    Citrus synchronization progress reporting object.
    """

    PENDING = None
    SUCCEEDED = True
    FAILED = False

    def __init__(self, conduit):
        """
        Constructor.
        """
        self.conduit = conduit
        ProgressReport.__init__(self)

    def _updated(self):
        """
        Notification that the report has been updated.
        Designed to be overridden and reported.
        """
        ProgressReport._updated(self)
        self.conduit.update_progress(self)


class RepositoryHandler(ContentHandler):

    def update(self, conduit, units, options):
        """
        Update content unit(s).
        Unit key of {} or None indicates updates update all
        but only if (all) option is True.
        @param conduit: A handler conduit.
        @type conduit: L{pulp.agent.lib.conduit.Conduit}
        @param units: A list of content unit_keys.
        @type units: list
        @param options: Unit update options.
          - apply : apply the transaction
          - importkeys : import GPG keys
          - reboot : Reboot after installed
        @type options: dict
        @return: An update report.
        @rtype: L{ContentReport}
        """
        report = ContentReport()
        progress = HandlerProgress(conduit)
        progress.push_step('fetch')
        all = options.get('all', False)
        repoids = [key['repo_id'] for key in units if key]
        if all:
            binds = self.all_binds()
        else:
            binds = self.binds(repoids)
        details = self.synchronize(progress, binds)
        progress.set_status(progress.SUCCEEDED)
        report.set_succeeded(details, len(details))
        return report

    def all_binds(self):
        """
        Get a list of ALL bind payloads for this consumer.
        @return: List of bind payloads.
        @rtype: list
        """
        binding = Binding()
        return binding.fetch_all()

    def binds(self, repoids):
        """
        Get a list of bind payloads for the specified list of repository ID.
        @param repoids: A list of repository IDs.
        @type repoids:  list
        @return: List of bind payloads.
        @rtype: list
        """
        binding = Binding()
        return binding.fetch(repoids)

    def filtered(self, binds):
        """
        Get a filtered list of binds.
          - Includes only the (pulp) distributor.
        @param binds: A list of bind payloads.
        @type binds: list
        @return: The filtered list of bind payloads.
        @rtype: list
        """
        return [b for b in binds if b['type_id'] == CITRUS_DISTRIBUTOR]

    def synchronize(self, progress, binds):
        """
        Synchronize repositories.
        @param progress: A progress report.
        @type progress: L{ProgressReport}
        @param binds: A list of bind payloads.
        @type binds: list
        @return: A sync report.
        @rtype: TBD
        """
        report = {}
        self.merge(progress, binds)
        progress.push_step('synchronize')
        for repo_id in [b['repo_id'] for b in binds]:
            progress.set_action('synchronize', repo_id)
            repo = LocalRepository(repo_id)
            repo.run_sync(progress)
        progress.set_status(progress.SUCCEEDED)
        return report

    def merge(self, progress, binds):
        """
        Merge repositories.
          - Delete repositories found locally but not upstream.
          - Merge repositories found BOTH upstream and locally.
          - Add repositories found upstream but NOT locally.
        @param progress: A progress report.
        @type progress: L{ProgressReport}
        @param binds: List of bind payloads.
        @type binds: list
        """
        self.purge(progress, binds)
        progress.push_step('merge')
        for bind in binds:
            try:
                repo_id = bind['repo_id']
                details = bind['details']
                upstream = Repository(repo_id, details)
                myrepo = LocalRepository.fetch(repo_id)
                if myrepo:
                    progress.set_action('merge', repo_id)
                    myrepo.merge(upstream)
                else:
                    progress.set_action('add', repo_id)
                    myrepo = LocalRepository(repo_id, upstream.details)
                    myrepo.add()
            except Exception, e:
                log.exception(str(bind))

    def purge(self, progress, binds):
        """
        Purge repositories found locally but NOT upstream.
        @param progress: A progress report.
        @type progress: L{ProgressReport}
        @param binds: List of bind payloads.
        @type binds: list
        """
        try:
            progress.push_step('purge')
            upstream = [b['repo_id'] for b in binds]
            downstream = [r.repo_id for r in LocalRepository.fetch_all()]
            for repo_id in downstream:
                if repo_id not in upstream:
                    progress.set_action('delete', repo_id)
                    repo = LocalRepository(repo_id)
                    repo.delete()
        except Exception, e:
            return e