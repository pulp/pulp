import os
import errno
import io
import stat

from datetime import datetime
from uuid import uuid4

from django.conf import settings
from django.core.files import File
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible


class FileContent(File):
    """
    An in-memory file.
    Designed to be used by FileField when content is known.

    Attributes:
        content (str): The actual content.

    Examples:
        >>>
        >>> from django.db import models
        >>>
        >>> class Person(models.Model):
        >>>     ssl_certificate = models.FileField()
        >>>
        >>> person = Person()
        >>> certificate = 'PEM ENCODED CERTIFICATE HERE'
        >>> person.ssl_certificate = FileContent(certificate)
        >>>
    """

    def __init__(self, content):
        """
        Args:
            content (str): The file content.

        Notes:
            The name is set to '-' to ensure that model.FileField
            will work properly.  Using '-' is arbitrary and just need to
            something other than None or ''.
        """
        super(FileContent, self).__init__(io.StringIO(content), '-')
        self.content = content
        self.size = len(content)

    def open(self, mode='r'):
        """
        Open for reading.

        Args:
            mode (str): See: open() mode.
        """
        if 'b' in mode:
            self.file = io.BytesIO(bytearray(self.content, encoding='utf8'))
        else:
            self.file = io.StringIO(self.content)

    def __bool__(self):
        return len(self.content) > 0


@deconstructible
class TLSLocation:
    """
    Determine storage location (path) for PEM encoded TLS keys and certificates
    associated with any model.

    Attributes:
        name (str): The file name.
    """

    MEDIA_TYPE = 'tls'

    def __init__(self, name):
        """
        Args:
            name (str): The file name.
        """
        self.name = name

    def __call__(self, model, name):
        """
        Determine storage location as: MEDIA_ROOT/tls/<model>/<id>/<name>.

        Args:
            model (pulpcore.app.models.Model): The model object.
            name (str): The (unused) input file path.

        Returns:
            str: An absolute (base) path
        """
        return os.path.join(
            settings.MEDIA_ROOT,
            self.MEDIA_TYPE,
            type(model).__name__,
            str(model.id),
            self.name)


class FileSystem(Storage):
    """
    Provides simplified filesystem storage.
    The django filesystem storage is overly complex and makes incompatible assumptions
    and has incompatible behaviors with regard to how final storage paths are calculated.
    """

    @staticmethod
    def unlink(path):
        """
        Delete the link at the specified path.
        No exception is raised if the link does not exist.

        Args:
            path (str): Path to unlink.

        Raises:
            OSError: On error.
        """
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass

    @staticmethod
    def copy(path, content):
        """
        Atomic copy of the content into storage.
        The content copied into a temporary file, then renamed.
        This prevents creating partial files.

        Args:
            path(str): The storage path.
            content (File): Source file object.

        Raises:
            FileExistsError: File already stored.
            OSError: On error.
        """
        tmp_path = '.'.join((path, str(uuid4()), 'tmp'))
        try:
            with open(tmp_path, 'wb+') as fp:
                while True:
                    bfr = content.read(1024000)
                    if bfr:
                        fp.write(bfr)
                    else:
                        break
            os.link(tmp_path, path)
        finally:
            FileSystem.unlink(tmp_path)

    @staticmethod
    def delete_empty_dirs(path, root):
        """
        Delete empty directories in the specified path.

        Args:
            path (str): An absolute path to directory to delete
            root (str): An absolute path to directory which should not be removed even if empty
        """
        if root == path:
            return
        try:
            os.rmdir(path)
        except OSError as e:
            if e.errno in [errno.ENOENT, errno.ENOTEMPTY]:
                return
            else:
                raise
        else:
            dir_up = os.path.dirname(path)
            FileSystem.delete_empty_dirs(dir_up, root)

    @staticmethod
    def _open(path, mode='rb'):
        """
        Open the file at the specified path.
        Required by the Storage API.

        Args:
            path (str): Absolute path to a file.
            mode (str): open mode.  Default: 'rb'.

        Returns:
            File: An open file object.
        """
        return File(open(path, mode))

    @staticmethod
    def _save(path, content):
        """
        Save the content of a file to the specified path.
        The directory tree is created as needed.  The file is linked when possible.
        Required by the Storage API.  An existing file will not be overwritten.

        Args:
            path (str): Target path to which the file is copied.
            content (File): Source file object.

        Returns:
            str: Final storage path.
        """
        os.makedirs(os.path.dirname(path), exist_ok=True)

        try:
            try:
                os.link(content.name, path)
            except OSError as e:
                if e.errno in (errno.EXDEV, errno.ENOENT):
                    FileSystem.copy(path, content)
                else:
                    raise
        except FileExistsError:
            pass
        else:
            try:
                st = os.stat(content.name)
                os.chmod(path, stat.S_IMODE(st.st_mode))
            except FileNotFoundError:
                pass

        return path

    @staticmethod
    def get_artifact_path(sha256digest):
        """
        Determine the absolute path where a file backing the Artifact should be stored.

        Args:
            sha256digest (str): sha256 digest of the file for the Artifact

        Returns:
            A string representing the absolute path where a file backing the Artifact should be
            stored
        """
        return os.path.join(settings.MEDIA_ROOT, 'artifact', sha256digest[0:2], sha256digest[2:])

    @staticmethod
    def published_metadata_path(model, name):
        """
        Get the storage path for published metadata.

        Args:
            model (pulpcore.app.models.PublishedMetadata): A model instance.
            name (str): The file name.

        Returns:
            str: The absolute storage path.
        """
        return os.path.join(
            settings.MEDIA_ROOT,
            'published',
            'metadata',
            str(model.pk),
            name)

    def get_available_name(self, name, max_length=None):
        """
        Get the available absolute path based on the name requested.
        Required by the Storage API.

        Args:
            name (str): File name.
            max_length (int): Maximum length, in characters, of the returned path.

        Returns:
            str: Available name.

        Raises:
            ValueError if ``max_length`` exceeded.
        """
        if max_length:
            if len(name) > max_length:
                raise ValueError('max_length exceeded')
        return name

    def delete(self, path):
        """
        Delete the file at the specified path.
        Required by the Storage API.

        Args:
            path (str): An absolute file path.
        """
        FileSystem.unlink(path)

    def exists(self, path):
        """
        Get whether the file actually exists at the specified path.
        Required by the Storage API.

        Args:
            path (str): An absolute file path.

        Returns:
            bool: True if exists.
        """
        return os.path.exists(path)

    def listdir(self, path):
        """
        List the content of the directory at the specified path.
        Required by the Storage API.

        Args:
            path (str): An absolute directory path.

        Returns:
            A tuple of two lists: (directories, files).
        """
        files = []
        directories = []
        for entry in os.listdir(path):
            if os.path.isdir(os.path.join(path, entry)):
                directories.append(entry)
            else:
                files.append(entry)
        return (directories, files)

    def path(self, name):
        """
        Get the absolute path to a file with the specified name.
        Required by the Storage API.

        Args:
            name (str): A file name.

        Returns:
            str: An absolute path.
        """
        return name

    def size(self, path):
        """
        Get the size of the file at the specified path.
        Required by the Storage API.

        Args:
            path (str): An absolute file path.

        Returns:
            int: The size in bytes.
        """
        return os.path.getsize(path)

    def url(self, path):
        """
        Get a URL for the file at the specified path.
        Required by the Storage API.

        Args:
            path (str): An absolute file path.

        Returns:
            str: An appropriate URL.
        """
        return 'file://{}'.format(path)

    def accessed_time(self, path):
        """
        Get the last accessed time of the file at specified path.
        Required by the Storage API.

        Args:
            path: An absolute file path.

        Returns:
            datetime: last access time.
        """
        return datetime.fromtimestamp(os.path.getatime(path))

    def created_time(self, path):
        """
        Get the created time of the file at specified path.
        Required by the Storage API.

        Args:
            path (str): An absolute file path.

        Returns:
            datetime: Created time.
        """
        return datetime.fromtimestamp(os.path.getctime(path))

    def modified_time(self, path):
        """
        Get the last modified time of the file at specified path.
        Required by the Storage API.

        Args:
            path (str): An absolute file path.

        Returns:
            datetime: Last modified time.
        """
        return datetime.fromtimestamp(os.path.getmtime(path))
