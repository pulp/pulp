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

from gettext import gettext as _
import traceback

from pulp.client.commands.repo.sync_publish import StatusRenderer
from pulp.client.extensions.core import COLOR_FAILURE

from pulp_puppet.common import constants
from pulp_puppet.common.publish_progress import  PublishProgressReport
from pulp_puppet.common.sync_progress import SyncProgressReport

class PuppetStatusRenderer(StatusRenderer):

    def __init__(self, context):
        super(PuppetStatusRenderer, self).__init__(context)

        # Sync Steps
        self.sync_metadata_last_state = constants.STATE_NOT_STARTED
        self.sync_modules_last_state = constants.STATE_NOT_STARTED

        # Publish Steps
        self.publish_modules_last_state = constants.STATE_NOT_STARTED
        self.publish_metadata_last_state = constants.STATE_NOT_STARTED
        self.publish_http_last_state = constants.STATE_NOT_STARTED
        self.publish_https_last_state = constants.STATE_NOT_STARTED

        # UI Widgets
        self.sync_metadata_bar = self.prompt.create_progress_bar()
        self.sync_modules_bar = self.prompt.create_progress_bar()
        self.publish_modules_bar = self.prompt.create_progress_bar()
        self.publish_metadata_spinner = self.prompt.create_spinner()

    def display_report(self, progress_report):

        # Sync Steps
        if constants.IMPORTER_ID in progress_report:
            sync_report = SyncProgressReport.from_progress_dict(progress_report[constants.IMPORTER_ID])
            self._display_sync_metadata_step(sync_report)
            self._display_sync_modules_step(sync_report)

        # Publish Steps
        if constants.DISTRIBUTOR_ID in progress_report:
            publish_report = PublishProgressReport.from_progress_dict(progress_report[constants.DISTRIBUTOR_ID])
            self._display_publish_modules_step(publish_report)
            self._display_publish_metadata_step(publish_report)
            self._display_publish_http_https_step(publish_report)

    # -- private --------------------------------------------------------------

    def _display_sync_metadata_step(self, sync_report):

        # Do nothing if it hasn't started yet or has already finished
        if sync_report.metadata_state == constants.STATE_NOT_STARTED or \
           self.sync_metadata_last_state in constants.COMPLETE_STATES:
            return

        # Only render this on the first non-not-started state
        if self.sync_metadata_last_state == constants.STATE_NOT_STARTED:
            self.prompt.write(_('Downloading metadata...'), tag='download-metadata')

        # Same behavior for running or success
        if sync_report.metadata_state in (constants.STATE_RUNNING, constants.STATE_SUCCESS):
            items_done = sync_report.metadata_query_finished_count
            items_total = sync_report.metadata_query_total_count
            item_type = _('Metadata Query')

            self._render_itemized_in_progress_state(items_done, items_total,
                item_type, self.sync_metadata_bar, sync_report.metadata_state)

        # The only state left to handle is if it failed
        else:
            self.prompt.render_failure_message(_('... failed'))
            self.prompt.render_spacer()
            self._render_error(sync_report.metadata_error_message,
                                sync_report.metadata_exception,
                                sync_report.metadata_traceback)

        # Before finishing update the state
        self.sync_metadata_last_state = sync_report.metadata_state

    def _display_sync_modules_step(self, sync_report):

        # Do nothing if it hasn't started yet or has already finished
        if sync_report.modules_state == constants.STATE_NOT_STARTED or \
           self.sync_modules_last_state in constants.COMPLETE_STATES:
            return

        # Only render this on the first non-not-started state
        if self.sync_modules_last_state == constants.STATE_NOT_STARTED:
            self.prompt.write(_('Downloading new modules...'), tag='downloading')

        # Same behavior for running or success
        if sync_report.modules_state in (constants.STATE_RUNNING, constants.STATE_SUCCESS):
            items_done = sync_report.modules_finished_count + sync_report.modules_error_count
            items_total = sync_report.modules_total_count
            item_type = _('Module')

            self._render_itemized_in_progress_state(items_done, items_total, item_type,
                self.sync_modules_bar, sync_report.modules_state)

        # The only state left to handle is if it failed
        else:
            self.prompt.render_failure_message(_('... failed'))
            self.prompt.render_spacer()
            self._render_error(sync_report.modules_error_message,
                               sync_report.modules_exception,
                               sync_report.modules_traceback)

        # Regardless of success or failure, display any individual module errors
        # if the new state is complete
        if sync_report.modules_state in constants.COMPLETE_STATES:
            self._render_module_errors(sync_report.modules_individual_errors)

        # Before finishing update the state
        self.sync_modules_last_state = sync_report.modules_state

    def _display_publish_modules_step(self, publish_report):

        # Do nothing if it hasn't started yet or has already finished
        if publish_report.modules_state == constants.STATE_NOT_STARTED or \
           self.publish_modules_last_state in constants.COMPLETE_STATES:
            return

        # Only render this on the first non-not-started state
        if self.publish_modules_last_state == constants.STATE_NOT_STARTED:
            self.prompt.write(_('Publishing modules...'), tag='publishing')

        # Same behavior for running or success
        if publish_report.modules_state in (constants.STATE_RUNNING, constants.STATE_SUCCESS):
            items_done = publish_report.modules_finished_count + publish_report.modules_error_count
            items_total = publish_report.modules_total_count
            item_type = _('Module')

            self._render_itemized_in_progress_state(items_done, items_total, item_type,
                self.publish_modules_bar, publish_report.modules_state)

        # The only state left to handle is if it failed
        else:
            self.prompt.render_failure_message(_('... failed'))
            self.prompt.render_spacer()
            self._render_error(publish_report.modules_error_message,
                               publish_report.modules_exception,
                               publish_report.modules_traceback)

        # Regardless of success or failure, display any individual module errors
        # if the new state is complete
        if publish_report.modules_state in constants.COMPLETE_STATES:
            self._render_module_errors(publish_report.modules_individual_errors)

        # Before finishing update the state
        self.publish_modules_last_state = publish_report.modules_state

    def _display_publish_metadata_step(self, publish_report):

        # Do nothing if it hasn't started yet or has already finished
        if publish_report.metadata_state == constants.STATE_NOT_STARTED or \
           self.publish_metadata_last_state in constants.COMPLETE_STATES:
            return

        # Only render this on the first non-not-started state
        if self.publish_metadata_last_state == constants.STATE_NOT_STARTED:
            self.prompt.write(_('Generating repository metadata...'), tag='generating')

        if publish_report.metadata_state == constants.STATE_RUNNING:
            self.publish_metadata_spinner.next()

        elif publish_report.metadata_state == constants.STATE_SUCCESS:
            self.publish_metadata_spinner.next(finished=True)
            self.prompt.write(_('... completed'), tag='completed')
            self.prompt.render_spacer()

        elif publish_report.metadata_state == constants.STATE_FAILED:
            self.publish_metadata_spinner.next(finished=True)
            self.prompt.render_failure_message(_('... failed'))
            self.prompt.render_spacer()
            self._render_error(publish_report.modules_error_message,
                               publish_report.modules_exception,
                               publish_report.modules_traceback)

        self.publish_metadata_last_state = publish_report.metadata_state

    def _display_publish_http_https_step(self, publish_report):

        # -- HTTP --------
        if publish_report.publish_http != constants.STATE_NOT_STARTED and \
           self.publish_http_last_state not in constants.COMPLETE_STATES:

            self.prompt.write(_('Publishing repository over HTTP...'))

            if publish_report.publish_http == constants.STATE_SUCCESS:
                self.prompt.write(_('... completed'), tag='http-completed')
            elif publish_report.publish_http == constants.STATE_SKIPPED:
                self.prompt.write(_('... skipped'), tag='http-skipped')
            else:
                self.prompt.write(_('... unknown'), tag='http-unknown')

            self.publish_http_last_state = publish_report.publish_http

            self.prompt.render_spacer()

        # -- HTTPS --------
        if publish_report.publish_https != constants.STATE_NOT_STARTED and \
           self.publish_https_last_state not in constants.COMPLETE_STATES:

            self.prompt.write(_('Publishing repository over HTTPS...'))

            if publish_report.publish_https == constants.STATE_SUCCESS:
                self.prompt.write(_('... completed'), tag='https-completed')
            elif publish_report.publish_https == constants.STATE_SKIPPED:
                self.prompt.write(_('... skipped'), tag='https-skipped')
            else:
                self.prompt.write(_('... unknown'), tag='https-unknown')

            self.publish_https_last_state = publish_report.publish_https

    def _render_itemized_in_progress_state(self, items_done, items_total, type_name,
                                           progress_bar, current_state):
        """
        This is a pretty ugly way of reusing similar code between the publish
        steps for packages and distributions. There might be a cleaner way
        but I was having trouble updating the correct state variable and frankly
        I'm out of time. Feel free to fix this if you are inspired.
        """

        # For the progress bar to work, we can't write anything after it until
        # we're completely finished with it. Assemble the download summary into
        # a string and let the progress bar render it.

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

        if current_state == constants.STATE_SUCCESS:
            self.prompt.write(_('... completed'))
            self.prompt.render_spacer()

    def _render_module_errors(self, individual_errors):

        if individual_errors is not None:

            # TODO: read this from config
            display_error_count = 5

            num_errors = min(len(individual_errors), display_error_count)

            if num_errors > 0:
                self.prompt.render_failure_message(_('Individual module errors occurred:'))

                for i, module_name in enumerate(individual_errors):
                    if i >= num_errors:
                        break

                    exception = individual_errors[module_name]['exception']
                    tb = individual_errors[module_name]['traceback']
                    tb = traceback.format_list(tb)

                    # render_failure_message puts too many blank lines, so
                    # simulate that rendering here

                    message =  _('Module: %(m)s') % {'m' : module_name}
                    self.prompt.write(message, color=COLOR_FAILURE)

                    message = _('Exception: %(e)s' % {'e' : exception})
                    self.prompt.write(message, color=COLOR_FAILURE)

                    message = _('Traceback:\n%(t)s') % {'t' : ''.join(tb)}
                    self.prompt.write(message, color=COLOR_FAILURE, skip_wrap=True)

                    self.prompt.render_spacer()

    def _render_error(self, error_message, exception, traceback):
        msg = _('The following error was encountered during the previous '
                'step. More information can be found in %(log)s')
        self.prompt.render_failure_message(msg % {'log' : self.context.config['logging']['filename']})
        self.prompt.render_spacer()
        self.prompt.render_failure_message('  %s' % error_message)

        self.context.logger.error(error_message)
        self.context.logger.error(exception)
        self.context.logger.error(traceback)