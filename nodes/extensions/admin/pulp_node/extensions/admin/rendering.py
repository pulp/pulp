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
from operator import itemgetter

from pulp.common.constants import PRIMARY_ID

from pulp_node.error import *
from pulp_node.reports import RepositoryProgress, RepositoryReport


# --- constants --------------------------------------------------------------


REPOSITORY_FIELD = _('(%(n)d/%(t)d) Repository: %(id)s')
STEP_FIELD = _('Step: %(s)s')
ADD_UNIT_FIELD = _('(%(n)d/%(t)d) Add unit: %(d)s')

PROGRESS_STATES = {
    RepositoryProgress.PENDING: _('Pending'),
    RepositoryProgress.MERGING: _('Merging Repository'),
    RepositoryProgress.DOWNLOADING_MANIFEST: _('Downloading Manifest'),
    RepositoryProgress.ADDING_UNITS: _('Adding Units'),
    RepositoryProgress.IMPORTING: _('Importing'),
    RepositoryProgress.FINISHED: _('Finished')
}

ACTIONS = {
    RepositoryReport.PENDING: _('Pending'),
    RepositoryReport.CANCELLED: _('Cancelled'),
    RepositoryReport.ADDED: _('Added'),
    RepositoryReport.MERGED: _('Merged'),
    RepositoryReport.DELETED: _('Removed')
}

NODE_ERRORS = {
    CaughtException.ERROR_ID: CaughtException.DESCRIPTION,
    PurgeOrphansError.ERROR_ID: PurgeOrphansError.DESCRIPTION,
    RepoSyncRestError.ERROR_ID: RepoSyncRestError.DESCRIPTION,
    GetBindingsError.ERROR_ID: GetBindingsError.DESCRIPTION,
    GetChildUnitsError.ERROR_ID: GetChildUnitsError.DESCRIPTION,
    GetParentUnitsError.ERROR_ID: GetParentUnitsError.DESCRIPTION,
    ImporterNotInstalled.ERROR_ID: ImporterNotInstalled.DESCRIPTION,
    DistributorNotInstalled.ERROR_ID: DistributorNotInstalled.DESCRIPTION,
    ManifestDownloadError.ERROR_ID: ManifestDownloadError.DESCRIPTION,
    UnitDownloadError.ERROR_ID: UnitDownloadError.DESCRIPTION,
    AddUnitError.ERROR_ID: AddUnitError.DESCRIPTION,
    DeleteUnitError.ERROR_ID: DeleteUnitError.DESCRIPTION,
    InvalidManifestError.ERROR_ID: InvalidManifestError.DESCRIPTION,
}

SYNC_TITLE = _('Child Node Synchronization')
SUCCEEDED_MSG = _('Synchronization succeeded')
FAILED_MSG = _('Error occurred during synchronization, check the child node logs for details')
REPORTED_ERRORS = _('The following [%(n)d] errors were reported')
REPOSITORIES_FAILED = _('The following repositories had errors')

PARENT_NODE = _('Parent Node')

# --- rendering --------------------------------------------------------------


class ProgressTracker:
    """
    Track and render repository progress reports.
    Each report has the following format:
      {repo_id: <str>,
       state: <str>,
       unit_add: {
         total: <int>,
         completed: <int>,
         details: <str>)
       }
    """

    @staticmethod
    def _find(repo_id, reports):
        """
        Find a report by repo_id.
        :param repo_id: A repository ID.
        :type repo_id: str
        :param reports: List of repository progress reports.
        :type reports: list
        :return: The found report or None
        :rtype: dict
        """
        for r in reports:
            if r['repo_id'] == repo_id:
                return r

    @staticmethod
    def _render(report, progress_bar):
        """
        Render the specified report and progress bar.
        :param report: A repository progress report.
        :type report: dict
        :param progress_bar: An okaara progress bar.
        :type progress_bar: okaara.progress.ProgressBar
        """
        state = report['state']
        unit_add = report['unit_add']
        total = unit_add['total']
        completed = unit_add['completed']
        details = unit_add['details'] or ''

        # just display the file part of paths because the directory
        # is not interesting and clutters up the display.

        if '/' in details:
            details = details.rsplit('/', 1)[1]

        # message part of the progress bar

        if state == RepositoryProgress.ADDING_UNITS:
            message = '\n'.join(
                (STEP_FIELD % {'s': PROGRESS_STATES[state]},
                 ADD_UNIT_FIELD % {'n': completed, 't': total, 'd': details}))
        else:
            message = None

        # prevent divide by zero and make sure the progress bar and
        # make sure the progress bar shows complete when the report is finished.

        if total < 1:
            if state == RepositoryProgress.FINISHED:
                progress_bar.render(1, 1)
            else:
                progress_bar.render(0.01, 1)
        else:
            progress_bar.render(completed, total, message)

        return progress_bar

    def __init__(self, prompt):
        """
        :param prompt: An okaara prompt.
        :type prompt: okaara.prompt.Prompt
        """
        self.prompt = prompt
        self.snapshot = []

    def display(self, report):
        """
        Display the specified progress report.
        :param report: A serialized pulp_node.reports.RepositoryProgress.
        :type report: dict
        """
        if report is None:
            # nothing to render
            return
        reports = report.get('progress')
        if reports is None:
            # nothing to render
            return

        # On the 2nd+ report, update the last in-progress report.

        if self.snapshot:
            report, progress_bar = self.snapshot[-1]
            repo_id = report['repo_id']
            report = self._find(repo_id, reports)
            self._render(report, progress_bar)

        # The latency in polling can causes gaps in the reported progress.
        # This includes the gap between never having processed a report and receiving
        # the 1st report.  Here, we get caught up in all cases.

        in_progress = [r for r in reports if r['state'] != RepositoryProgress.PENDING]
        for i in range(len(self.snapshot), len(in_progress)):
            r = in_progress[i]
            progress_bar = self.prompt.create_progress_bar()
            self.snapshot.append((r, progress_bar))
            repo_id = r['repo_id']
            self.prompt.write('\n')
            self.prompt.write(REPOSITORY_FIELD % {'n': i + 1, 't': len(reports), 'id': repo_id})
            self._render(r, progress_bar)


class UpdateRenderer(object):
    """
    Render the node synchronization summary with the following format:
      succeeded: <bool>
      details: {
        errors: [
          { error_id: <str>,
            details: {}
          },
        ]
        repositories: [
          { repo_id: <str>,
            action: <str>,
            units: {
              added: <int>,
              updated: <int>,
              removed: <int>
            }
          },
        ]
      }
    """

    def __init__(self, prompt, report):
        self.prompt = prompt
        self.succeeded = report['succeeded']
        self.details = report['details']
        self.errors = self.details.get('errors', [])
        self.message = self.details.get('message')
        self.repositories = self.details.get('repositories', {})

    def render(self):
        if self.message:
            # An unexpected exception has been reported
            self.prompt.render_failure_message(self.message)
            self.prompt.render_failure_message(FAILED_MSG)
            return

        documents = []
        for repo_report in sorted(self.repositories, key=itemgetter('repo_id')):
            sources = repo_report['sources']
            downloads = sources.get('downloads', {})
            for source_id, stat in downloads.items():
                if source_id == PRIMARY_ID:
                    source_id = PARENT_NODE
                stat['source_id'] = source_id
            sources['downloads'] = downloads.values()
            document = {
                'repository': {
                    'id': repo_report['repo_id'],
                    'action': ACTIONS[repo_report['action']],
                    'units': repo_report['units'],
                    'content_sources': sources
                },
            }
            documents.append(document)

        self.prompt.write('\n\n')

        if self.succeeded:
            self.prompt.render_success_message(SUCCEEDED_MSG)
        else:
            self.prompt.render_failure_message(FAILED_MSG)

        self.prompt.render_title(SYNC_TITLE)
        self.prompt.render_document_list(documents)

        if not self.succeeded:
            n = 1
            self.prompt.render_title(REPORTED_ERRORS % dict(n=len(self.errors)))
            for ne in self.errors:
                repo_id = ne['error_id']
                details = ne['details']
                details['n'] = n
                description = NODE_ERRORS.get(repo_id, str(ne))
                self.prompt.write('- %.2d: %s\n' % (n, description % details))
                n += 1

        failed_repositories = self.failed_repositories()
        if failed_repositories:
            self.prompt.render_title(REPOSITORIES_FAILED)
            for repo_id in failed_repositories:
                self.prompt.write('- %s' % repo_id)

    def failed_repositories(self):
        failed = set()
        for error in self.errors:
            repo_id = error['details'].get('repo_id')
            if repo_id:
                failed.add(repo_id)
        return sorted(failed)
