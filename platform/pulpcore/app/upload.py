import hashlib
from django.core.files.uploadhandler import TemporaryFileUploadHandler
from django.core.files.uploadedfile import TemporaryUploadedFile


class PulpTemporaryUploadedFile(TemporaryUploadedFile):
    """
    A file uploaded to a temporary location in Pulp.
    """

    def __init__(self, name, content_type, size, charset, content_type_extra=None):
        self.hashers = {}
        for hasher in hashlib.algorithms_guaranteed:
            self.hashers[hasher] = getattr(hashlib, hasher)()
        super().__init__(name, content_type, size, charset, content_type_extra)


class HashingFileUploadHandler(TemporaryFileUploadHandler):
    """
    Upload handler that streams data into a temporary file.
    """

    def new_file(self, field_name, file_name, content_type, content_length, charset=None,
                 content_type_extra=None):
        """
        Signal that a new file has been started.

        Args:
            field_name (str): Name of the model field that this file is associated with. This
                value is not used by this implementation of TemporaryFileUploadHandler.
            file_name (str): Name of file being uploaded.
            content_type (str): Type of file
            content_length (int): Size of the file being stored. This value is not used by this
                implementation of TemporaryFileUploadHandler.
            charset (str):
        """
        self.field_name = field_name
        self.content_length = content_length
        self.file = PulpTemporaryUploadedFile(file_name, content_type, 0, charset,
                                              content_type_extra)

    def receive_data_chunk(self, raw_data, start):
        self.file.write(raw_data)
        for hasher in hashlib.algorithms_guaranteed:
            self.file.hashers[hasher].update(raw_data)

