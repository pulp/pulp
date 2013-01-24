# Copyright (c) 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""
Provides classes that implement repository synchronization strategies.
The citrus handler delegates the synchronization to one of
the strategies provided here.
"""

from gettext import gettext as _
from logging import getLogger

from pulp.citrus.model import *
from pulp.citrus.progress import ProgressReport



log = getLogger(__name__)


class Strategy:

    def __init__(self, progress):
        """
        Repository synchronization strategy.
        :param progress: A progress reporting object.
        :type progress: ProgressReport
        """
        self.progress = progress

    def synchronize(self, bindings, options):
        """
        Synchronize local repositories based on bindings.
        :param bindings: A list of consumer binding payloads.
        :type bindings: list
        :param options: synchronization options.
        :type options: dict
        :return: The synchronization report.
        """
        raise NotImplementedError()

    # --- protected ---------------------------------------------------------------------

    def _add_repositories(self, bindings):
        """
        Add or update repositories based on bindings.
          - Merge repositories found BOTH upstream and locally.
          - Add repositories found upstream but NOT locally.
        :param bindings: List of bind payloads.
        :type bindings: list
        :return: A tuple of: (added, merged, failed).
            added is: repo_id
            merged is: repo_id
            failed is: (repo_id, error_message)
        :rtype: tuple
        """
        added = []
        merged = []
        failed = []
        self.progress.push_step('merge', len(bindings))
        for bind in bindings:
            try:
                repo_id = bind['repo_id']
                details = bind['details']
                upstream = Repository(repo_id, details)
                myrepo = LocalRepository.fetch(repo_id)
                if myrepo:
                    self.progress.set_action('merge', repo_id)
                    myrepo.merge(upstream)
                    merged.append(repo_id)
                else:
                    self.progress.set_action('add', repo_id)
                    myrepo = LocalRepository(repo_id, upstream.details)
                    myrepo.add()
                    added.append(repo_id)
            except Exception, e:
                msg = _('Add/Merge repository: %(r)s failed: %(e)s')
                failed.append((repo_id, msg % {'r':repo_id, 'e':repr(e)}))
        return (added, merged, failed)

    def _synchronize_repositories(self, repo_ids):
        """
        Run synchronization on repositories.
        :param repo_ids: A list of repo IDs.
        :type repo_ids: list
        :return: A tuple of: (reports, errors)
          - reports: A list of repo sync reports.
          - errors: A list of (repo_id, error_message)
        """
        errors = []
        reports = {}
        self.progress.push_step('synchronize', len(repo_ids))
        for repo_id in repo_ids:
            repo = LocalRepository(repo_id)
            try:
                report = repo.run_synchronization(self.progress)
                details = report['details']
                _report = details.get('report')
                exception = details.get('exception')
                if _report:
                    if not _report['succeeded']:
                        msg = _('synchronization failed on repository: %(r)s')
                        errors.append((repo_id, msg % {'r':repo_id}))
                        self.progress.set_status(ProgressReport.FAILED)
                    else:
                        self.progress.set_status(ProgressReport.SUCCEEDED)
                    reports[repo_id] = report
                    continue
                if exception:
                    msg = _('repository: %(r)s error: %(e)s')
                    errors.append((repo_id, msg % {'r':repo_id, 'e':exception}))
                    self.progress.set_status(ProgressReport.FAILED)
                    continue
                self.progress.set_status(ProgressReport.FAILED)
                msg = _('unexpected result for repository: %(r)s')
                raise Exception(msg % {'r':repo_id})
            except Exception, e:
                msg = repr(e)
                self.progress.error(msg)
                errors.append((repo_id, msg))
                reports[repo_id] = dict(succeeded=False, exception=msg)
        return (reports, errors)

    def _delete_repositories(self, bindings):
        """
        Delete repositories found locally but NOT upstream.
        :param bindings: List of bind payloads.
        :type bindings: list
        :return: A tuple of: (removed, failed).
            removed is: repo_id
            failed is: (repo_id, error_message)
        :rtype: tuple
        """
        removed = []
        failed = []
        self.progress.push_step('purge', len(bindings))
        upstream = [b['repo_id'] for b in bindings]
        downstream = [r.repo_id for r in LocalRepository.fetch_all()]
        for repo_id in downstream:
            try:
                if repo_id not in upstream:
                    self.progress.set_action('delete', repo_id)
                    repo = LocalRepository(repo_id)
                    repo.delete()
                    removed.append(repo_id)
            except Exception, e:
                msg = _('Delete repository: %(r)s failed: %(e)s')
                failed.append((repo_id, msg % {'r':repo_id, 'e':repr(e)}))
        return (removed, failed)


class Mirror(Strategy):

    def synchronize(self, bindings, options):
        """
        Synchronize repositories.
          - Add/Merge bound repositories as needed.
          - Synchronize all bound repositories.
          - Purge unbound repositories.
          - Purge orphaned content units.
        :param bindings: A list of bind payloads.
        :type bindings: list
        :param options: Unit update options.
        :type options: dict
        :return: A result of: (report, errors)
          - report: TBD
          - errors: A list of: (repo_id, error)
        :rtype: tuple(2)
        """
        errors = []
        added = []
        merged = []
        removed = []

        # add/merge repositories
        try:
            _added, _merged, _failed = self._add_repositories(bindings)
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
            reports, _errors = self._synchronize_repositories(repo_ids)
            importer_reports.update(reports)
            errors.extend(_errors)
        except Exception, e:
            msg = repr(e)
            errors.append(msg)

        # delete repositories
        try:
            _removed, _failed = self._delete_repositories(bindings)
            removed.extend(_removed)
            errors.extend(_failed)
        except Exception, e:
            msg = repr(e)
            errors.append(msg)

        # remove orphans
        try:
            self.progress.push_step('purge_orphans')
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

        self.progress.set_status(ProgressReport.SUCCEEDED)
        return (report, errors)

