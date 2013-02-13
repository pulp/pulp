# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.


from gettext import gettext as _
from logging import getLogger

from pulp_citrus.handler.model import *
from pulp_citrus.progress import ProgressReport
from pulp_citrus.handler.reports import HandlerReport


log = getLogger(__name__)


# --- abstract strategy -----------------------------------------------------------------


class HandlerStrategy(object):
    """
    Provides strategies for synchronizing repositories between pulp servers.
    :ivar cancelled: The flag indicating that the current operation
        has been cancelled.
    :type cancelled: bool
    :var progress: A progress report.
    :type progress: HandlerReport
    """

    def __init__(self, progress):
        """
        :param progress: A progress reporting object.
        :type progress: ProgressReport
        """
        self.cancelled = False
        self.progress = progress

    def synchronize(self, bindings, options):
        """
        Synchronize local repositories based on bindings.
        Must be overridden by subclasses.
        :param bindings: A list of consumer binding payloads.
        :type bindings: list
        :param options: synchronization options.
        :type options: dict
        :return: The synchronization report.
        """
        raise NotImplementedError()

    def cancel(self):
        """
        Cancel the current operation.
        """
        self.cancelled = True

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
            if self.cancelled:
                break
            try:
                repo_id = bind['repo_id']
                details = bind['details']
                upstream = Repository(repo_id, details)
                local = LocalRepository.fetch(repo_id)
                if local:
                    self.progress.set_action('merge', repo_id)
                    local.merge(upstream)
                    merged.append(repo_id)
                else:
                    self.progress.set_action('add', repo_id)
                    local = LocalRepository(repo_id, upstream.details)
                    local.add()
                    added.append(repo_id)
            except Exception, e:
                msg = _('Add/Merge repository: %(r)s failed: %(e)s')
                failed.append((repo_id, msg % {'r':repo_id, 'e':repr(e)}))
        return (added, merged, failed)

    def _synchronize_repositories(self, repo_ids, options):
        """
        Run synchronization on repositories.
        :param repo_ids: A list of repo IDs.
        :type repo_ids: list
        :param options: Unit update options.
        :type options: dict
        :return: A tuple of: (reports, errors)
          - reports: A list of repo sync reports.
          - errors: A list of (repo_id, error_message)
        """
        errors = []
        reports = {}
        self.progress.push_step('synchronize', len(repo_ids))
        for repo_id in repo_ids:
            if self.cancelled:
                break
            repo = LocalRepository(repo_id)
            try:
                strategy = options.get('strategy')
                report = repo.run_synchronization(self.progress, strategy)
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
        local = [r.repo_id for r in LocalRepository.fetch_all()]
        for repo_id in local:
            if self.cancelled:
                break
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


# --- strategies ------------------------------------------------------------------------


class Mirror(HandlerStrategy):

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
        :return: A report
        :rtype: Report
        """
        report = HandlerReport()
        merge_report = report.merge_report
        importer_reports = report.importer_reports

        # add/merge repositories
        try:
            added, merged, failed = self._add_repositories(bindings)
            merge_report.added.extend(added)
            merge_report.merged.extend(merged)
            report.errors.extend(failed)
        except Exception, e:
            msg = repr(e)
            report.errors.append(msg)

        # synchronize repositories
        try:
            repo_ids = merge_report.added + merge_report.merged
            reports, _errors = self._synchronize_repositories(repo_ids, options)
            importer_reports.update(reports)
            report.errors.extend(_errors)
        except Exception, e:
            msg = repr(e)
            report.errors.append(msg)

        # delete repositories
        try:
            removed, failed = self._delete_repositories(bindings)
            merge_report.removed.extend(removed)
            report.errors.extend(failed)
        except Exception, e:
            msg = repr(e)
            report.errors.append(msg)

        # remove orphans
        if options.get('purge_orphans'):
            try:
                self.progress.push_step('purge_orphans')
                LocalRepository.purge_orphans()
            except Exception, e:
                msg = repr(e)
                report.errors.append(msg)

        self.progress.set_status(ProgressReport.SUCCEEDED)
        return report


class Additive(HandlerStrategy):

    def synchronize(self, bindings, options):
        """
        Synchronize repositories.
          - Add/Merge bound repositories as needed.
          - Synchronize all bound repositories.
        :param bindings: A list of bind payloads.
        :type bindings: list
        :param options: Unit update options.
        :type options: dict
        :return: A report
        :rtype: Report
        """
        report = HandlerReport()
        merge_report = report.merge_report
        importer_reports = report.importer_reports

        # add/merge repositories
        try:
            added, merged, failed = self._add_repositories(bindings)
            merge_report.added.extend(added)
            merge_report.merged.extend(merged)
            report.errors.extend(failed)
        except Exception, e:
            msg = repr(e)
            report.errors.append(msg)

        # synchronize repositories
        try:
            repo_ids = merge_report.added + merge_report.merged
            reports, _errors = self._synchronize_repositories(repo_ids, options)
            importer_reports.update(reports)
            report.errors.extend(_errors)
        except Exception, e:
            msg = repr(e)
            report.errors.append(msg)

        self.progress.set_status(ProgressReport.SUCCEEDED)
        return report


# --- factory ---------------------------------------------------------------------------


STRATEGIES = {
    'mirror' : Mirror,
    'additive' : Additive,
}


class StrategyUnsupported(Exception):

    def __init__(self, name):
        msg = _('handler strategy "%(s)s" not supported')
        Exception.__init__(self, msg % {'s':name})


def find_strategy(name):
    """
    Find a strategy (class) by name.
    :param name: A strategy name.
    :type name: str
    :return: A strategy class.
    :rtype: HandlerStrategy
    :raise: StrategyUnsupported on not found.
    """
    try:
        return STRATEGIES[name]
    except KeyError:
        raise StrategyUnsupported(name)