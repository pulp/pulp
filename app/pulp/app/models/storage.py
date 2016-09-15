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

        :param artifact: An content artifact.
        :type  artifact: pulp.app.models.content.Artifact
        :return: An absolute (base) path.
        :rtype: str
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

        :param artifact: An content artifact.
        :type  artifact: pulp.app.models.content.Artifact
        :param name: Unused but matches the FileField API.
        :param name: str
        :return: An absolute path.
        :rtype: str
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

        :param path: The absolute directory path.
        :type  path: str
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

        :param path: A path to unlink.
        :type  path: str
        """
        try:
            os.unlink(path)
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise

    @staticmethod
    def _open(path, mode='rb'):
        """
        Open the file at the specified path.
        Required by the Storage API.

        :param path: An absolute path to a file.
        :type  path: str
        :param mode: The open mode.  Default: 'rb'.
        :type  mode: str
        :return: An open file object.
        :rtype: File
        """
        return File(open(path, mode))

    @staticmethod
    def _save(path, content):
        """
        Copy the content of a file to the specified path.
        The directory tree is created as needed.
        Required by the Storage API.

        :param path: The (target) path to which the file is copied.
        :type  path: str
        :param content: The (source) file object.
        :type  content: File
        :return: The final storage path.
        :rtype: str
        """
        FileSystem.mkdir(os.path.dirname(path))
        shutil.copy(content.name, path)
        return path

    def get_available_name(self, name, max_length=None):
        """
        Get the available absolute path based on the name requested.
        Required by the Storage API.

        :param name: The file name.
        :type  name: str
        :param max_length: The max length of the returned path.
        :type  max_length: str
        :return: The name.
        :rtype: str
        :raise: ValueError on max_length exceeded.
        """
        if max_length:
            if len(name) > max_length:
                raise ValueError('max_length exceeded')
        return name

    def delete(self, path):
        """
        Delete the file at the specified path.
        Required by the Storage API.

        :param path: An absolute file path.
        :type  path: str
        """
        FileSystem.unlink(path)

    def exists(self, path):
        """
        Get whether the file actually exists at the specified path.
        Required by the Storage API.

        :param path: An absolute file path.
        :type  path: str
        :return: True if exists.
        :rtype: bool
        """
        return os.path.exists(path)

    def listdir(self, path):
        """
        List the content of the directory at the specified path.
        Required by the Storage API.

        :param path: An absolute directory path.
        :type  path: str
        :return: A tuple of two lists: (directories, files).
        :rtype: tuple
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

        :param name: A File.name.
        :type  name: str
        :return: An absolute path.
        :rtype: str
        """
        return name

    def size(self, path):
        """
        Get the size of the file at the specified path.
        Required by the Storage API.

        :param path: An absolute file path.
        :type  path: str
        :return: The size in bytes.
        :rtype: int
        """
        return os.path.getsize(path)

    def url(self, path):
        """
        Get a URL for the file at the specified path.
        Required by the Storage API.

        :param path: An absolute file path.
        :type  path: str
        :return: An appropriate URL.
        :rtype: str
        """
        return 'file://{}'.format(path)

    def accessed_time(self, path):
        """
        Get the last accessed time of the file at specified path.
        Required by the Storage API.

        :param path: An absolute file path.
        :type  path: str
        :return: last access time.
        :rtype: datetime
        """
        return datetime.fromtimestamp(os.path.getatime(path))

    def created_time(self, path):
        """
        Get the created time of the file at specified path.
        Required by the Storage API.

        :param path: An absolute file path.
        :type  path: str
        :return: Created time.
        :rtype: datetime
        """
        return datetime.fromtimestamp(os.path.getctime(path))

    def modified_time(self, path):
        """
        Get the last modified time of the file at specified path.
        Required by the Storage API.

        :param path: An absolute file path.
        :type  path: str
        :return: Last modified time.
        :rtype: datetime
        """
        return datetime.fromtimestamp(os.path.getmtime(path))
