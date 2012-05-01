# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
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
Contains functionality related to rendering the progress report for an
RPM sync operation.
"""

from gettext import gettext as _

# -- constants ----------------------------------------------------------------

STATE_NOT_STARTED = 'NOT_STARTED'
STATE_RUNNING = 'IN_PROGRESS'
STATE_COMPLETE = 'FINISHED'
STATE_FAILED = 'FAILED'
END_STATES = (STATE_COMPLETE, STATE_FAILED)

# -- classes ------------------------------------------------------------------

class StatusRenderer(object):

    def __init__(self, context):
        self.context = context
        self.prompt = context.prompt

        self.metadata_last_state = STATE_NOT_STARTED
        self.download_last_state = STATE_NOT_STARTED
        self.errata_last_state = STATE_NOT_STARTED

        self.metadata_spinner = self.prompt.create_spinner()
        self.download_bar = self.prompt.create_progress_bar()
        self.errata_spinner = self.prompt.create_spinner()


    def display_report(self, progress_report):
        """
        Displays the contents of the progress report to the user. This will
        aggregate the calls to render individual sections of the report.
        """

        # There's a small race condition where the task will indicate it's
        # begun running but the importer has yet to submit a progress report
        # (or it has yet to be saved into the task). Quick check here to make
        # sure the importer's report is present before proceeding.

        if 'importer' not in progress_report:
            return

        self.render_metadata_step(progress_report)
        self.render_download_step(progress_report)
        self.render_errata_step(progress_report)

    def render_metadata_step(self, progress_report):
        """
        Displays the details of the importer's metadata download step.
        """

        state = progress_report['importer']['metadata']['state']

        # Render nothing if we haven't begun yet
        if state == STATE_NOT_STARTED:
            return

        # Only render this on the first non-not-started state
        if self.metadata_last_state == STATE_NOT_STARTED:
            self.prompt.write(_('Downloading metadata...'))

        if state == STATE_RUNNING:
            self.metadata_spinner.next()
            self.metadata_last_state = STATE_RUNNING

        elif state == STATE_COMPLETE and self.metadata_last_state not in END_STATES:
            self.metadata_spinner.next(finished=True)
            self.prompt.write(_('... completed'))
            self.prompt.render_spacer()
            self.metadata_last_state = STATE_COMPLETE

        elif state == STATE_FAILED and self.metadata_last_state not in END_STATES:
            self.metadata_spinner.next(finished=True)
            self.prompt.write(_('... failed'))
            self.prompt.render_spacer()
            self.metadata_last_state = STATE_FAILED

    def render_download_step(self, progress_report):
        """
        Displays the details of the importer's downloading of packages.
        """

        data = progress_report['importer']['content']
        state = data['state']

        # Render nothing if we haven't begun yet
        if state == STATE_NOT_STARTED:
            return

        details = data['details']

        # Only render this on first non-not-started state
        if self.download_last_state == STATE_NOT_STARTED:
            self.prompt.write(_('Downloading repository content...'))

        # If it's running or finished, the output is still the same. This way,
        # if the status is viewed after this step, the content download
        # summary is still available.

        # Sync report format can be found at: https://fedorahosted.org/pulp/wiki/RepoSyncStatus

        if state in (STATE_RUNNING, STATE_COMPLETE) and self.download_last_state not in END_STATES:

            self.download_last_state = state

            # For the progress bar to work, we can't write anything after it until
            # we're completely finished with it. Assemble the download summary into
            # a string and let the progress bar render it.
            message_data = {
                'rpm_done'    : details['rpm']['items_total'] - details['rpm']['items_left'],
                'rpm_total'   : details['rpm']['items_total'],
                'delta_done'  : details['delta_rpm']['items_total'] - details['delta_rpm']['items_left'],
                'delta_total' : details['delta_rpm']['items_total'],
                'tree_done'   : details['tree_file']['items_total'] - details['tree_file']['items_left'],
                'tree_total'  : details['tree_file']['items_total'],
                'file_done'   : details['file']['items_total'] - details['file']['items_left'],
                'file_total'  : details['file']['items_total'],
                }

            template  = 'RPMs:       %(rpm_done)s/%(rpm_total)s items\n'
            template += 'Delta RPMs: %(delta_done)s/%(delta_total)s items\n'
            template += 'Tree Files: %(tree_done)s/%(tree_total)s items\n'
            template += 'Files:      %(file_done)s/%(file_total)s items'
            template = _(template)

            bar_message = template % message_data

            overall_done = data['size_total'] - data['size_left']
            overall_total = data['size_total']

            # If all of the packages are already downloaded and up to date,
            # the total bytes to process will be 0. This means the download
            # step is basically finished, so fill the progress bar.
            if overall_total is 0:
                overall_total = overall_done = 1

            self.download_bar.render(overall_done, overall_total, message=bar_message)

            if state == STATE_COMPLETE:
                self.prompt.write(_('... completed'))
                self.prompt.render_spacer()

                # If there are any errors, write them out here
                display_error_count = self.context.extension_config.getint('main', 'num_display_errors')

                num_errors = min(len(data['error_details']), display_error_count)

                if num_errors > 0:
                    self.prompt.render_failure_message(_('Individual package errors encountered during sync:'))

                    for i in range(0, num_errors):
                        error = data['error_details'][i]
                        error_msg = error['error']
                        traceback = '\n'.join(error['traceback'])

                        message_data = {
                            'name'      : error['filename'],
                            'error'      : error_msg,
                            'traceback' : traceback
                        }

                        template  = 'Package: %(name)s\n'
                        template += 'Error:   %(error)s\n'
                        if message_data["traceback"]:
                            template += 'Traceback:\n'
                            template += '%(traceback)s'

                        message = template % message_data

                        self.prompt.render_failure_message(message)
                    self.prompt.render_spacer()

        elif state == STATE_FAILED and self.download_last_state not in END_STATES:

            # This state means something went horribly wrong. There won't be
            # individual package error details which is why they are only
            # displayed above and not in this case.

            self.prompt.write(_('... failed'))
            self.download_last_state = STATE_FAILED

    def render_errata_step(self, progress_report):
        """
        Displays the details of the importer's errata import step.
        """

        state = progress_report['importer']['errata']['state']

        # Render nothing if we haven't begun yet
        if state == STATE_NOT_STARTED:
            return

        # Only render this on the first non-not-started state
        if self.errata_last_state == STATE_NOT_STARTED:
            self.prompt.write(_('Importing errata...'))

        if state == STATE_RUNNING:
            self.errata_spinner.next()
            self.errata_last_state = STATE_RUNNING

        elif state == STATE_COMPLETE and self.errata_last_state not in END_STATES:
            self.errata_spinner.next(finished=True)
            self.prompt.write(_('Imported %s errata') % progress_report['importer']['errata']['num_errata'])
            self.prompt.write(_('... completed'))
            self.prompt.render_spacer()
            self.errata_last_state = STATE_COMPLETE

        elif state == STATE_FAILED and self.errata_last_state not in END_STATES:
            self.errata_spinner.next(finished=True)
            self.prompt.write(_('... failed'))
            self.prompt.render_spacer()
            self.errata_last_state = STATE_FAILED
