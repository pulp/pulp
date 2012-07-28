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
import os

from okaara.prompt import COLOR_GREEN, COLOR_YELLOW

from   pulp.client.extensions.extensions import PulpCliCommand
import pulp.client.upload.manager as upload_lib
from   pulp.client.upload.ui import perform_upload

# -- constants ----------------------------------------------------------------

COLOR_RUNNING = COLOR_GREEN
COLOR_PAUSED = COLOR_YELLOW

# -- framework hook -----------------------------------------------------------

def initialize(context):

    repo_section = context.cli.find_section('repo')
    uploads_section = repo_section.create_subsection('uploads', _('package and errata upload'))

    d = 'lists in progress and paused uploads'
    uploads_section.add_command(ListCommand(context, 'list', _(d)))

    d = 'resumes a paused upload request'
    uploads_section.add_command(ResumeCommand(context, 'resume', _(d)))

    d = 'cancels an outstanding upload request'
    uploads_section.add_command(CancelCommand(context, 'cancel', _(d)))

# -- commands -----------------------------------------------------------------

class ResumeCommand(PulpCliCommand):
    """
    Displays a list of paused uploads and allows one or more of them to be
    resumed.
    """

    def __init__(self, context, name, description):
        PulpCliCommand.__init__(self, name, description, self.resume)
        self.context = context

        d = 'display extra information about the upload process'
        self.create_flag('-v', _(d))

    def resume(self, **kwargs):
        self.context.prompt.render_title(_('Upload Requests'))

        # Determine which (if any) uploads are eligible to resume
        upload_manager = configure_upload_manager(self.context)
        uploads = upload_manager.list_uploads()

        if len(uploads) is 0:
            d = 'No outstanding uploads found'
            self.context.prompt.render_paragraph(_(d))
            return

        non_running_uploads = [u for u in uploads if not u.is_running]
        if len(non_running_uploads) is 0:
            d = 'All requests are currently in the process of being uploaded.'
            self.context.prompt.render_paragraph(_(d))
            return

        # Prompt the user to select one or more uploads to resume
        source_filenames = [os.path.basename(u.source_filename) for u in non_running_uploads]
        q = _('Select one or more uploads to resume: ')
        selected_indexes = self.context.prompt.prompt_multiselect_menu(q, source_filenames, interruptable=True)

        # User either selected no items or elected to abort (or ctrl+c)
        if selected_indexes is self.context.prompt.ABORT or len(selected_indexes) is 0:
            return

        # Resolve the user selections for display and uploading
        selected_uploads = [u for i, u in enumerate(non_running_uploads) if i in selected_indexes]
        selected_filenames = [os.path.basename(u.source_filename) for u in selected_uploads]
        selected_ids = [u.upload_id for u in selected_uploads]

        self.context.prompt.render_paragraph(_('Resuming upload for: %(u)s') % {'u' : ', '.join(selected_filenames)})

        perform_upload(self.context, upload_manager, selected_ids)

class ListCommand(PulpCliCommand):
    """
    Lists all upload requests, including their status of running v. paused.
    """

    def __init__(self, context, name, description):
        PulpCliCommand.__init__(self, name, description, self.list)
        self.context = context

    def list(self, **kwargs):
        self.context.prompt.render_title(_('Upload Requests'))

        # Load upload request trackers
        upload_manager = configure_upload_manager(self.context)
        uploads = upload_manager.list_uploads()

        # Punch out early if there are none
        if len(uploads) is 0:
            d = 'No outstanding uploads found'
            self.context.prompt.render_paragraph(_(d))
            return

        # Display each filename along with its status
        for upload in uploads:
            if upload.is_running:
                state = '[%s]' % self.context.prompt.color(_(' Running '), COLOR_RUNNING)
            else:
                state = '[%s]' % self.context.prompt.color(_(' Paused  '), COLOR_PAUSED)

            template = '%s %s'
            message = template % (state, os.path.basename(upload.source_filename))
            self.context.prompt.write(message)

        self.context.prompt.render_spacer()

class CancelCommand(PulpCliCommand):
    """
    Displays a list of paused uploads and allows the user to select one or more
    to resume uploading.
    """

    def __init__(self, context, name, description):
        PulpCliCommand.__init__(self, name, description, self.cancel)
        self.context = context

        d = 'removes the client-side tracking file for the upload regardless of ' \
        'whether or not it was able to be deleted on the server; this should ' \
        'only be used in the event that the server\'s knowledge of an upload ' \
        'has been removed'
        self.create_flag('--force', _(d))

    def cancel(self, **kwargs):
        self.context.prompt.render_title(_('Upload Requests'))

        force = kwargs['force'] or False

        # Load all requests
        upload_manager = configure_upload_manager(self.context)
        uploads = upload_manager.list_uploads()

        # Punch out early if there are no requests we can act on
        if len(uploads) is 0:
            d = 'No outstanding uploads found'
            self.context.prompt.render_paragraph(_(d))
            return

        # We can only cancel paused uploads, so check to make sure there is
        # at least one
        non_running_uploads = [u for u in uploads if not u.is_running]
        if len(non_running_uploads) is 0:
            d = 'All requests are currently in the process of being uploaded. ' \
            'Only paused uploads may be cancelled.'
            self.context.prompt.render_paragraph(_(d))
            return

        # Prompt for which upload requests to cancel
        source_filenames = [os.path.basename(u.source_filename) for u in non_running_uploads]
        q = _('Select one or more uploads to cancel: ')
        selected_indexes = self.context.prompt.prompt_multiselect_menu(q, source_filenames, interruptable=True)

        # If the user selected none or aborted (or ctrl+c), punch out
        if selected_indexes is self.context.prompt.ABORT or len(selected_indexes) is 0:
            return

        # Resolve selected uploads against their associated metadata
        selected_uploads = [u for i, u in enumerate(non_running_uploads) if i in selected_indexes]
        selected_filenames = [os.path.basename(u.source_filename) for u in selected_uploads]
        selected_ids = [u.upload_id for u in selected_uploads]

        # Try to delete as many as possible. If at least one failed, return
        # a non-happy exit code.
        error_encountered = False
        for i, upload_id in enumerate(selected_ids):
            try:
                upload_manager.delete_upload(upload_id, force=force)
                self.context.prompt.render_success_message(_('Successfully deleted %(f)s') % {'f' : selected_filenames[i]})
            except Exception, e:
                self.context.prompt.render_failure_message(_('Error deleting %(f)s') % {'f' : selected_filenames[i]})
                self.context.exception_handler.handle_exception(e)
                error_encountered = True

        if error_encountered:
            return os.EX_IOERR
        else:
            return os.EX_OK

# -- utility ------------------------------------------------------------------

def configure_upload_manager(context):
    """
    Instantiates and configures the upload manager. The context is used to
    access any necessary configuration.

    @return: initialized and ready to run upload manager instance
    @rtype:  UploadManager
    """
    upload_working_dir = context.config['filesystem']['upload_working_dir']
    upload_working_dir = os.path.expanduser(upload_working_dir)
    chunk_size = int(context.config['server']['upload_chunk_size'])
    upload_manager = upload_lib.UploadManager(upload_working_dir, context.server, chunk_size)
    upload_manager.initialize()
    return upload_manager
