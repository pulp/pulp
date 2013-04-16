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
from operator import itemgetter

from pulp_node import constants
from pulp_node.handlers.model import *
from pulp_node.handlers.validation import Validator
from pulp_node.error import NodeError, CaughtException
from pulp_node.handlers.reports import SummaryReport, HandlerProgress, RepositoryReport


log = getLogger(__name__)


# --- i18n ------------------------------------------------------------------------------

STRATEGY_UNSUPPORTED = _('Handler strategy "%(s)s" not supported')


# --- abstract strategy -----------------------------------------------------------------


class HandlerStrategy(object):
    """
    Provides strategies for synchronizing repositories between pulp servers.
    :ivar cancelled: The flag indicating that the current operation
        has been cancelled.
    :type cancelled: bool
    :ivar progress_report: A progress report.
    :type progress_report: HandlerProgress
    :ivar summary_report: The summary report.
    :type summary_report: SummaryReport
    """

    def __init__(self, progress_report, summary_report):
        """
        :param progress_report: A progress reporting object.
        :type progress_report: HandlerProgress
        :param summary: A summary reporting object.
        :type summary: SummaryReport
        """
        self.cancelled = False
        self.progress_report = progress_report
        self.summary_report = summary_report

    def synchronize(self, bindings, options):
        """
        Synchronize child repositories based on bindings.
        Subclasses must not override this method.
        :param bindings: A list of consumer binding payloads.
        :type bindings: list
        :param options: synchronization options.
        :type options: dict
        """
        bindings.sort(key=itemgetter('repo_id'))

        self.summary_report.setup(bindings)
        self.progress_report.started(bindings)

        try:
            # validation
            validator = Validator(self.summary_report)
            validator.validate(bindings)
            if self.summary_report.failed():
                return

            # synchronization implemented by subclasses
            self._synchronize(bindings)

            # purge orphans
            if options.get(constants.PURGE_ORPHANS_KEYWORD):
                ChildRepository.purge_orphans()
        except NodeError, ne:
            self.summary_report.errors.append(ne)
        except Exception, e:
            log.exception('synchronization failed')
            error = CaughtException(e)
            self.summary_report.errors.append(error)
        finally:
            self.progress_report.finished()

    def _synchronize(self, bindings):
        """
        Specific strategies defined by subclasses.
        :param bindings: A list of consumer binding payloads.
        :type bindings: list
        """
        raise NotImplementedError()

    def cancel(self):
        """
        Cancel the current operation.
        """
        self.cancelled = True

    # --- protected ---------------------------------------------------------------------

    def _merge_repositories(self, bindings):
        """
        Add or update repositories based on bindings.
          - Merge repositories found in BOTH parent and child.
          - Add repositories found in the parent but NOT in the child.
        :param bindings: List of bind payloads.
        :type bindings: list
        """
        for bind in bindings:
            if self.cancelled:
                break
            try:
                repo_id = bind['repo_id']
                details = bind['details']
                parent = Repository(repo_id, details)
                child = ChildRepository.fetch(repo_id)
                progress = self.progress_report.find_report(repo_id)
                progress.begin_merging()
                if child:
                    self.summary_report[repo_id].action = RepositoryReport.MERGED
                    child.merge(parent)
                else:
                    child = ChildRepository(repo_id, parent.details)
                    self.summary_report[repo_id].action = RepositoryReport.ADDED
                    child.add()
                self._synchronize_repository(repo_id)
            except NodeError, ne:
                self.summary_report.errors.append(ne)
            except Exception, e:
                log.exception(repo_id)
                error = CaughtException(e, repo_id)
                self.summary_report.errors.append(error)

    def _synchronize_repository(self, repo_id):
        """
        Run synchronization on a repository by ID.
        :param repo_id: A repository ID.
        :type repo_id: str
        """
        repo = ChildRepository(repo_id)
        progress = self.progress_report.find_report(repo_id)
        importer_report = repo.run_synchronization(progress)
        progress.finished()
        details = importer_report['details']
        for _dict in details['errors']:
            e = NodeError(None)
            e.load(_dict)
            self.summary_report.errors.append(e)
        _report = self.summary_report[repo_id]
        _report.units.added = importer_report['added_count']
        _report.units.updated = importer_report['updated_count']
        _report.units.removed = importer_report['removed_count']

    def _delete_repositories(self, bindings):
        """
        Delete repositories found in the child but NOT in the parent.
        :param bindings: List of bind payloads.
        :type bindings: list
        """
        repositories_on_parent = [b['repo_id'] for b in bindings]
        repositories_on_child = [r.repo_id for r in ChildRepository.fetch_all()]
        for repo_id in sorted(repositories_on_child):
            if self.cancelled:
                break
            try:
                if repo_id not in repositories_on_parent:
                    self.summary_report[repo_id] = RepositoryReport(repo_id, RepositoryReport.DELETED)
                    repo = ChildRepository(repo_id)
                    repo.delete()
            except NodeError, ne:
                self.summary_report.errors.append(ne)
            except Exception, e:
                log.exception(repo_id)
                error = CaughtException(e, repo_id)
                self.summary_report.errors.append(error)


# --- strategies ------------------------------------------------------------------------


class Mirror(HandlerStrategy):

    def _synchronize(self, bindings):
        """
        Synchronize repositories.
          - Add/Merge bound repositories as needed.
          - Synchronize all bound repositories.
          - Purge unbound repositories.
          - Purge orphaned content units.
        :param bindings: A list of bind payloads.
        :type bindings: list
        """
        self._merge_repositories(bindings)
        self._delete_repositories(bindings)


class Additive(HandlerStrategy):

    def _synchronize(self, bindings):
        """
        Synchronize repositories.
          - Add/Merge bound repositories as needed.
          - Synchronize all bound repositories.
        :param bindings: A list of bind payloads.
        :type bindings: list
        """
        self._merge_repositories(bindings)


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