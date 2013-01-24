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

from gettext import gettext as _
from pulp.agent.lib.handler import ContentHandler
from pulp.agent.lib.report import ContentReport
from pulp.citrus.progress import ProgressReport
from pulp.citrus.model import *
from logging import getLogger

log = getLogger(__name__)


class Progress(ProgressReport):
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


class CitrusHandler(ContentHandler):

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
        progress = Progress(conduit)
        progress.push_step('fetch_bindings')
        all = options.get('all', False)
        repo_ids = [key['repo_id'] for key in units if key]
        if all:
            binds = RemoteBinding.fetch_all()
        else:
            binds = RemoteBinding.fetch(repo_ids)
        details, errors = self.synchronize(progress, binds, options)
        progress.end()
        if errors:
            report.set_failed(details)
        else:
            report.set_succeeded(details)
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
        @return: A result of: (report, errors)
          - report: TBD
          - errors: A list of: (repo_id, error)
        @rtype: tuple(2)
        """
        errors = []
        added = []
        merged = []
        removed = []

        strategy = options.get('strategy', 'mirror')

        # add/merge repositories
        try:
            _added, _merged, _failed = self.add_repositories(progress, binds)
            added.extend(_added)
            merged.extend(_merged)
            errors.extend(_failed)
        except Exception, e:
            msg = repr(e)
            errors.append(msg)

        # synchronize repositories
        importer_reports = {}
        try:
            repo_ids = added + merged
            reports, _errors = self.synchronize_repositories(repo_ids, progress)
            importer_reports.update(reports)
            errors.extend(_errors)
        except Exception, e:
            msg = repr(e)
            errors.append(msg)

        # delete repositories
        try:
            _removed, _failed = self.delete_repositories(progress, binds)
            removed.extend(_removed)
            errors.extend(_failed)
        except Exception, e:
            msg = repr(e)
            errors.append(msg)

        # remove orphans
        try:
            progress.push_step('purge_orphans')
            LocalRepository.purge_orphans()
        except Exception, e:
            msg = repr(e)
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
            failed is: (repo_id, error_message)
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
                msg = _('Add/Merge repository: %(r)s failed: %(e)s')
                failed.append((repo_id, msg % {'r':repo_id, 'e':repr(e)}))
        return (added, merged, failed)

    def synchronize_repositories(self, repo_ids, progress):
        """
        Run synchronization on repositories.
        @param repo_ids: A list of repo IDs.
        @type repo_ids: list
        @param progress: A progress report.
        @type progress: L{ProgressReport}
        @return: A tuple of: (reports, errors)
          - reports: A list of repo sync reports.
          - errors: A list of (repo_id, error_message)
        """
        errors = []
        reports = {}
        progress.push_step('synchronize', len(repo_ids))
        for repo_id in repo_ids:
            repo = LocalRepository(repo_id)
            try:
                report = repo.run_synchronization(progress)
                details = report['details']
                _report = details.get('report')
                exception = details.get('exception')
                if _report:
                    if not _report['succeeded']:
                        msg = _('synchronization failed on repository: %(r)s')
                        errors.append((repo_id, msg % {'r':repo_id}))
                        progress.set_status(progress.FAILED)
                    else:
                        progress.set_status(progress.SUCCEEDED)
                    reports[repo_id] = report
                    continue
                if exception:
                    msg = _('repository: %(r)s error: %(e)s')
                    errors.append((repo_id, msg % {'r':repo_id, 'e':exception}))
                    progress.set_status(progress.FAILED)
                    continue
                progress.set_status(progress.FAILED)
                msg = _('unexpected result for repository: %(r)s')
                raise Exception(msg % {'r':repo_id})
            except Exception, e:
                msg = repr(e)
                progress.error(msg)
                errors.append((repo_id, msg))
                reports[repo_id] = dict(succeeded=False, exception=msg)
        return (reports, errors)

    def delete_repositories(self, progress, binds):
        """
        Delete repositories found locally but NOT upstream.
        @param progress: A progress report.
        @type progress: L{ProgressReport}
        @param binds: List of bind payloads.
        @type binds: list
        @return: A tuple of: (removed, failed).
            removed is: repo_id
            failed is: (repo_id, error_message)
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
                msg = _('Delete repository: %(r)s failed: %(e)s')
                failed.append((repo_id, msg % {'r':repo_id, 'e':repr(e)}))
        return (removed, failed)