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
    RepositoryReport.ADDED: _('Added'),
    RepositoryReport.MERGED: _('Merged'),
    RepositoryReport.DELETED: _('Removed')
}

SYNC_TITLE = _('Child Node Synchronization')
SUCCEEDED_MSG = _('Synchronization succeeded')
FAILED_MSG = _('Error occurred during synchronization, check the child node logs for details')
REPORTED_ERRORS = _('The following [%(n)d] errors were reported:')
REPOSITORIES_FAILED = _('The following repositories had errors:')


# --- rendering --------------------------------------------------------------


class ProgressTracker:

    def __init__(self, prompt):
        self.prompt = prompt
        self.snapshot = []

    def display(self, report):
        reports = report['progress']

        # On the 2nd+ report, update the last in-progress report.
        if self.snapshot:
            r, pb = self.snapshot[-1]
            repo_id = r['repo_id']
            r = self._find(repo_id, reports)
            self._render(r, pb)

        # The latency in polling can causes gaps in the reported progress.
        # This includes the gap between never having processed a report and receiving
        # the 1st report.  Here, we get caught up in all cases.
        in_progress = self._in_progress(reports)
        for i in range(len(self.snapshot), len(in_progress)):
            r = in_progress[i]
            pb = self.prompt.create_progress_bar()
            self.snapshot.append((r, pb))
            repo_id = r['repo_id']
            self.prompt.write('\n')
            self.prompt.write(REPOSITORY_FIELD % {'n': i + 1, 't': len(reports), 'id': repo_id})
            self._render(r, pb)

    def _find(self, repo_id, reports):
        for r in reports:
            if r['repo_id'] == repo_id:
                return r

    def _in_progress(self, reports):
        return [r for r in reports if r['state'] != RepositoryProgress.PENDING]

    def _render(self, report, pb):
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
                pb.render(1, 1)
            else:
                pb.render(0.01, 1)
        else:
            pb.render(completed, total, message)

        return pb


class UpdateRenderer(object):
    """
    Render the node synchronization summary with the following format:
      succeeded: <bool>
      details: {
        errors: [
          { error_id: <str>,
            details: {}
        ]
        repositories: [
          { repo_id: <str>,
            action: <str>,
            units: {
              added: <int>,
              updated: <int>,
              removed: <int>
            }
        ]
      }
    """

    def __init__(self, prompt, report):
        self.prompt = prompt
        self.succeeded = report['succeeded']
        self.details = report['details']
        self.errors = self.details['errors']
        self.repositories = self.details['repositories']

    def render(self):
        documents = []
        for repo_report in sorted(self.repositories, key=itemgetter('repo_id')):
            document = {
                'repository': {
                    'id': repo_report['repo_id'],
                    'action': ACTIONS[repo_report['action']],
                    'units': repo_report['units']
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
            self.prompt.render_title(REPORTED_ERRORS % dict(n=len(self.errors)))
            self.prompt.render_document_list(self.errors)

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