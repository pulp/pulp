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
from pulp.agent.lib.report import ContentReport
from pulp.citrus.progress import ProgressReport
from pulp.citrus.model import *
from logging import getLogger

log = getLogger(__name__)


class HandlerProgress(ProgressReport):
    """
    Citrus synchronization progress reporting object.
    """

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
        self.conduit.update_progress(self.dict())


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
        @type options: dict
        @return: An update report.
        @rtype: L{ContentReport}
        """
        report = ContentReport()
        progress = HandlerProgress(conduit)
        progress.push_step('fetch_bindings')
        all = options.get('all', False)
        repoids = [key['repo_id'] for key in units if key]
        binding = Binding()
        if all:
            binds = binding.fetch_all()
        else:
            binds = binding.fetch(repoids)
        details, errors = self.synchronize(progress, binds, options)
        progress.set_status(progress.SUCCEEDED)
        report.set_succeeded(details, len(details))
        return report

    def synchronize(self, progress, binds, options):
        """
        Synchronize repositories.
          - Add/Merge bound repositories as needed.
          - Synchronize all bound repositories.
          - Purge unbound repositories.
          - Purge orphaned content units.
        @param progress: A progress report.
        @type progress: L{ProgressReport}
        @param binds: A list of bind payloads.
        @type binds: list
        @param options: Unit update options.
        @type options: dict
        @return: A sync report.
        @rtype: TBD
        """
        errors = []
        added = []
        merged = []
        removed = []

        # add/merge repositories
        try:
            _added, _merged, _failed = self.add_repositories(progress, binds)
            added.extend(_added)
            merged.extend(_merged)
            errors.append(_failed)
        except Exception, e:
            msg = str(e)
            errors.append(msg)

        # synchronize repositories
        importer_reports = {}
        progress.push_step('synchronize', len(binds))
        for repo_id in [b['repo_id'] for b in binds]:
            repo = LocalRepository(repo_id)
            try:
                report = repo.run_synchronization(progress)
                importer_reports[repo_id] = dict(succeeded=True, report=report)
            except Exception, e:
                msg = str(e)
                progress.error(msg)
                errors.append((repo_id, msg))
                importer_reports[repo_id] = dict(succeeded=False, exception=msg)

        # purge repositories
        try:
            _removed, _failed = self.delete_repositories(progress, binds)
            removed.extend(_removed)
            errors.append(_failed)
        except Exception, e:
            msg = str(e)
            errors.append(msg)

        # remove orphans
        try:
            progress.push_step('purge_orphans')
            LocalRepository.purge_orphans()
        except Exception, e:
            msg = str(e)
            errors.append(msg)

        report = {
            'errors':errors,
            'merge':{
                'added':added,
                'merged':merged,
                'removed':removed,
            },
            'synchronization': importer_reports,
        }

        progress.set_status(progress.SUCCEEDED)
        return (report, errors)

    def add_repositories(self, progress, binds):
        """
        Add or update repositories.
          - Merge repositories found BOTH upstream and locally.
          - Add repositories found upstream but NOT locally.
        @param progress: A progress report.
        @type progress: L{ProgressReport}
        @param binds: List of bind payloads.
        @type binds: list
        @return: A tuple of: (added, merged, failed).
            added is: repo_id
            merged is: repo_id
            failed is: (repo_id, msg)
        @rtype: tuple
        """
        added = []
        merged = []
        failed = []
        progress.push_step('merge', len(binds))
        for bind in binds:
            try:
                repo_id = bind['repo_id']
                details = bind['details']
                upstream = Repository(repo_id, details)
                myrepo = LocalRepository.fetch(repo_id)
                if myrepo:
                    progress.set_action('merge', repo_id)
                    myrepo.merge(upstream)
                    merged.append(repo_id)
                else:
                    progress.set_action('add', repo_id)
                    myrepo = LocalRepository(repo_id, upstream.details)
                    myrepo.add()
                    added.append(repo_id)
            except Exception, e:
                msg = 'Add/Merge repository: %s failed:%s' % (repo_id, str(e))
                failed.append((repo_id, msg))
        return (added, merged, failed)

    def delete_repositories(self, progress, binds):
        """
        Delete repositories found locally but NOT upstream.
        @param progress: A progress report.
        @type progress: L{ProgressReport}
        @param binds: List of bind payloads.
        @type binds: list
        @return: A tuple of: (removed, failed).
            removed is: repo_id
            failed is: (repo_id, msg)
        @rtype: tuple
        """
        removed = []
        failed = []
        progress.push_step('purge', len(binds))
        upstream = [b['repo_id'] for b in binds]
        downstream = [r.repo_id for r in LocalRepository.fetch_all()]
        for repo_id in downstream:
            try:
                if repo_id not in upstream:
                    progress.set_action('delete', repo_id)
                    repo = LocalRepository(repo_id)
                    repo.delete()
                    removed.append(repo_id)
            except Exception, e:
                msg = 'Delete repository %s failed: %s' % (repo_id, str(e))
                failed.append((repo_id, msg))
        return (removed, failed)