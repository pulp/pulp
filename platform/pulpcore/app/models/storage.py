import os
import errno
import shutil

from datetime import datetime

from django.conf import settings
from django.core.files import File
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible


@deconstructible
class StoragePath(object):
    """
    Content storage path.
    """

    @staticmethod
    def base_path(artifact):
        """
        Get the base path used to store a file associated with the specified artifact.
        All artifact files *must* be stored relative to this location.

        Args:
            artifact (pulpcore.app.models.content.Artifact): Content artifact.

        Returns:
            str: An absolute (base) path
        """
        digest = artifact.content.natural_key_digest()
        return os.path.join(
            settings.MEDIA_ROOT,
            'units',
            artifact.content.type,
            digest[0:2],
            digest[2:])

    def __call__(self, artifact, name):
        """
        Get the absolute path used to store a file associated
        with the specified artifact.

        Args:
            artifact (pulpcore.app.models.content.Artifact): Content artifact.
            name (str): Unused, here to match Django's FileField API.

        Returns:
            str: Absolute path.
        """
        return os.path.join(StoragePath.base_path(artifact), artifact.relative_path)


class FileSystem(Storage):
    """
    Provides simplified filesystem storage.
    The django filesystem storage is overly complex and makes incompatible assumptions
    and has incompatible behaviors with regard to how final storage paths are calculated.
    """

    @staticmethod
    def mkdir(path):
        """
        Make the directory (and parent directories) at the specified path.
        No exception is raised if the directory already exists.

        Args:
            path (str): Absolute directory path.
        """
        try:
            os.makedirs(path)
        except OSError as e:
            if e.errno == errno.EEXIST and os.path.isdir(path):
                # ignored.
                pass
            else:
                raise

    @staticmethod
    def unlink(path):
        """
        Delete the link at the specified path.
        No exception is raised if the link does not exist.

        Args:
            path (str): Path to unlink.
        """
        try:
            os.unlink(path)
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise

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
        Copy the content of a file to the specified path.
        The directory tree is created as needed.
        Required by the Storage API.

        Args:
            path (str): Target path to which the file is copied.
            content (File): Source file object.

        Returns:
            str: Final storage page.
        """
        FileSystem.mkdir(os.path.dirname(path))
        shutil.copy(content.name, path)
        return path

    def get_available_name(self, name, max_length=None):
        """
        Get the available absolute path based on the name requested.
        Required by the Storage API.

        Args:
            name (str): File name.
            max_lenth (int): Maximum length, in characters, of the returned path.

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
