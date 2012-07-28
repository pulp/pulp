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
Utilities for rendering a consistent UI on top of the UploadManager.
"""

from gettext import gettext as _
import os

from pulp.bindings.exceptions import ConflictException

def perform_upload(context, upload_manager, upload_ids):
    """
    Uploads (resumes if necessary) uploading the given upload requests. The
    context is used to retrieve the bindings and this call will use the prompt
    to display output to the screen.

    @param context: framework provided context
    @type  context: PulpCliContext

    @param upload_manager: initialized upload manager instance
    @type  upload_manager: UploadManager

    @param upload_ids: list of upload IDs to handle
    @type  upload_ids: list
    """

    d = 'Starting upload of selected packages. If this process is stopped through '\
        'ctrl+c, the uploads will be paused and may be resumed later using the '\
        'resume command or cancelled entirely using the cancel command.'
    context.prompt.render_paragraph(_(d))

    # Upload and import each upload. The try block is inside of the loop to
    # allow uploads to continue even if one hits an exception. The exception
    # handler is called directly to use the standard logging/display for
    # exceptions but otherwise the next upload is allowed. The only variation
    # is that a KeyboardInterrupt represents pausing the upload process.
    for upload_id in upload_ids:
        try:
            tracker = upload_manager.get_upload(upload_id)
            if tracker.source_filename:
                # Upload the bits
                context.prompt.write(_('Uploading: %(n)s') % {'n' : os.path.basename(tracker.source_filename)})
                bar = context.prompt.create_progress_bar()

                def progress_callback(item, total):
                    msg = _('%(i)s/%(t)s bytes')
                    bar.render(item, total, msg % {'i' : item, 't' : total})

                upload_manager.upload(upload_id, progress_callback)

                context.prompt.write(_('... completed'))
                context.prompt.render_spacer()

            # Import the upload request
            context.prompt.write(_('Importing into the repository...'))

            # If the import fails due to a conflict, this call will bubble up
            # the appropriate exception to the middleware. It's best to let
            # this bubble up as there's no reason to process any more uploads
            # in the list; if one conflicted and this call is scoped to a
            # particular repo, there's no reason to bother with the others as
            # they will fail too.
            try:
                response = upload_manager.import_upload(upload_id)
            except ConflictException:
                upload_manager.delete_upload(upload_id, force=True)
                raise

            if response.is_async():
                msg = 'Import postponed due to queued operations against the '\
                      'repository. The progress of this import can be viewed in the '\
                      'repository tasks list.'
                context.prompt.render_warning_message(_(msg))

                # Do not delete the upload here; we need it lying around for
                # when the import is completed
            else:
                context.prompt.write(_('... completed'))
                context.prompt.render_spacer()

                # Delete the request
                context.prompt.write(_('Deleting the upload request...'))
                upload_manager.delete_upload(upload_id)
                context.prompt.write(_('... completed'))
                context.prompt.render_spacer()

        except KeyboardInterrupt:
            d = 'Uploading paused'
            context.prompt.render_paragraph(_(d))
            return

        except Exception, e:
            context.exception_handler.handle_exception(e)
