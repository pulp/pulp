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

from pulp.bindings.exceptions import ConflictException
from pulp.client.commands import options
from pulp.client.extensions.extensions import PulpCliCommand, PulpCliFlag, PulpCliOption

# -- constants ----------------------------------------------------------------

COLOR_RUNNING = COLOR_GREEN
COLOR_PAUSED = COLOR_YELLOW

# Command Default Descriptions
DESC_UPLOAD = _('uploads one or more puppet modules into a repository')
DESC_RESUME = _('resume a paused upload request')
DESC_LIST = _('lists in progress and paused uploads')
DESC_CANCEL = _('cancels an outstanding upload request')

# Options
DESC_FORCE = _('removes the client-side tracking file for the upload regardless of '
    'whether or not it was able to be deleted on the server; this should '
    'only be used in the event that the server\'s knowledge of an upload '
    'has been removed')
FLAG_FORCE = PulpCliFlag('--force', DESC_FORCE)

DESC_FILE = _('full path to file to upload; may be specified multiple times '
              'for multiple files')
OPTION_FILE = PulpCliOption('--file', DESC_FILE, aliases=['-f'], allow_multiple=True, required=False)

DESC_DIR = _('full path to a directory containing files to upload; '
             'may be specified multiple times for multiple directories')
OPTION_DIR = PulpCliOption('--dir', DESC_DIR, aliases=['-d'], allow_multiple=True, required=False)

DESC_VERBOSE = _('display extra information about the upload process')
FLAG_VERBOSE = PulpCliFlag('-v', DESC_VERBOSE)

# -- commands -----------------------------------------------------------------

class UploadCommand(PulpCliCommand):

    def __init__(self, context, upload_manager, name='upload',
                 description=DESC_UPLOAD, method=None):

        if method is None:
            method = self.run

        super(UploadCommand, self).__init__(name, description, method)

        self.context = context
        self.prompt = context.prompt
        self.upload_manager = upload_manager

        self.add_option(options.OPTION_REPO_ID)
        self.add_option(OPTION_FILE)
        self.add_option(OPTION_DIR)
        self.add_flag(FLAG_FORCE)
        self.add_flag(FLAG_VERBOSE)

    def run(self, **kwargs):
        self.prompt.render_title(_('Puppet Module Upload'))

        repo_id = kwargs[options.OPTION_REPO_ID.keyword]
        specified_files = kwargs.pop(OPTION_FILE.keyword) or []
        specified_dirs = kwargs.pop(OPTION_DIR.keyword) or []
        verbose = kwargs.pop(FLAG_VERBOSE.keyword) or False

        # Resolve the total list of files to upload
        all_filenames = list(specified_files)

        for d in specified_dirs:
            # Sanity check
            if not os.path.exists(d):
                self.context.prompt.render_failure_message(_('Directory %(d)s does not exist') % {'d' : d})
                return os.EX_IOERR

            # Load the files in the directory
            files_in_dir = self.matching_files_in_dir(d)
            all_filenames += files_in_dir

        # Make sure at least one file was found
        if len(all_filenames) is 0:
            self.context.prompt.render_failure_message(_('No files selected for upload'))
            return os.EX_DATAERR

        # Integrity check on the total list of files
        for f in all_filenames:
            if not os.path.exists(f) or not os.access(f, os.R_OK):
                self.context.prompt.render_failure_message(_('File %(f)s does not exist or could not be read') % {'f' : f})
                return os.EX_IOERR
            if not os.path.isfile(f):
                self.context.prompt.render_failure_message(_('%(f)s is not a file') % {'f' : f})
                return os.EX_IOERR

        # Display the list of found files
        if verbose:
            self.prompt.write(_('Files to be uploaded:'))
            for r in all_filenames:
                self.prompt.write('  %s' % os.path.basename(r))
            self.prompt.render_spacer()

        # Package into tuples of (filename, type_id, unit key, metadata)
        file_tuples = [ [f, None, {}, {}] for f in all_filenames]

        # Determine the metadata for each file
        self.prompt.write(_('Extracting necessary metdata for each file...'))
        bar = self.prompt.create_progress_bar()

        for i, file_tuple in enumerate(file_tuples):
            filename = file_tuple[0]
            bar.render(i+1, len(file_tuples), message=_('Analyzing: %(n)s') % {'n' : os.path.basename(filename)})

            file_tuple[1] = self.determine_type_id(filename, **kwargs)
            file_tuple[2].update(self.generate_unit_key(filename, **kwargs))
            file_tuple[3].update(self.generate_metadata(filename, **kwargs))

        self.prompt.write(_('... completed'))
        self.prompt.render_spacer()

        # Initialize all uploads
        self.prompt.write(_('Creating upload requests on the server...'))
        bar = self.prompt.create_progress_bar()

        upload_ids = []
        for i, job in enumerate(file_tuples):
            filename = job[0]
            type_id  = job[1]
            unit_key = job[2]
            metadata = job[3]

            bar.render(i+1, len(file_tuples), message=_('Initializing: %(n)s') % {'n' : os.path.basename(filename)})
            upload_id = self.upload_manager.initialize_upload(filename, repo_id, type_id, unit_key, metadata)
            upload_ids.append(upload_id)

        self.prompt.write(_('... completed'))
        self.prompt.render_spacer()

        # Start the upload process
        perform_upload(self.context, self.upload_manager, upload_ids)

    def matching_files_in_dir(self, dir):
        """
        Returns which files in the given directory should be uploaded. This
        should be overridden in subclasses to limit files uploaded from a
        directory to match certain file types.

        The default implementation if not overridden will return all files
        in the given directory.

        :param dir: directory in which to list files
        :type  dir: str

        :return: list of full paths of files to upload
        :rtype:  list
        """
        all_files = []
        for f in os.listdir(dir):
            if os.path.isfile(f):
                filename = os.path.join(dir, f)
                all_files.append(filename)

        return all_files

    def determine_type_id(self, filename, **kwargs):
        """
        Returns the ID of the type of file being uploaded, used by the server
        to determine the correct plugin to handle the upload. Subclasses must
        override this method to return an appropriate value.

        :param filename: full path to the file being uploaded
        :type  filename: str
        :param kwargs: arguments passed into the upload call by the user
        :type  kwargs: dict

        :return: ID of the type of file being uploaded
        :rtype:  str
        """
        raise NotImplementedError()

    def generate_unit_key(self, filename, **kwargs):
        """
        For the given file, returns the unit key that should be specified in
        the upload request. Subclasses must override this method to return
        an appropriate key.

        :param filename: full path to the file being uploaded
        :type  filename: str
        :param kwargs: arguments passed into the upload call by the user
        :type  kwargs: dict

        :return: unit key that should be uploaded for the file
        :rtype:  dict
        """
        raise NotImplementedError()

    def generate_metadata(self, filename, **kwargs):
        """
        For the given file, returns a list of metadata that should be included
        as part of the upload request. Subclasses need not override this method
        if no extra metadata is specified in the upload request.

        :param filename: full path to the file being uploaded
        :type  filename: str
        :param kwargs: arguments passed into the upload call by the user
        :type  kwargs: dict

        :return: metadata information that should be uploaded for the file
        :rtype:  dict
        """
        return {}


class ResumeCommand(PulpCliCommand):
    """
    Displays a list of paused uploads and allows one or more of them to be
    resumed.
    """

    def __init__(self, context, upload_manager, name='resume', description=DESC_RESUME, method=None):

        if method is None:
            method = self.run

        PulpCliCommand.__init__(self, name, description, method)

        self.context = context
        self.prompt = context.prompt
        self.upload_manager = upload_manager

    def run(self):
        self.context.prompt.render_title(_('Upload Requests'))

        # Determine which (if any) uploads are eligible to resume
        uploads = self.upload_manager.list_uploads()

        if len(uploads) is 0:
            d = _('No outstanding uploads found')
            self.context.prompt.render_paragraph(d)
            return

        non_running_uploads = [u for u in uploads if not u.is_running]
        if len(non_running_uploads) is 0:
            d = _('All requests are currently in the process of being uploaded')
            self.context.prompt.render_paragraph(d)
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

        perform_upload(self.context, self.upload_manager, selected_ids)


class ListCommand(PulpCliCommand):
    """
    Lists all upload requests, including their status of running v. paused.
    """

    def __init__(self, context, upload_manager, name='list', description=DESC_LIST, method=None):

        if method is None:
            method = self.run

        PulpCliCommand.__init__(self, name, description, method)

        self.context = context
        self.prompt = context.prompt
        self.upload_manager = upload_manager

    def run(self, **kwargs):
        self.context.prompt.render_title(_('Upload Requests'))

        # Load upload request trackers
        uploads = self.upload_manager.list_uploads()

        # Punch out early if there are none
        if len(uploads) is 0:
            d = _('No outstanding uploads found')
            self.context.prompt.render_paragraph(d)
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

    def __init__(self, context, upload_manager, name='cancel', description=DESC_CANCEL, method=None):

        if method is None:
            method = self.run

        PulpCliCommand.__init__(self, name, description, method)

        self.context = context
        self.prompt = context.prompt
        self.upload_manager = upload_manager

    def run(self, **kwargs):
        self.context.prompt.render_title(_('Upload Requests'))

        force = kwargs.pop(FLAG_FORCE.keyword, False)

        # Load all requests
        uploads = self.upload_manager.list_uploads()

        # Punch out early if there are no requests we can act on
        if len(uploads) is 0:
            d = _('No outstanding uploads found')
            self.context.prompt.render_paragraph(d)
            return

        # We can only cancel paused uploads, so check to make sure there is
        # at least one
        non_running_uploads = [u for u in uploads if not u.is_running]
        if len(non_running_uploads) is 0:
            d = _('All requests are currently in the process of being uploaded. '
                  'Only paused uploads may be cancelled.')
            self.context.prompt.render_paragraph(d)
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
                self.upload_manager.delete_upload(upload_id, force=force)
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

    d = _('Starting upload of selected packages. If this process is stopped through '
         'ctrl+c, the uploads will be paused and may be resumed later using the '
         'resume command or cancelled entirely using the cancel command.')
    context.prompt.render_paragraph(d)

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
                msg = _('Import postponed due to queued operations against the '
                        'repository. The progress of this import can be viewed in the '
                        'repository tasks list.')
                context.prompt.render_warning_message(msg)

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
            d = _('Uploading paused')
            context.prompt.render_paragraph(d)
            return

        except Exception, e:
            context.exception_handler.handle_exception(e)
