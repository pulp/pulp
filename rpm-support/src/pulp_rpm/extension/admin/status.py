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
Contains functionality related to rendering the progress report for a the RPM
plugins (both the sync and publish operations).
"""

from gettext import gettext as _

from pulp.client.commands.repo.sync_publish import StatusRenderer

from pulp_rpm.common import constants


class RpmStatusRenderer(StatusRenderer):

    def __init__(self, context):
        super(RpmStatusRenderer, self).__init__(context)

        # Sync Steps
        self.metadata_last_state = constants.STATE_NOT_STARTED
        self.download_last_state = constants.STATE_NOT_STARTED
        self.errata_last_state = constants.STATE_NOT_STARTED
        self.comps_last_state = constants.STATE_NOT_STARTED

        # Publish Steps
        self.packages_last_state = constants.STATE_NOT_STARTED
        self.distributions_last_state = constants.STATE_NOT_STARTED
        self.generate_metadata_last_state = constants.STATE_NOT_STARTED
        self.publish_http_last_state = constants.STATE_NOT_STARTED
        self.publish_https_last_state = constants.STATE_NOT_STARTED

        # UI Widgets
        self.metadata_spinner = self.prompt.create_spinner()
        self.download_bar = self.prompt.create_progress_bar()
        self.errata_spinner = self.prompt.create_spinner()
        self.comps_spinner = self.prompt.create_spinner()

        self.packages_bar = self.prompt.create_progress_bar()
        self.distributions_bar = self.prompt.create_progress_bar()
        self.generate_metadata_spinner = self.prompt.create_spinner()
        self.publish_http_spinner = self.prompt.create_spinner()
        self.publish_https_spinner = self.prompt.create_spinner()

    def display_report(self, progress_report):
        """
        Displays the contents of the progress report to the user. This will
        aggregate the calls to render individual sections of the report.
        """

        # There's a small race condition where the task will indicate it's
        # begun running but the importer has yet to submit a progress report
        # (or it has yet to be saved into the task). This should be alleviated
        # by the if statements below.

        # Sync Steps
        if 'yum_importer' in progress_report:
            self.render_metadata_step(progress_report)
            self.render_download_step(progress_report)
            self.render_errata_step(progress_report)
            self.render_comps_step(progress_report)

        # Publish Steps
        if 'yum_distributor' in progress_report:
            self.render_packages_step(progress_report)
            self.render_distributions_step(progress_report)
            self.render_generate_metadata_step(progress_report)
            self.render_publish_http_step(progress_report)
            self.render_publish_https_step(progress_report)

    def render_metadata_step(self, progress_report):

        # Example Data:
        # "metadata": {
        #    "state": "FINISHED"
        # }

        current_state = progress_report['yum_importer']['metadata']['state']
        def update_func(new_state):
            self.metadata_last_state = new_state
        self._render_general_spinner_step(self.metadata_spinner, current_state, self.metadata_last_state, _('Downloading metadata...'), update_func)

    def render_download_step(self, progress_report):

        # Example Data:
        # "content": {
        #    "num_success": 21,
        #    "size_total": 3871257,
        #    "items_left": 0,
        #    "items_total": 21,
        #    "state": "FINISHED",
        #    "size_left": 0,
        #    "details": {
        #        "tree_file": {
        #            "num_success": 0,
        #            "size_total": 0,
        #            "items_left": 0,
        #            "items_total": 0,
        #            "size_left": 0,
        #            "num_error": 0
        #        },
        #        "rpm": {
        #            "num_success": 21,
        #            "size_total": 3871257,
        #            "items_left": 0,
        #            "items_total": 21,
        #            "size_left": 0,
        #            "num_error": 0
        #        },
        #        "delta_rpm": {
        #            "num_success": 0,
        #            "size_total": 0,
        #            "items_left": 0,
        #            "items_total": 0,
        #            "size_left": 0,
        #            "num_error": 0
        #        },
        #        "file": {
        #            "num_success": 0,
        #            "size_total": 0,
        #            "items_left": 0,
        #            "items_total": 0,
        #            "size_left": 0,
        #            "num_error": 0
        #        }
        #    },
        # }

        data = progress_report['yum_importer']['content']
        state = data['state']

        # Render nothing if we haven't begun yet
        if state == constants.STATE_NOT_STARTED:
            return

        details = data['details']

        # Only render this on the first non-not-started state
        if self.download_last_state == constants.STATE_NOT_STARTED:
            self.prompt.write(_('Downloading repository content...'))

        # If it's running or finished, the output is still the same. This way,
        # if the status is viewed after this step, the content download
        # summary is still available.

        if state in (constants.STATE_RUNNING, constants.STATE_COMPLETE) and self.download_last_state not in constants.COMPLETE_STATES:

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

            if state == constants.STATE_COMPLETE:
                self.prompt.write(_('... completed'))
                self.prompt.render_spacer()

                # If there are any errors, write them out here
                # TODO: read this from config
                # display_error_count = self.context.extension_config.getint('main', 'num_display_errors')
                display_error_count = 5

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

        elif state == constants.STATE_FAILED and self.download_last_state not in constants.COMPLETE_STATES:

            # This state means something went horribly wrong. There won't be
            # individual package error details which is why they are only
            # displayed above and not in this case.

            self.prompt.write(_('... failed'))
            self.download_last_state = constants.STATE_FAILED

    def render_errata_step(self, progress_report):

        # Example Data:
        # "errata": {
        #    "state": "FINISHED",
        #    "num_errata": 0
        # }

        current_state = progress_report['yum_importer']['errata']['state']
        def update_func(new_state):
            self.errata_last_state = new_state
        self._render_general_spinner_step(self.errata_spinner, current_state, self.errata_last_state, _('Importing errata...'), update_func)

    def render_packages_step(self, progress_report):

        # Example Data:
        # "packages": {
        #    "num_success": 21,
        #    "items_left": 0,
        #    "items_total": 21,
        #    "state": "FINISHED",
        #    "error_details": [],
        #    "num_error": 0
        # },

        data = progress_report['yum_distributor']['packages']
        state = data['state']

        if state == constants.STATE_NOT_STARTED:
            return

        # Only render this on the first non-not-started state
        if self.packages_last_state == constants.STATE_NOT_STARTED:
            self.prompt.write(_('Publishing packages...'))

        # If it's running or finished, the output is still the same. This way,
        # if the status is viewed after this step, the content download
        # summary is still available.

        if state in (constants.STATE_RUNNING, constants.STATE_COMPLETE) and self.packages_last_state not in constants.COMPLETE_STATES:

            self.packages_last_state = state
            self._render_itemized_in_progress_state(data, _('packages'), self.packages_bar, state)

        elif state == constants.STATE_FAILED and self.packages_last_state not in constants.COMPLETE_STATES:

            # This state means something went horribly wrong. There won't be
            # individual package error details which is why they are only
            # displayed above and not in this case.

            self.prompt.write(_('... failed'))
            self.packages_last_state = constants.STATE_FAILED

    def render_distributions_step(self, progress_report):

        # Example Data:
        # "distribution": {
        #    "num_success": 0,
        #    "items_left": 0,
        #    "items_total": 0,
        #    "state": "FINISHED",
        #    "error_details": [],
        #    "num_error": 0
        # },

        data = progress_report['yum_distributor']['distribution']
        state = data['state']

        if state == constants.STATE_NOT_STARTED:
            return

        # Only render this on the first non-not-started state
        if self.distributions_last_state  == constants.STATE_NOT_STARTED:
            self.prompt.write(_('Publishing distributions...'))

        # If it's running or finished, the output is still the same. This way,
        # if the status is viewed after this step, the content download
        # summary is still available.

        if state in (constants.STATE_RUNNING, constants.STATE_COMPLETE) and self.distributions_last_state not in constants.COMPLETE_STATES:

            self.distributions_last_state = state
            self._render_itemized_in_progress_state(data, _('distributions'), self.distributions_bar, state)

        elif state == constants.STATE_FAILED and self.distributions_last_state not in constants.COMPLETE_STATES:

            # This state means something went horribly wrong. There won't be
            # individual package error details which is why they are only
            # displayed above and not in this case.

            self.prompt.write(_('... failed'))
            self.distributions_last_state = constants.STATE_FAILED

    def render_comps_step(self, progress_report):
        # Example Data:
        # "comps": {
        #    "state": "FINISHED",
        #    "num_available_groups": 0,
        #    "num_available_categories": 0,
        #    "num_orphaned_groups": 0,
        #    "num_orphaned_categories": 0,
        #    "num_new_groups": 0,
        #    "num_new_categories": 0,
        # }

        current_state = progress_report['yum_importer']['comps']['state']
        def update_func(new_state):
            self.comps_last_state = new_state
        self._render_general_spinner_step(self.comps_spinner, current_state, self.comps_last_state, _('Importing package groups/categories...'), update_func)

    def render_generate_metadata_step(self, progress_report):

        # Example Data:
        # "metadata": {
        #    "state": "FINISHED"
        # }

        current_state = progress_report['yum_distributor']['metadata']['state']
        def update_func(new_state):
            self.generate_metadata_last_state = new_state
        self._render_general_spinner_step(self.generate_metadata_spinner, current_state, self.generate_metadata_last_state, _('Generating metadata'), update_func)

    def render_publish_http_step(self, progress_report):

        # Example Data:
        # "publish_http": {
        #    "state": "SKIPPED"
        # },

        current_state = progress_report['yum_distributor']['publish_http']['state']
        def update_func(new_state):
            self.publish_http_last_state = new_state
        self._render_general_spinner_step(self.publish_http_spinner, current_state, self.publish_http_last_state, _('Publishing repository over HTTP'), update_func)

    def render_publish_https_step(self, progress_report):

        # Example Data:
        # "publish_http": {
        #    "state": "SKIPPED"
        # },

        current_state = progress_report['yum_distributor']['publish_https']['state']
        def update_func(new_state):
            self.publish_https_last_state = new_state
        self._render_general_spinner_step(self.publish_https_spinner, current_state, self.publish_https_last_state, _('Publishing repository over HTTPS'), update_func)

    # -- general rendering functions ----------------------------------------------

    def _render_general_spinner_step(self, spinner, current_state, last_state, start_text, state_update_func):
        """
        There are a number of steps that are simply running or finished. This
        method will apply a standard display for those situations.

        @param spinner: spinner instance to use to show progress; should be
               different per call and not reused
        @type  spinner: Spinner

        @param current_state: state of the step taken from the progress report
        @type  current_state: str

        @param last_state: last state for the step as stored in this instance
        @type  last_state: str

        @param start_text: text to describe the step; only displayed the first
               time the step begins; should be i18n'd before this call
        @type  start_text: str

        @param state_update_func: function to call into to change the state for
               this step
        @type  state_update_func: func
        """

        # Render nothing if we haven't begun yet
        if current_state == constants.STATE_NOT_STARTED:
            return

        # Only render this on the first non-not-started state
        if last_state == constants.STATE_NOT_STARTED:
            self.prompt.write(start_text)

        if current_state == constants.STATE_RUNNING:
            spinner.next()
            state_update_func(constants.STATE_RUNNING)

        elif current_state == constants.STATE_COMPLETE and last_state not in constants.COMPLETE_STATES:
            spinner.next(finished=True)
            self.prompt.write(_('... completed'))
            self.prompt.render_spacer()
            state_update_func(constants.STATE_COMPLETE)

        elif current_state == constants.STATE_SKIPPED and last_state not in constants.COMPLETE_STATES:
            spinner.next(finished=True)
            self.prompt.write(_('... skipped'))
            self.prompt.render_spacer()
            state_update_func(constants.STATE_SKIPPED)

        elif current_state == constants.STATE_FAILED and last_state not in constants.COMPLETE_STATES:
            spinner.next(finished=True)
            self.prompt.write(_('... failed'))
            self.prompt.render_spacer()
            state_update_func(constants.STATE_FAILED)

    def _render_itemized_in_progress_state(self, data, type_name, progress_bar, state):
        """
        This is a pretty ugly way of reusing similar code between the publish
        steps for packages and distributions. There might be a cleaner way
        but I was having trouble updating the correct state variable and frankly
        I'm out of time. Feel free to fix this if you are inspired.
        """

        # For the progress bar to work, we can't write anything after it until
        # we're completely finished with it. Assemble the download summary into
        # a string and let the progress bar render it.

        items_done = data['items_total'] - data['items_left']
        items_total = data['items_total']

        message_data = {
            'name'        : type_name.title(),
            'items_done'  : items_done,
            'items_total' : items_total,
            }

        template = _('%(name)s: %(items_done)s/%(items_total)s items')
        bar_message = template % message_data

        # If there's nothing to download in this step, flag the bar as complete
        if items_total is 0:
            items_total = items_done = 1

        progress_bar.render(items_done, items_total, message=bar_message)

        if state == constants.STATE_COMPLETE:
            self.prompt.write(_('... completed'))
            self.prompt.render_spacer()

            # If there are any errors, write them out here
            # TODO: read this from config
            # display_error_count = self.context.extension_config.getint('main', 'num_display_errors')
            display_error_count = 5

            num_errors = min(len(data['error_details']), display_error_count)

            if num_errors > 0:
                self.prompt.render_failure_message(_('Individual errors encountered during publishing:'))

                for i in range(0, num_errors):
                    error = data['error_details'][i]
                    error_msg = error['error']
                    traceback = '\n'.join(error['traceback'])

                    message_data = {
                        'name'      : error['filename'],
                        'error'      : error_msg,
                        'traceback' : traceback
                    }

                    template  = 'File:    %(name)s\n'
                    template += 'Error:   %(error)s\n'
                    if message_data["traceback"]:
                        template += 'Traceback:\n'
                        template += '%(traceback)s'
                    template = _(template)

                    message = template % message_data

                    self.prompt.render_failure_message(message)
                self.prompt.render_spacer()
