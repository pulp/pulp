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


# --- request  --------------------------------------------------------------------------


class Request(object):
    """
    Represents a specific request to synchronize a child node.
    It contains the resources needed by the strategy to complete the request
    and maintains the state of the request.
    :ivar conduit: A handler conduit.
    :type conduit: pulp.agent.lib.conduit.Conduit
    :ivar progress: A progress report.
    :type progress: HandlerProgress
    :ivar summary: The summary report.
    :type summary: SummaryReport
    :ivar bindings: A list of consumer binding payloads.
    :type bindings: list
    :ivar scope: Specifies the scope of the request (node|repository).
    :type scope: str
    :ivar options: synchronization options.
    :type options: dict
    """

    def __init__(self, conduit, progress, summary, bindings, scope, options):
        """
        :param conduit: A handler conduit.
        :type conduit: pulp.agent.lib.conduit.Conduit
        :param progress: A progress report.
        :type progress: HandlerProgress
        :param summary: The summary report.
        :type summary: SummaryReport
        :param bindings: A list of consumer binding payloads.
        :type bindings: list
        :param scope: The request scope (node|repository)
        :type scope: str
        :param options: synchronization options.
        :type options: dict
        """
        self.conduit = conduit
        self.progress = progress
        self.summary = summary
        self.bindings = sorted(bindings, key=itemgetter('repo_id'))
        self.scope = scope
        self.options = options
        summary.setup(self.bindings)

    def cancelled(self):
        """
        Get whether the request has been cancelled.
        :return: True if cancelled.
        :rtype: bool
        """
        return self.conduit.cancelled()

    def started(self):
        """
        Processing of the request has started.
        """
        self.progress.started(self.bindings)

    def finished(self):
        """
        Processing of the request has finished.
        """
        self.progress.finished()


# --- abstract strategy -----------------------------------------------------------------


class HandlerStrategy(object):
    """
    Provides strategies for synchronizing repositories between pulp servers.
    """

    def synchronize(self, request):
        """
        Synchronize child repositories based on bindings.
        Subclasses must not override this method.
        """
        request.started()

        try:
            # validation
            validator = Validator(request.summary)
            validator.validate(request.bindings)
            if request.summary.failed():
                return

            # synchronization implemented by subclasses
            self._synchronize(request)

            # purge orphans
            if request.options.get(constants.PURGE_ORPHANS_KEYWORD):
                Repository.purge_orphans()
        except NodeError, ne:
            request.summary.errors.append(ne)
        except Exception, e:
            log.exception('synchronization failed')
            error = CaughtException(e)
            request.summary.errors.append(error)
        finally:
            request.finished()

    def _synchronize(self, request):
        """
        Specific strategies defined by subclasses.
        :param request: A synchronization request.
        :type request: SyncRequest
        """
        raise NotImplementedError()

    # --- protected ---------------------------------------------------------------------

    def _merge_repositories(self, request):
        """
        Add or update repositories based on bindings.
          - Merge repositories found in BOTH parent and child.
          - Add repositories found in the parent but NOT in the child.
        :param request: A synchronization request.
        :type request: SyncRequest
        """
        for bind in request.bindings:
            try:
                repo_id = bind['repo_id']
                details = bind['details']
                if request.cancelled():
                    request.summary[repo_id].action = RepositoryReport.CANCELLED
                    continue
                parent = Repository(repo_id, details)
                child = Repository.fetch(repo_id)
                progress = request.progress.find_report(repo_id)
                progress.begin_merging()
                if child:
                    request.summary[repo_id].action = RepositoryReport.MERGED
                    child.merge(parent)
                else:
                    child = Repository(repo_id, parent.details)
                    request.summary[repo_id].action = RepositoryReport.ADDED
                    child.add()
                self._synchronize_repository(request, repo_id)
            except NodeError, ne:
                request.summary.errors.append(ne)
            except Exception, e:
                log.exception(repo_id)
                error = CaughtException(e, repo_id)
                request.summary.errors.append(error)

    def _synchronize_repository(self, request, repo_id):
        """
        Run synchronization on a repository by ID.
        :param request: A synchronization request.
        :type request: SyncRequest
        :param repo_id: A repository ID.
        :type repo_id: str
        """
        progress = request.progress.find_report(repo_id)
        skip = request.options.get(constants.SKIP_CONTENT_UPDATE_KEYWORD, False)
        if skip:
            progress.finished()
            return
        repo = Repository(repo_id)
        importer_report = repo.run_synchronization(progress, request.cancelled, request.options)
        if request.cancelled():
            request.summary[repo_id].action = RepositoryReport.CANCELLED
            return
        progress.finished()
        details = importer_report['details']
        for _dict in details['errors']:
            ne = NodeError(None)
            ne.load(_dict)
            request.summary.errors.append(ne)
        _report = request.summary[repo_id]
        _report.units.added = importer_report['added_count']
        _report.units.updated = importer_report['updated_count']
        _report.units.removed = importer_report['removed_count']
        _report.sources = details['sources']

    def _delete_repositories(self, request):
        """
        Delete repositories found in the child but NOT in the parent.
        :param request: A synchronization request.
        :type request: SyncRequest
        """
        repositories_on_parent = [b['repo_id'] for b in request.bindings]
        repositories_on_child = [r.repo_id for r in Repository.fetch_all()]
        for repo_id in sorted(repositories_on_child):
            if request.cancelled():
                request.summary[repo_id] = RepositoryReport(repo_id, RepositoryReport.CANCELLED)
                continue
            try:
                if repo_id not in repositories_on_parent:
                    request.summary[repo_id] = RepositoryReport(repo_id, RepositoryReport.DELETED)
                    repo = Repository(repo_id)
                    repo.delete()
            except NodeError, ne:
                request.summary.errors.append(ne)
            except Exception, e:
                log.exception(repo_id)
                error = CaughtException(e, repo_id)
                request.summary.errors.append(error)


# --- strategies ------------------------------------------------------------------------


class Mirror(HandlerStrategy):

    def _synchronize(self, request):
        """
        Synchronize repositories.
          - Add/Merge bound repositories as needed.
          - Synchronize all bound repositories.
          - Purge unbound repositories (scope=node only).
        :param request: A synchronization request.
        :type request: SyncRequest
        """
        self._merge_repositories(request)
        if request.scope == constants.NODE_SCOPE:
            self._delete_repositories(request)


class Additive(HandlerStrategy):

    def _synchronize(self, request):
        """
        Synchronize repositories.
          - Add/Merge bound repositories as needed.
          - Synchronize all bound repositories.
        :param request: A synchronization request.
        :type request: SyncRequest
        """
        self._merge_repositories(request)


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