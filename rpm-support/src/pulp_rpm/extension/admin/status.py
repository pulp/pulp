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
from pulp_rpm.common.status_utils import render_general_spinner_step, render_itemized_in_progress_state

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
        render_general_spinner_step(self.prompt, self.metadata_spinner, current_state, self.metadata_last_state, _('Downloading metadata...'), update_func)

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
        render_general_spinner_step(self.prompt, self.errata_spinner, current_state, self.errata_last_state, _('Importing errata...'), update_func)

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
            render_itemized_in_progress_state(self.prompt, data, _('packages'), self.packages_bar, state)

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
            render_itemized_in_progress_state(self.prompt, data, _('distributions'), self.distributions_bar, state)

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
        render_general_spinner_step(self.prompt, self.comps_spinner, current_state, self.comps_last_state, _('Importing package groups/categories...'), update_func)

    def render_generate_metadata_step(self, progress_report):

        # Example Data:
        # "metadata": {
        #    "state": "FINISHED"
        # }

        current_state = progress_report['yum_distributor']['metadata']['state']
        def update_func(new_state):
            self.generate_metadata_last_state = new_state
        render_general_spinner_step(self.prompt, self.generate_metadata_spinner, current_state, self.generate_metadata_last_state, _('Generating metadata'), update_func)

    def render_publish_http_step(self, progress_report):

        # Example Data:
        # "publish_http": {
        #    "state": "SKIPPED"
        # },

        current_state = progress_report['yum_distributor']['publish_http']['state']
        def update_func(new_state):
            self.publish_http_last_state = new_state
        render_general_spinner_step(self.prompt, self.publish_http_spinner, current_state, self.publish_http_last_state, _('Publishing repository over HTTP'), update_func)

    def render_publish_https_step(self, progress_report):

        # Example Data:
        # "publish_http": {
        #    "state": "SKIPPED"
        # },

        current_state = progress_report['yum_distributor']['publish_https']['state']
        def update_func(new_state):
            self.publish_https_last_state = new_state
        render_general_spinner_step(self.prompt, self.publish_https_spinner, current_state, self.publish_https_last_state, _('Publishing repository over HTTPS'), update_func)


class RpmIsoStatusRenderer(StatusRenderer):

    def __init__(self, context):
        super(RpmIsoStatusRenderer, self).__init__(context)

        # Publish Steps
        self.rpms_last_state = constants.STATE_NOT_STARTED
        self.distributions_last_state = constants.STATE_NOT_STARTED
        self.generate_metadata_last_state = constants.STATE_NOT_STARTED
        self.isos_last_state = constants.STATE_NOT_STARTED
        self.publish_http_last_state = constants.STATE_NOT_STARTED
        self.publish_https_last_state = constants.STATE_NOT_STARTED
        self.displayed_generated_isos = False

        # UI Widgets
        self.rpms_bar = self.prompt.create_progress_bar()
        self.distributions_bar = self.prompt.create_progress_bar()
        self.generate_metadata_spinner = self.prompt.create_spinner()
        self.isos_bar = self.prompt.create_progress_bar()
        self.publish_http_spinner = self.prompt.create_spinner()
        self.publish_https_spinner = self.prompt.create_spinner()

    def display_report(self, progress_report):
        """
        Displays the contents of the progress report to the user. This will
        aggregate the calls to render individual sections of the report.
        """
        # Publish Steps
        if 'iso_distributor' in progress_report:
            self.render_rpms_step(progress_report)
            self.render_distributions_step(progress_report)
            self.render_generate_metadata_step(progress_report)
            self.render_isos_step(progress_report)
            self.render_publish_https_step(progress_report)
            self.render_publish_http_step(progress_report)
            self.display_generated_isos(progress_report)

    def render_rpms_step(self, progress_report):

        # Example Data:
        # "rpms": {
        # "num_success": 20, 
        # "items_left": 0, 
        # "items_total": 20, 
        # "state": "FINISHED", 
        # "error_details": [], 
        # "num_error": 0
        # },

        data = progress_report['iso_distributor']['rpms']
        state = data['state']

        if state == constants.STATE_NOT_STARTED:
            return

        # Only render this on the first non-not-started state
        if self.rpms_last_state == constants.STATE_NOT_STARTED:
            self.prompt.write(_('Exporting packages...'))

        # If it's running or finished, the output is still the same. This way,
        # if the status is viewed after this step, the content download
        # summary is still available.

        if state in (constants.STATE_RUNNING, constants.STATE_COMPLETE) and self.rpms_last_state not in constants.COMPLETE_STATES:

            self.rpms_last_state = state
            render_itemized_in_progress_state(self.prompt, data, _('rpms'), self.rpms_bar, state)

        elif state == constants.STATE_FAILED and self.rpms_last_state not in constants.COMPLETE_STATES:

            # This state means something went horribly wrong. There won't be
            # individual rpms error details which is why they are only
            # displayed above and not in this case.

            self.prompt.write(_('... failed'))
            self.rpms_last_state = constants.STATE_FAILED


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

        data = progress_report['iso_distributor']['distribution']
        state = data['state']

        if state == constants.STATE_NOT_STARTED:
            return

        # Only render this on the first non-not-started state
        if self.distributions_last_state  == constants.STATE_NOT_STARTED:
            self.prompt.write(_('Exporting distributions...'))

        # If it's running or finished, the output is still the same. This way,
        # if the status is viewed after this step, the content download
        # summary is still available.

        if state in (constants.STATE_RUNNING, constants.STATE_COMPLETE) and self.distributions_last_state not in constants.COMPLETE_STATES:

            self.distributions_last_state = state
            render_itemized_in_progress_state(self.prompt, data, _('distributions'), self.distributions_bar, state)

        elif state == constants.STATE_FAILED and self.distributions_last_state not in constants.COMPLETE_STATES:

            # This state means something went horribly wrong. There won't be
            # individual package error details which is why they are only
            # displayed above and not in this case.

            self.prompt.write(_('... failed'))
            self.distributions_last_state = constants.STATE_FAILED


    def render_isos_step(self, progress_report):
        
        # Example Data:
        # "isos": {
        #     "num_success": 1, 
        #     "size_total": 3361542, 
        #     "written_files": [
        #         "pulp-rhel6-20120920-01.iso"
        #      ], 
        #     "items_left": 0, 
        #     "items_total": 1, 
        #     "size_left": 0, 
        #     "state": "FINISHED", 
        #     "error_details": [], 
        #     "current_file": null, 
        #     "num_error": 0
        #     },

        data = progress_report['iso_distributor']['isos']
        state = data['state']

        if state == constants.STATE_NOT_STARTED:
            return

        # Only render this on the first non-not-started state
        if self.isos_last_state  == constants.STATE_NOT_STARTED:
            self.prompt.write(_('Creating ISOs...'))

        # If it's running or finished, the output is still the same. This way,
        # if the status is viewed after this step, summary is still available.
        if state in (constants.STATE_RUNNING, constants.STATE_COMPLETE) and self.isos_last_state not in constants.COMPLETE_STATES:

            self.isos_last_state = state

            overall_done = data['items_total'] - data['items_left']
            overall_total = data['items_total']

            if overall_total is 0:
                overall_total = overall_done = 1

            self.isos_bar.render(overall_done, overall_total)
            
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

                        template  = _('File:    %(name)s\n')
                        template += _('Error:   %(error)s\n')
                        if message_data["traceback"]:
                            template += _('Traceback:\n')
                            template += _('%(traceback)s')

                        message = template % message_data

                        self.prompt.render_failure_message(message)

                    self.prompt.render_spacer()
            
        elif state == constants.STATE_FAILED and self.isos_last_state not in constants.COMPLETE_STATES:

            # This state means something went horribly wrong. There won't be
            # individual package error details which is why they are only
            # displayed above and not in this case.

            self.prompt.write(_('... failed'))
            self.isos_last_state = constants.STATE_FAILED

    def render_generate_metadata_step(self, progress_report):

        # Example Data:
        # "metadata": {
        #    "state": "FINISHED"
        # }

        current_state = progress_report['iso_distributor']['metadata']['state']
        def update_func(new_state):
            self.generate_metadata_last_state = new_state
        render_general_spinner_step(self.prompt, self.generate_metadata_spinner, current_state, self.generate_metadata_last_state, _('Generating metadata'), update_func)

    def render_publish_http_step(self, progress_report):

        # Example Data:
        # "publish_http": {
        #    "state": "SKIPPED"
        # },

        current_state = progress_report['iso_distributor']['publish_http']['state']

        if current_state == constants.STATE_COMPLETE and self.publish_http_last_state not in constants.COMPLETE_STATES:
            self.publish_http_last_state = current_state
            self.prompt.write(_('Successfully published ISOs over HTTP'))
            self.prompt.render_spacer()
        if current_state == constants.STATE_FAILED and self.publish_http_last_state not in constants.COMPLETE_STATES:
            self.publish_http_last_state = current_state
            self.prompt.write(_('Failed to publish ISOs over HTTP'))
            self.prompt.render_spacer()

    def render_publish_https_step(self, progress_report):

        # Example Data:
        # "publish_http": {
        #    "state": "SKIPPED"
        # },

        current_state = progress_report['iso_distributor']['publish_https']['state']

        if current_state == constants.STATE_COMPLETE and self.publish_https_last_state not in constants.COMPLETE_STATES:
            self.publish_https_last_state = current_state
            self.prompt.write(_('Successfully published ISOs over HTTPS'))
            self.prompt.render_spacer()
        if current_state == constants.STATE_FAILED and self.publish_https_last_state not in constants.COMPLETE_STATES:
            self.publish_https_last_state = current_state
            self.prompt.write(_('Failed to publish ISOs over HTTPS'))
            self.prompt.render_spacer()

    def display_generated_isos(self, progress_report):

        # Example Data:
        # "isos": {
        #     "num_success": 1, 
        #     "size_total": 3361542, 
        #     "written_files": [
        #         "pulp-rhel6-20120920-01.iso"
        #      ], 
        #     "items_left": 0, 
        #     "items_total": 1, 
        #     "size_left": 0, 
        #     "state": "FINISHED", 
        #     "error_details": [], 
        #     "current_file": null, 
        #     "num_error": 0
        #     },

        https_state = progress_report['iso_distributor']['publish_https']['state']
        http_state = progress_report['iso_distributor']['publish_http']['state']

        if not self.displayed_generated_isos:
            if https_state in constants.COMPLETE_STATES and http_state in constants.COMPLETE_STATES: 
                filenames = progress_report['iso_distributor']['isos']['written_files']
                if filenames:
                    self.prompt.write(_('ISOs created:'))
                    for filename in filenames:
                        self.prompt.write('    %s' % filename)
                    self.prompt.render_spacer()
                    self.displayed_generated_isos = True



