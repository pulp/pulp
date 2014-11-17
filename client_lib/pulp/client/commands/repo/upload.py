from gettext import gettext as _
import os

from okaara.prompt import COLOR_GREEN, COLOR_YELLOW

from pulp.bindings.exceptions import ConflictException
from pulp.client.commands import options, polling
from pulp.client.extensions.extensions import PulpCliCommand, PulpCliFlag, PulpCliOption
from pulp.client.upload.manager import UploadManager


COLOR_RUNNING = COLOR_GREEN
COLOR_PAUSED = COLOR_YELLOW

# Command Default Descriptions
DESC_UPLOAD = _('uploads one or more units into a repository')
DESC_RESUME = _('resume a paused upload request')
DESC_LIST = _('lists in-progress and paused uploads')
DESC_CANCEL = _('cancels an outstanding upload request')

# Options
DESC_FORCE = _('removes the client-side tracking file for the upload regardless of '
               'whether or not it was able to be deleted on the server; this should '
               'only be used in the event that the server\'s knowledge of an upload '
               'has been removed')
FLAG_FORCE = PulpCliFlag('--force', DESC_FORCE)

DESC_FILE = _('full path to a file to upload; may be specified multiple times '
              'for multiple files')
OPTION_FILE = PulpCliOption('--file', DESC_FILE, aliases=['-f'], allow_multiple=True,
                            required=False)

DESC_DIR = _('full path to a directory containing files to upload; '
             'may be specified multiple times for multiple directories')
OPTION_DIR = PulpCliOption('--dir', DESC_DIR, aliases=['-d'], allow_multiple=True, required=False)

DESC_VERBOSE = _('display extra information about the upload process')
FLAG_VERBOSE = PulpCliFlag('-v', DESC_VERBOSE)


class MetadataException(Exception):
    """
    Raised by the generate_* methods to indicate the necessary unit key or
    metadata for a unit being uploaded/created could not be determined. This
    exception will be gracefully handled by the upload workflow and will print
    the provided message to the user to indicate why the metadata generation
    failed. The message should be i18n-ified before being passed into the
    exception instance.
    """

    def __init__(self, message):
        Exception.__init__(self, message)
        self.message = message

    def __str__(self):
        return self.message


class PerformUploadCommand(polling.PollingCommand):
    """
    UploadCommand and ResumeCommand both need the same perform_upload() method, but they have
    incompatible initialization so it doesn't make sense for ResumeCommand to subclass
    UploadCommand. They both subclass this class so they can get the perform_upload() method.
    """

    def perform_upload(self, context, upload_manager, upload_ids, user_input):
        """
        Uploads (resumes if necessary) uploading the given upload requests. The
        context is used to retrieve the bindings and this call will use the prompt
        to display output to the screen.

        :param context:        framework provided context
        :type  context:        PulpCliContext
        :param upload_manager: initialized upload manager instance
        :type  upload_manager: UploadManager
        :param upload_ids:     list of upload IDs to handle
        :type  upload_ids:     list
        :param user_input:     keyword arguments that were passed this this command
        :type  user_input:     dict
        """

        d = _('Starting upload of selected units. If this process is stopped through '
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
                    context.prompt.write(
                        _('Uploading: %(n)s') % {'n': os.path.basename(tracker.source_filename)})
                    bar = context.prompt.create_progress_bar()

                    def progress_callback(item, total):
                        msg = _('%(i)s/%(t)s bytes')
                        bar.render(item, total, msg % {'i': item, 't': total})

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

                self.poll([response.response_body], user_input)

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


class UploadCommand(PerformUploadCommand):
    """
    This is the PulpCLICommand that handles unit uploads to the Pulp server.
    """

    def __init__(self, context, upload_manager=None, name='upload',
                 description=DESC_UPLOAD, method=None, upload_files=True):
        """
        Extendable command for handling the process of uploading a file to
        Pulp and the UI involved in displaying the status. There are a number
        of methods a subclass may want to implement from throughout the
        workflow.

        :param context: Pulp client context
        :type  context: pulp.client.extensions.core.ClientContext
        :param upload_manager: created and configured upload manager instance
        :type  upload_manager: pulp.client.upload.manager.UploadManager
        :param upload_files: if false, the user will not be prompted for files
               to upload and the create will be purely metadata based
        :type  upload_files: bool
        """
        if upload_manager is None:
            upload_manager = UploadManager.init_with_defaults(context)

        if method is None:
            method = self.run

        super(UploadCommand, self).__init__(name, description, method, context)

        self.context = context
        self.prompt = context.prompt
        self.upload_manager = upload_manager
        self.upload_files = upload_files

        self.add_option(options.OPTION_REPO_ID)

        if upload_files:
            self.add_option(OPTION_FILE)
            self.add_option(OPTION_DIR)

        self.add_flag(FLAG_VERBOSE)

    def run(self, **user_input):
        """
        This is the main method that gets called when an upload is requested.

        :param user_input: The user provided settings
        :type  user_input: dict
        """
        self.prompt.render_title(_('Unit Upload'))

        repo_id = user_input[options.OPTION_REPO_ID.keyword]
        specified_files = user_input.get(OPTION_FILE.keyword) or []
        specified_dirs = user_input.get(OPTION_DIR.keyword) or []
        verbose = user_input.get(FLAG_VERBOSE.keyword) or False
        override_config = self.generate_override_config(**user_input)

        self._verify_repo_exists(repo_id)

        # Resolve the total list of files to upload
        all_filenames = list(specified_files)

        for d in specified_dirs:
            # Sanity check
            if not os.path.isdir(d):
                self.context.prompt.render_failure_message(
                    _('Directory %(d)s does not exist') % {'d': d})
                return os.EX_IOERR

            # Load the files in the directory
            files_in_dir = self.matching_files_in_dir(d)
            all_filenames += files_in_dir

        # Make sure at least one file was found
        if len(all_filenames) == 0 and self.upload_files:
            self.context.prompt.render_failure_message(_('No files selected for upload'))
            return os.EX_DATAERR

        # Integrity check on the total list of files
        for f in all_filenames:
            if not os.path.isfile(f) or not os.access(f, os.R_OK):
                self.context.prompt.render_failure_message(
                    _('File %(f)s does not exist or could not be read') % {'f': f})
                return os.EX_IOERR

        # Package into FileBundle DTOs
        orig_file_bundles = [FileBundle(f) for f in all_filenames]

        # Determine the metadata for each file
        self.prompt.write(_('Extracting necessary metadata for each request...'))
        bar = self.prompt.create_progress_bar()

        # If not a file-based upload, make a single request with the values
        # from the generate_* commands
        if self.upload_files:
            for i, file_bundle in enumerate(orig_file_bundles):
                filename = file_bundle.filename
                bar.render(i + 1, len(orig_file_bundles),
                           message=_('Analyzing: %(n)s') % {'n': os.path.basename(filename)})

                try:
                    unit_key, unit_metadata = self.generate_unit_key_and_metadata(filename,
                                                                                  **user_input)
                except MetadataException, e:
                    msg = _('Metadata for %(name)s could not be generated. The '
                            'specific error is as follows:')
                    msg = msg % {'name': filename}
                    self.prompt.render_spacer()
                    self.prompt.render_failure_message(msg)
                    self.prompt.render_failure_message(e.message)
                    return os.EX_DATAERR

                type_id = self.determine_type_id(filename, **user_input)
                file_bundle.type_id = type_id
                file_bundle.unit_key.update(unit_key)
                file_bundle.metadata.update(unit_metadata)
        else:
            try:
                unit_key, unit_metadata = self.generate_unit_key_and_metadata(None, **user_input)
            except MetadataException, e:
                msg = _('Metadata for the unit to create could not be generated. '
                        'The specific error is as follows:')
                self.prompt.render_spacer()
                self.prompt.render_failure_message(msg)
                self.prompt.render_failure_message(e.message)
                return os.EX_DATAERR

            type_id = self.determine_type_id(None, **user_input)
            file_bundle = FileBundle(None, type_id, unit_key, unit_metadata)
            orig_file_bundles.append(file_bundle)

        self.prompt.write(_('... completed'))
        self.prompt.render_spacer()

        # Give the subclass a chance to remove any files that shouldn't be uploaded
        file_bundles = self.create_upload_list(orig_file_bundles, **user_input)

        # Display the list of files to upload
        if verbose and self.upload_files:

            # Files that are actually being uploaded
            self.prompt.write(_('Files to be uploaded:'))
            for file_bundle in file_bundles:
                self.prompt.write('  %s' % os.path.basename(file_bundle.filename))

            # Files that were removed by the subclass
            removed_file_bundles = set(orig_file_bundles) - set(file_bundles)
            if len(removed_file_bundles) > 0:
                self.prompt.render_spacer()
                self.prompt.write(_('Skipped files:'))
                for file_bundle in removed_file_bundles:
                    self.prompt.write('  %s' % os.path.basename(file_bundle.filename))

            self.prompt.render_spacer()

        # Gracefully punch out if all files were skipped; we'll only be here if there was originally
        # one or more file specified
        if len(file_bundles) == 0:
            self.context.prompt.write(_('No files eligible for upload'))
            return os.EX_OK

        # Initialize all uploads
        self.prompt.write(_('Creating upload requests on the server...'))
        bar = self.prompt.create_progress_bar()

        upload_ids = []
        for i, file_bundle in enumerate(file_bundles):
            filename = file_bundle.filename

            if self.upload_files:
                msg = _('Initializing: %(n)s') % {'n': os.path.basename(filename)}
            else:
                msg = _('Initializing upload')

            bar.render(i + 1, len(file_bundles), message=msg)
            upload_id = self.upload_manager.initialize_upload(
                filename, repo_id, file_bundle.type_id, file_bundle.unit_key, file_bundle.metadata,
                override_config)
            upload_ids.append(upload_id)

        self.prompt.write(_('... completed'))
        self.prompt.render_spacer()

        # Start the upload process
        self.perform_upload(self.context, self.upload_manager, upload_ids, user_input)

    def matching_files_in_dir(self, directory):
        """
        Returns which files in the given directory should be uploaded. This
        should be overridden in subclasses to limit files uploaded from a
        directory to match certain file types.

        The default implementation if not overridden will return all files
        in the given directory.

        :param directory: directory in which to list files
        :type  directory: str

        :return: list of full paths of files to upload
        :rtype:  list
        """
        all_files = []
        for f in os.listdir(directory):
            filename = os.path.join(directory, f)
            if os.path.isfile(filename):
                all_files.append(filename)

        return all_files

    def determine_type_id(self, filename, **kwargs):
        """
        Returns the ID of the type of file being uploaded, used by the server
        to determine the correct plugin to handle the upload. Subclasses must
        override this method to return an appropriate value.

        :param filename: full path to the file being uploaded
        :type  filename: str:param kwargs: arguments passed into the upload call by the user
        :type  kwargs: dict

        :return: ID of the type of file being uploaded
        :rtype:  str
        """
        raise NotImplementedError()

    def generate_unit_key_and_metadata(self, filename, **kwargs):
        """
        For the given file, returns a tuple of the unit key and metadata to
        upload for the upload request. This call will aggregate calls to
        generate_unit_key and generate_metadata if not overridden, meaning
        subclasses may choose to ignore this call and simply override those.
        In the event that performance gains would be made by loading both
        at once, this call may be overridden.

        :param filename: full path to the file being uploaded
        :type  filename: str, None
        :param kwargs: arguments passed into the upload call by the user
        :type  kwargs: dict

        :return: tuple of unit key and metadata to upload for the file
        :rtype:  tuple

        :raise MetadataException: if the metadata or unit key cannot be
               properly determined for the unit being uploaded
        """
        unit_key = self.generate_unit_key(filename, **kwargs)
        metadata = self.generate_metadata(filename, **kwargs)
        return unit_key, metadata

    def generate_unit_key(self, filename, **kwargs):
        """
        For the given file, returns the unit key that should be specified in
        the upload request. Subclasses must override this method to return
        an appropriate key.

        :param filename: full path to the file being uploaded
        :type  filename: str, None
        :param kwargs: arguments passed into the upload call by the user
        :type  kwargs: dict

        :return: unit key that should be uploaded for the file
        :rtype:  dict

        :raise MetadataException: if the unit key cannot be properly determined
               for the unit being uploaded
        """
        raise NotImplementedError()

    def generate_metadata(self, filename, **kwargs):
        """
        For the given file, returns a list of metadata that should be included
        as part of the upload request. Subclasses need not override this method
        if no extra metadata is specified in the upload request.

        :param filename: full path to the file being uploaded
        :type  filename: str, None
        :param kwargs: arguments passed into the upload call by the user
        :type  kwargs: dict

        :return: metadata information that should be uploaded for the file
        :rtype:  dict

        :raise MetadataException: if the metadata cannot be properly determined
               for the unit being uploaded
        """
        return {}

    def generate_override_config(self, **kwargs):
        """
        Subclasses may override this to introduce an override config value to the upload
        command. If not overridden, an empty override config will be specified.

        :param kwargs: parsed from the user input

        :return: value to pass the upload call as its override_config parameter
        """
        return {}

    def create_upload_list(self, file_bundles, **kwargs):
        """
        Called after the metadata has been extracted for each file specified by the
        user. This method returns a list of which of those files should actually be
        uploaded, allowing the subclass a chance to remove files for whatever reason
        (likely if the subclasses wishes to check for the existence of those files
        in the server).

        In most cases, the default implementation may remain unchanged.

        :param file_bundles: list of FileBundle instances that contain the filename and
               metadata for each file to be uploaded
        :type  file_bundles: list
        :param kwargs: arguments passed into the upload call by the user
        :type  kwargs: dict

        :return: new list containing the FileBundle instances from the original file_bundles list
                 that should be uploaded
        :rtype:  list
        """
        return file_bundles

    def _verify_repo_exists(self, repo_id):
        """
        Called at the outset of an upload request, this method will ensure the
        requested repository exists on the server. If the repository does not
        exist, the missing resource exception is bubbled up.
        """
        self.context.server.repo.repository(repo_id)


class ResumeCommand(PerformUploadCommand):
    """
    Displays a list of paused uploads and allows one or more of them to be
    resumed.
    """

    def __init__(self, context, upload_manager, name='resume', description=DESC_RESUME,
                 method=None):
        """
        Initialize the ResumeCommand.

        :param context:        Pulp client context
        :type  context:        pulp.client.extensions.core.ClientContext
        :param upload_manager: created and configured upload manager instance
        :type  upload_manager: pulp.client.upload.manager.UploadManager
        :param name:           The name of the command (optional, defaults to 'resume')
        :type  name:           basestring
        :param description:    The description of the command (optional,
                               defaults to pulp.client.commands.repo.upload.DESC_RESUME)
        :type  description:    basestring
        :param method:         The method the command should run when invoked (optional, defaults to
                               pulp.client.commands.repo.upload.ResumeCommand.run)
        :type  method:         callable
        """

        if method is None:
            method = self.run

        super(ResumeCommand, self).__init__(name, description, method, context)

        self.context = context
        self.prompt = context.prompt
        self.upload_manager = upload_manager

    def run(self, **user_input):
        """
        This performs the work to resume the upload.

        :param user_input: The user specified flags
        :type  user_input: dict
        """
        self.context.prompt.render_title(_('Upload Requests'))

        # Determine which (if any) uploads are eligible to resume
        uploads = self.upload_manager.list_uploads()

        if len(uploads) == 0:
            d = _('No outstanding uploads found')
            self.context.prompt.render_paragraph(d)
            return

        non_running_uploads = [u for u in uploads if not u.is_running]
        if len(non_running_uploads) == 0:
            d = _('All requests are currently in the process of being uploaded')
            self.context.prompt.render_paragraph(d)
            return

        # Prompt the user to select one or more uploads to resume
        source_filenames = [os.path.basename(u.source_filename) for u in non_running_uploads]
        q = _('Select one or more uploads to resume: ')
        selected_indexes = self.context.prompt.prompt_multiselect_menu(q, source_filenames,
                                                                       interruptable=True)

        # User either selected no items or elected to abort (or ctrl+c)
        if selected_indexes is self.context.prompt.ABORT or len(selected_indexes) == 0:
            return

        # Resolve the user selections for display and uploading
        selected_uploads = [u for i, u in enumerate(non_running_uploads) if i in selected_indexes]
        selected_filenames = [os.path.basename(u.source_filename) for u in selected_uploads]
        selected_ids = [u.upload_id for u in selected_uploads]

        self.context.prompt.render_paragraph(
            _('Resuming upload for: %(u)s') % {'u': ', '.join(selected_filenames)})

        self.perform_upload(self.context, self.upload_manager, selected_ids, user_input)


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
        if len(uploads) == 0:
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

            # Fix for BZ 1100892 - rpm repo uploads list fails
            if upload.source_filename:
                source_name = os.path.basename(upload.source_filename)
            else:
                source_name = _('Metadata Upload')

            message = template % (state, source_name)
            self.context.prompt.write(message)

        self.context.prompt.render_spacer()


class CancelCommand(PulpCliCommand):
    """
    Displays a list of paused uploads and allows the user to select one or more
    to cancel.
    """

    def __init__(self, context, upload_manager, name='cancel', description=DESC_CANCEL,
                 method=None):

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
        if len(uploads) == 0:
            d = _('No outstanding uploads found')
            self.context.prompt.render_paragraph(d)
            return

        # We can only cancel paused uploads, so check to make sure there is
        # at least one
        non_running_uploads = [u for u in uploads if not u.is_running]
        if len(non_running_uploads) == 0:
            d = _('All requests are currently in the process of being uploaded. '
                  'Only paused uploads may be cancelled.')
            self.context.prompt.render_paragraph(d)
            return

        # Prompt for which upload requests to cancel
        source_filenames = [os.path.basename(u.source_filename) for u in non_running_uploads]
        q = _('Select one or more uploads to cancel: ')
        selected_indexes = self.context.prompt.prompt_multiselect_menu(q, source_filenames,
                                                                       interruptable=True)

        # If the user selected none or aborted (or ctrl+c), punch out
        if selected_indexes is self.context.prompt.ABORT or len(selected_indexes) == 0:
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
                self.context.prompt.render_success_message(
                    _('Successfully deleted %(f)s') % {'f': selected_filenames[i]})
            except Exception, e:
                self.context.prompt.render_failure_message(
                    _('Error deleting %(f)s') % {'f': selected_filenames[i]})
                self.context.exception_handler.handle_exception(e)
                error_encountered = True

        if error_encountered:
            return os.EX_IOERR
        else:
            return os.EX_OK


class FileBundle(object):
    """
    Holder for all information pertaining to a single file being uploaded.
    """

    def __init__(self, filename, type_id=None, unit_key=None, metadata=None):
        super(FileBundle, self).__init__()
        self.filename = filename
        self.type_id = type_id
        self.unit_key = unit_key or {}
        self.metadata = metadata or {}

    def __eq__(self, other):
        return self.filename == other.filename

    def __str__(self):
        return self.filename
