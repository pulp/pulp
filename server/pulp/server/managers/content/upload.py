from errno import ENOENT
from gettext import gettext as _
import logging
import os
import sys
from uuid import uuid4

from celery import task

from pulp.plugins.conduits.upload import UploadConduit
from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.loader import api as plugin_api, exceptions as plugin_exceptions
from pulp.server import config as pulp_config
from pulp.server.async.tasks import Task
from pulp.server.db import model
from pulp.server.exceptions import (PulpDataException, MissingResource, PulpExecutionException,
                                    PulpException)
import pulp.server.managers.factory as manager_factory


logger = logging.getLogger(__name__)


class ContentUploadManager(object):
    def initialize_upload(self):
        """
        Informs the Pulp server that a new file is about to be uploaded, allowing
        it to do any preparation it needs to do to store or track the upload.

        The ID returned from this call is used to track this specific uploaded
        file for the remainder of its life.

        @return: unique ID to refer to this upload request in the future
        @rtype:  str
        """

        # Eventually I can see this method keeping track of uploads in the
        # database so a user can later query the server to find incomplete
        # uploaded files, stats on usage of existing uploaded files, and a
        # way to know which should be deleted to clean up.

        upload_id = str(uuid4())

        # Initialize the file, the main benefit being that if the server cannot
        # write to the file path we will find out now and bomb on the initialize
        # before attempting to write bits.
        file_path = ContentUploadManager._upload_file_path(upload_id)
        f = open(file_path, 'w')
        f.close()

        return upload_id

    def save_data(self, upload_id, offset, data):
        """
        Saves bits into the given upload request starting at an offset value.
        The initialize_upload method should be called prior to this method
        to retrieve the upload_id value and perform any steps necessary before
        bits can be saved.

        @param upload_id: upload request ID
        @type  upload_id: str

        @param offset: area in the uploaded file to start writing at
        @type  offset: int

        @param data: content to write to the file
        @type  data: str
        """

        file_path = ContentUploadManager._upload_file_path(upload_id)

        # Make sure the upload was initialized first and hasn't been deleted
        if not os.path.exists(file_path):
            raise MissingResource(upload_request=upload_id)

        f = open(file_path, 'r+')
        f.seek(offset)
        f.write(data)
        f.close()

    def delete_upload(self, upload_id):
        """
        Deletes all files associated with the given upload request. If the
        upload request does not exist or has already been deleted, this call
        will raise MissingResource.

        @param upload_id: upload request ID
        @type  upload_id: str

        @raise MissingResource: if the upload request ID does not exist
        """

        file_path = ContentUploadManager._upload_file_path(upload_id)
        try:
            os.remove(file_path)
        except OSError as e:
            if e.errno != ENOENT:
                raise

    def read_upload(self, upload_id):
        """
        Utility method for reading and returning the contents of an upload
        request. This is preferred to getting the file path and reading it
        directly in case the implementation changes to supported multiple
        segmented files per upload.

        This call is meant for testing purposes only and shouldn't be used
        for large files.

        @param upload_id: upload request ID
        @type  upload_id: str

        @return: contents of the uploaded file
        @rtype:  str
        """

        file_path = ContentUploadManager._upload_file_path(upload_id)
        f = open(file_path)
        contents = f.read()
        f.close()

        return contents

    def list_upload_ids(self):
        """
        Returns a list of IDs for all in progress uploads.

        @return: list of IDs
        @rtype:  list
        """
        upload_dir = ContentUploadManager._upload_storage_dir()
        upload_ids = os.listdir(upload_dir)
        return upload_ids

    @staticmethod
    def is_valid_upload(repo_id, unit_type_id):
        """
        Checks that the repository is configured to handle an upload request
        for the given unit type ID. This should be called prior to beginning
        the upload to prevent a wasted effort in the bits uploading.

        :param repo_id:         identifies the repo into which the unit is being uploaded
        :param unit_type_id:    type of unit being uploaded
        :return:                true if the repository can attempt to handle the unit
        :rtype:                 bool
        :raise MissingResource: if the repository or its importer do not exist
        """

        importer_manager = manager_factory.repo_importer_manager()

        # Will raise an appropriate exception if it cannot be found
        repo_importer = importer_manager.get_importer(repo_id)

        # Make sure the importer on the repo can support the indicated type
        importer_types = plugin_api.list_importer_types(repo_importer['importer_type_id'])['types']

        if unit_type_id not in importer_types:
            raise PulpDataException('Invalid unit type for repository')

        return True

    @staticmethod
    def import_uploaded_unit(repo_id, unit_type_id, unit_key, unit_metadata, upload_id,
                             override_config=None):
        """
        Called to trigger the importer's handling of an uploaded unit. This
        should not be called until the bits have finished uploading. The
        importer is then responsible for moving the file to the correct location,
        adding it to the Pulp server's inventory, and associating it with the
        repository.

        This call will first call is_valid_upload to check the integrity of the
        destination repository. See that method's documentation for exception
        possibilities.

        :param repo_id:       identifies the repository into which the unit is uploaded
        :type  repo_id:       str
        :param unit_type_id:  type of unit being uploaded
        :type  unit_type_id:  str
        :param unit_key:      unique identifier for the unit (user-specified)
        :type  unit_key:      dict
        :param unit_metadata: any user-specified information about the unit
        :type  unit_metadata: dict
        :param upload_id:     upload being imported
        :type  upload_id:     str
        :return:              A SyncReport indicating the success or failure of the upload
        :rtype:               pulp.plugins.model.SyncReport
        """
        # If it doesn't raise an exception, it's good to go
        ContentUploadManager.is_valid_upload(repo_id, unit_type_id)
        importer_manager = manager_factory.repo_importer_manager()
        repo_obj = model.Repository.objects.get_repo_or_missing_resource(repo_id)
        repo_importer = importer_manager.get_importer(repo_id)

        try:
            importer_instance, plugin_config = plugin_api.get_importer_by_id(
                repo_importer['importer_type_id'])
        except plugin_exceptions.PluginNotFound:
            raise MissingResource(repo_id), None, sys.exc_info()[2]

        # Assemble the data needed for the import
        conduit = UploadConduit(repo_id, repo_importer['id'])

        call_config = PluginCallConfiguration(plugin_config, repo_importer['config'],
                                              override_config)
        transfer_repo = repo_obj.to_transfer_repo()

        file_path = ContentUploadManager._upload_file_path(upload_id)

        # Invoke the importer
        try:
            return importer_instance.upload_unit(transfer_repo, unit_type_id, unit_key,
                                                 unit_metadata, file_path, conduit, call_config)
        except PulpException:
            msg = _('Error from the importer while importing uploaded unit to repository [%(r)s]')
            msg = msg % {'r': repo_id}
            logger.exception(msg)
            raise
        except Exception, e:
            msg = _('Error from the importer while importing uploaded unit to repository [%(r)s]')
            msg = msg % {'r': repo_id}
            logger.exception(msg)
            raise PulpExecutionException(e), None, sys.exc_info()[2]

        # TODO: Add support for tracking the report as a history entry on the repo

    @staticmethod
    def _upload_file_path(upload_id):
        """
        Returns the full path to the file backing the given upload.

        :param upload_id: identifies the upload in question
        :type  upload_id: str
        :return:          full path on the server's filesystem
        :rtype:           str
        """
        upload_storage_dir = ContentUploadManager._upload_storage_dir()
        path = os.path.join(upload_storage_dir, upload_id)
        return path

    @staticmethod
    def _upload_storage_dir():
        """
        Calculates the location of the directory into which to store uploaded
        files. This is necessary as a dynamic call so unit tests have the
        opportunity to change the constants entry for local storage.

        This call will create the directory if it doesn't exist.

        :return: full path to the upload directory
        """
        storage_dir = pulp_config.config.get('server', 'storage_dir')
        upload_storage_dir = os.path.join(storage_dir, 'uploads')

        if not os.path.exists(upload_storage_dir):
            os.makedirs(upload_storage_dir)

        return upload_storage_dir


import_uploaded_unit = task(ContentUploadManager.import_uploaded_unit, base=Task)
