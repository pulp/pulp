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
Layer on top of the upload APIs to perform many of the common client-side tasks
around uploading a content unit, such as the ability to resume a cancelled
download, uploading a file in multiple chunks instead of a single call, and
client-side tracking of upload requests on the server.
"""

import copy
import os
import pickle
import sys

from pulp.client.lock import LockFile

# -- constants ----------------------------------------------------------------

DEFAULT_CHUNKSIZE = 1048576 # 1 MB per upload call

# -- exceptions ---------------------------------------------------------------

class ManagerUninitializedException(Exception):
    """
    Raised in the event the manager is used before it is initialized.
    """
    pass

class MissingUploadRequestException(Exception):
    """
    Raised in the event that an attempt is made on an upload request that
    does not exist, either its local tracker file or as indicated that it is
    no longer available on the server.
    """
    pass

class IncompleteUploadException(Exception):
    """
    Raised when attempting to import an upload that has not completed uploading.
    """
    pass

class ConcurrentUploadException(Exception):
    """
    Raised when attempting to start an upload that is already in progress.
    """
    pass

# -- classes ------------------------------------------------------------------

class UploadManager(object):
    """
    Provides utilities for working with Pulp's upload content unit APIs. There
    should only be one instance of this class per upload working directory (the
    location used to store upload request status files).

    Once instantiated, the initialize() method must be called before performing
    any operations are performed.

    This class' thread safety admittedly isn't the best. The intention, at least
    initially, is to be used in a CLI where there will only be a single thread
    per process. As such, there are no in memory locks. The tracker files per
    upload will carry some state information to prevent two processes from
    concurrently modifying the same tracker.

    Likewise, the working directory contents are only read once and cached. This
    will be a problem if we expect an instance to be long running (i.e. the
    interactive shell) and need to account for multiple instances of the shell
    running at once.

    In the future when we support an interactive shell interface we'll need to
    revisit and add some in memory locking and a tighter integration with the
    on disk state files.
    """

    def __init__(self, upload_working_dir, bindings, chunk_size=DEFAULT_CHUNKSIZE):
        """
        @param upload_working_dir: directory in which to store client-side files
               to track upload requests; if it doesn't exist it will be created
               during the initialize() call
        @type  upload_working_dir: str

        @param bindings: server bindings from the client context
        @type  bindings: Bindings

        @param chunk_size: size in bytes of data to upload on each call to the
               server
        @type  chunk_size: int
        """
        self.upload_working_dir = upload_working_dir
        self.bindings = bindings
        self.chunk_size = chunk_size

        # Internal state
        self.tracker_files = {}
        self.is_initialized = False

    def initialize(self):
        """
        Must be called prior to using the manager. This call prepares the
        working directory and loads any tracker files it finds. See the
        class level docs for more information on loading those files in a
        multiple process environment.
        """

        # Create the working directory if it doesn't exist
        if not os.path.exists(self.upload_working_dir):
            os.makedirs(self.upload_working_dir)

        # Load all tracker files from the working directory
        for filename in os.listdir(self.upload_working_dir):
            full_filename = os.path.join(self.upload_working_dir, filename)
            tracker_file = UploadTracker.load(full_filename)
            self.tracker_files[tracker_file.upload_id] = tracker_file

        self.is_initialized = True

    def initialize_upload(self, filename, repo_id, unit_type_id, unit_key, unit_metadata):
        """
        Called at the outset of a new upload request. This call requests the
        server create a new upload request to be able to upload bits to it.
        The parameters provided to this call are stored client-side and will
        be sent to the server once the upload itself has completed as part of
        the import_upload call.

        @param filename: full path to the file on disk to upload
        @type  filename: str

        @param repo_id: identifies the repository into which the unit is uploaded
        @type  repo_id: str

        @param unit_type_id: identifies the type of unit being uploaded
        @type  unit_type_id: str

        @param unit_key: unique key for the uploaded unit; contents will vary
               based on content type
        @type  unit_key: dict

        @param unit_metadata: any metadata about the unit to pass to the importer
               when importing the unit; what is done with these values is up to
               the importer's implementation

        @return: upload ID used to identify this upload request in future calls
        """
        self._verify_initialized()

        response = self.bindings.uploads.initialize_upload().response_body

        upload_id = response['upload_id']
        location = response['_href']

        # Build up the tracker file to track this upload
        tracker_filename = self._tracker_filename(upload_id)
        tracker_file = UploadTracker(tracker_filename)
        tracker_file.upload_id = upload_id
        tracker_file.location = location
        tracker_file.offset = 0
        tracker_file.repo_id = repo_id
        tracker_file.unit_type_id = unit_type_id
        tracker_file.unit_key = unit_key
        tracker_file.unit_metadata = unit_metadata
        tracker_file.source_filename = filename

        # Save the tracker file to disk
        tracker_file.save()

        # Add to in memory cache
        self._cache_tracker_file(tracker_file)

        return upload_id

    def upload(self, upload_id, callback_func=None, force=False):
        """
        Begins or resumes the upload process for the given upload request.
        This call will not return until the upload is complete. The other
        expected exit point is a KeyboardError to kill the process. The
        client-side on disk tracker files will store the current offset and
        resume the upload from where it left off on the next call to this method.

        The callback_func is used to get feedback on the upload process. After
        each successful upload segment call to the server, this function
        will be invoked with the new offset in the file and the file size
        (intended to be fed into a progress indicator). As this is called
        after each upload segment call, the granularity at which it is called
        depends on the chunk_size value for this instance.

        The callback_func should have a signature of (int, int).

        This call will raise an exception if an upload is already in progress
        for the given upload_id. If that isn't the case and the tracker file's
        running flag is stale, the force parameter will bypass this check and
        start the upload anyway.

        @param upload_id: identifies the upload request
        @type  upload_id: str

        @param callback_func: optional method to be called after each upload
               call to the server
        @type  callback_func: func

        @param force: if true will bypass the running check to prevent concurrent
               uploads
        @type  force: bool

        @raise MissingUploadRequestException: if a tracker file for upload_id
               cannot be found
        @raise ConcurrentUploadException: if an upload is already in progress
               for upload_id
        """
        self._verify_initialized()

        tracker_file = self._get_tracker_file_by_id(upload_id)

        if tracker_file is None:
            raise MissingUploadRequestException()

        # If the tracker state gets into a bad place, the caller can force it
        # to upload anyway.
        if not force and tracker_file.is_running:
            raise ConcurrentUploadException()

        try:
            # Flag the upload request as running so other processes don't
            # attempt to run it as well
            tracker_file.is_running = True
            tracker_file.save()

            source_file_size = os.path.getsize(tracker_file.source_filename)

            f = open(tracker_file.source_filename, 'r')
            while True:
                # Load the chunk to upload
                f.seek(tracker_file.offset)
                data = f.read(self.chunk_size)
                if not data:
                    break

                # Server request
                self.bindings.uploads.upload_segment(upload_id, tracker_file.offset, data)

                # Status update and callback notification
                tracker_file.offset = min(tracker_file.offset + self.chunk_size, source_file_size)
                tracker_file.save()

                callback_func(tracker_file.offset, source_file_size)

            tracker_file.is_finished_uploading = True
        finally:
            # Regardless of how this ends, it's no longer running, so make sure
            # we update the tracker accordingly.
            tracker_file.is_running = False
            tracker_file.save()

    def import_upload(self, upload_id):
        """
        Once the file is finished uploading, this call will request the server
        import the upload. The data provided during initialize_upload is sent
        with the call. The server may raise an exception if the import fails
        for some reason.

        @param upload_id: identifies the upload request to import
        @type  upload_id: str

        @raise MissingUploadRequestException: if there is no tracker file for
               the given upload_id
        @raise IncompleteUploadException: if the tracker file indicates the
               upload has not completed
        """
        self._verify_initialized()

        tracker = self._get_tracker_file_by_id(upload_id)
        if tracker is None:
            raise MissingUploadRequestException()

        if not tracker.is_finished_uploading:
            raise IncompleteUploadException()

        response = self.bindings.uploads.import_upload(upload_id, tracker.repo_id,
                   tracker.unit_type_id, tracker.unit_key, tracker.unit_metadata)

        return response

    def list_uploads(self):
        """
        Returns all upload requests known to this instance.

        @return: list of UploadTracker instances
        @rtype:  list
        """
        self._verify_initialized()

        cached_trackers = self._all_tracker_files()
        copies = [copy.copy(t) for t in cached_trackers] # copy for safety
        return copies

    def get_upload(self, upload_id):
        """
        Returns a copy of the upload tracker for the given ID.

        @param upload_id: upload to return
        @type  upload_id: str

        @return: copy of the upload tracker if it exists; None otherwise
        @rtype:  UploadTracker
        """
        tracker = self._get_tracker_file_by_id(upload_id)
        if tracker:
            tracker = copy.copy(tracker) # copy for safety
        return tracker

    def delete_upload(self, upload_id, force=False):
        """
        Deletes the given upload request. Deleting a request is done both
        on the server and the client-side tracking file. The server step is
        performed first. If it fails, the client-side tracking file is not
        deleted. If the server is in a weird state and the client-side
        tracker still needs to be deleted, the force flag can be specified to
        perform the client-side clean up regardless of the server response.

        @param upload_id: identifies the upload request
        @type  upload_id: str

        @param force: if true, delete the client-side knowledge of the upload
               regardles of the server's response.
        @type  force: bool
        """
        self._verify_initialized()

        tracker = self._get_tracker_file_by_id(upload_id)
        if tracker is None:
            raise MissingUploadRequestException()

        if not force and tracker.is_running:
            raise ConcurrentUploadException()

        # Try to delete the server side upload first. If that fails, the force
        # option can be used to delete the client side trackre anyway.
        try:
            response = self.bindings.uploads.delete_upload(upload_id)
        except Exception, e:
            # Only raise the server side exception on a force
            if not force:
                raise e, None, sys.exc_info()[2]

        # Client Side Clean Up
        self._uncache_tracker_file(tracker)
        tracker.delete()

    # -- tracker utilities ----------------------------------------------------

    def _tracker_filename(self, upload_id):
        return os.path.join(self.upload_working_dir, upload_id)

    def _cache_tracker_file(self, tracker_file):
        self.tracker_files[tracker_file.upload_id] = tracker_file

    def _uncache_tracker_file(self, tracker_file):
        self.tracker_files.pop(tracker_file.upload_id, None)

    def _get_tracker_file_by_id(self, upload_id):
        return self.tracker_files.get(upload_id, None)

    def _all_tracker_files(self):
        return self.tracker_files.values()

    # -- misc utility ---------------------------------------------------------

    def _verify_initialized(self):
        if not self.is_initialized:
            raise ManagerUninitializedException()

class UploadTracker(object):
    """
    Client-side file to carry all information related to a single upload
    request on the server.
    """

    def __init__(self, filename):
        self.filename = filename # filename of the tracker file itself

        # Upload call information
        self.upload_id = None
        self.location = None # URL to the upload request on the server
        self.offset = None # start of next chunk to upload
        self.source_filename = None # path on disk to the file to upload

        # Import call information
        self.repo_id = None
        self.unit_type_id = None
        self.unit_key = None
        self.unit_metadata = None

        # State information
        self.is_running = False
        self.is_finished_uploading = False

    def save(self):
        """
        Saves the current state of the tracker file. This will lock on the file
        to prevent multiple processes from editing it at once, even though that
        probably won't happen if the above code for upload works correctly.
        """

        # Can't lock if it doesn't exist, but this should be good enough. The
        # filenames are UUIDs and should be reasonably unique, so the chance
        # that two files with the same name are saved for the first time is
        # really remote.
        lock_file = None
        if os.path.exists(self.filename):
            lock_file = LockFile(self.filename)
            lock_file.acquire()

        f = open(self.filename, 'w')
        pickle.dump(self, f)
        f.close()

        if lock_file:
            lock_file.release()

    def delete(self):
        os.remove(self.filename)

    @classmethod
    def load(cls, filename):
        """
        Loads the given tracker file. The file must exist and be readable; the
        caller should ensure that before loading.

        @return: tracker instance
        @rtype:  UploadTracker
        """
        f = open(filename, 'r')
        status_file = pickle.load(f)
        f.close()

        return status_file
