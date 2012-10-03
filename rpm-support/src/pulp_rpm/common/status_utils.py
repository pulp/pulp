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

from gettext import gettext as _

from pulp_rpm.common import constants

# -- general rendering functions ----------------------------------------------

def render_general_spinner_step(prompt, spinner, current_state, last_state, start_text, state_update_func):
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
        prompt.write(start_text)

    if current_state == constants.STATE_RUNNING:
        spinner.next()
        state_update_func(constants.STATE_RUNNING)

    elif current_state == constants.STATE_COMPLETE and last_state not in constants.COMPLETE_STATES:
        spinner.next(finished=True)
        prompt.write(_('... completed'))
        prompt.render_spacer()
        state_update_func(constants.STATE_COMPLETE)

    elif current_state == constants.STATE_SKIPPED and last_state not in constants.COMPLETE_STATES:
        spinner.next(finished=True)
        prompt.write(_('... skipped'))
        prompt.render_spacer()
        state_update_func(constants.STATE_SKIPPED)

    elif current_state == constants.STATE_FAILED and last_state not in constants.COMPLETE_STATES:
        spinner.next(finished=True)
        prompt.write(_('... failed'))
        prompt.render_spacer()
        state_update_func(constants.STATE_FAILED)


def render_itemized_in_progress_state(prompt, data, type_name, progress_bar, state):
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
        prompt.write(_('... completed'))
        prompt.render_spacer()

    # If there are any errors, write them out here
    # TODO: read this from config
    # display_error_count = self.context.extension_config.getint('main', 'num_display_errors')
    display_error_count = 5

    num_errors = min(len(data['error_details']), display_error_count)

    if num_errors > 0:
        prompt.render_failure_message(_('Individual errors encountered during publishing:'))

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

            prompt.render_failure_message(message)

        prompt.render_spacer()

