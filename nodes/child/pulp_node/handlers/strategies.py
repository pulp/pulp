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

from pulp_node import constants
from pulp_node.handlers.model import *
from pulp_node.handlers.reports import HandlerReport, HandlerProgress


log = getLogger(__name__)


# --- i18n ------------------------------------------------------------------------------

ADD_REPOSITORY_FAILED = _('Add/Merge repository: %(r)s failed: %(e)s')
REPOSITORY_SYNC_FAILED = _('Synchronization failed on repository: %(r)s')
REPOSITORY_SYNC_ERROR = _('Repository: %(r)s error: %(e)s')
REPOSITORY_DELETE_FAILED = _('Delete repository: %(r)s failed: %(e)s')
UNEXPECTED_SYNC_RESULT = _('Unexpected result for repository: %(r)s')
STRATEGY_UNSUPPORTED = _('Handler strategy "%(s)s" not supported')


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
        :type progress: HandlerProgress
        """
        self.cancelled = False
        self.progress = progress

    def synchronize(self, bindings, options):
        """
        Synchronize child repositories based on bindings.
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
          - Merge repositories found in BOTH parent and child.
          - Add repositories found in the parent but NOT in the child.
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
        for bind in bindings:
            if self.cancelled:
                break
            try:
                repo_id = bind['repo_id']
                details = bind['details']
                parent = Repository(repo_id, details)
                child = ChildRepository.fetch(repo_id)
                if child:
                    child.merge(parent)
                    merged.append(repo_id)
                else:
                    child = ChildRepository(repo_id, parent.details)
                    child.add()
                    added.append(repo_id)
            except Exception, e:
                msg = ADD_REPOSITORY_FAILED % {'r': repo_id, 'e': repr(e)}
                failed.append((repo_id, msg))
                log.exception(msg)
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
        for repo_id in sorted(repo_ids):
            if self.cancelled:
                break
            repo = ChildRepository(repo_id)
            try:
                progress = self.progress.find_report(repo_id)
                report = repo.run_synchronization(progress)
                progress.finished()
                details = report['details']
                _report = details.get('report')
                exception = details.get('exception')
                if _report:
                    if not _report['succeeded']:
                        msg = REPOSITORY_SYNC_FAILED % {'r': repo_id}
                        errors.append((repo_id, msg))
                    reports[repo_id] = report
                    continue
                if exception:
                    msg = REPOSITORY_SYNC_ERROR % {'r': repo_id, 'e': exception}
                    errors.append((repo_id, msg))
                    continue
                msg = UNEXPECTED_SYNC_RESULT % {'r': repo_id}
                raise Exception(msg)
            except Exception, e:
                msg = repr(e)
                errors.append((repo_id, msg))
                reports[repo_id] = dict(succeeded=False, exception=msg)
                log.exception(msg)
        return (reports, errors)

    def _delete_repositories(self, bindings):
        """
        Delete repositories found in the child but NOT in the parent.
        :param bindings: List of bind payloads.
        :type bindings: list
        :return: A tuple of: (removed, failed).
            removed is: repo_id
            failed is: (repo_id, error_message)
        :rtype: tuple
        """
        removed = []
        failed = []
        parent = [b['repo_id'] for b in bindings]
        child = [r.repo_id for r in ChildRepository.fetch_all()]
        for repo_id in child:
            if self.cancelled:
                break
            try:
                if repo_id not in parent:
                    repo = ChildRepository(repo_id)
                    repo.delete()
                    removed.append(repo_id)
            except Exception, e:
                msg = REPOSITORY_DELETE_FAILED % {'r': repo_id, 'e': repr(e)}
                failed.append((repo_id, msg))
                log.exception(msg)
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

        # delete repositories
        try:
            removed, failed = self._delete_repositories(bindings)
            merge_report.removed.extend(removed)
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

        # remove orphans
        if options.get('purge_orphans'):
            try:
                ChildRepository.purge_orphans()
            except Exception, e:
                msg = repr(e)
                report.errors.append(msg)

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

        # remove orphans
        if options.get('purge_orphans'):
            try:
                ChildRepository.purge_orphans()
            except Exception, e:
                msg = repr(e)
                report.errors.append(msg)

        return report


# --- factory ---------------------------------------------------------------------------


STRATEGIES = {
    constants.MIRROR_STRATEGY: Mirror,
    constants.ADDITIVE_STRATEGY: Additive,
}


class StrategyUnsupported(Exception):

    def __init__(self, name):
        msg = STRATEGY_UNSUPPORTED % {'s': name}
        Exception.__init__(self, msg)


def find_strategy(name):
    """
    Find a strategy (class) by name.
    :param name: A strategy name.
    :type name: str
    :return: A strategy class.
    :rtype: callable
    :raise: StrategyUnsupported on not found.
    """
    try:
        return STRATEGIES[name]
    except KeyError:
        raise StrategyUnsupported(name)