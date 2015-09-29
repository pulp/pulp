import os
import errno
import shutil

from hashlib import sha256

from pulp.server.config import config


def mkdir(path):
    """
    Create a directory at the specified path.
    Directory (and intermediate) directories are only created if they
    don't already exist.

    :param path: The absolute path to the leaf directory to be created.
    :type path: str
    """
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


class ContentStorage(object):
    """
    Base class for content storage.
    """

    def put(self, unit, path):
        """
        Put the content (bits) associated with the specified content unit into storage.
        The file (or directory) at the specified *path* is transferred into storage.

        :param unit: The content unit to be stored.
        :type unit: pulp.server.db.models.ContentUnit
        :param path: The absolute path to the file (or directory) to be stored.
        :type path: str
        """
        raise NotImplementedError()

    def get(self, unit):
        """
        Get the content (bits) associated with the specified content unit from storage.

        Note: This method included for symmetry and to demonstrate
              the full potential of this model.

        :return: A file-like object used to stream the content.
        :rtype: file
        """
        raise NotImplementedError()

    def open(self):
        """
        Open the storage.
        """
        pass

    def close(self):
        """
        Close the storage.
        """
        pass

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *unused):
        self.close()


class FileStorage(ContentStorage):
    """
    Direct storage for files and directories.
    """

    def put(self, unit, path):
        """
        Put the content defined by the content unit into storage.
        The file (or directory) at the specified *path* is transferred into storage.

        :param unit: The content unit to be stored.
        :type unit: pulp.server.db.models.ContentUnit
        :param path: The absolute path to the file (or directory) to be stored.
        :type path: str
        """
        storage_dir = os.path.join(
            config.get('server', 'storage_dir'),
            'content',
            'units')
        destination = os.path.join(storage_dir, unit.unit_type_id, unit.id[0:4], unit.id)
        mkdir(os.path.dirname(destination))
        if os.path.isdir(path):
            shutil.copytree(path, destination)
        else:
            shutil.copy(path, destination)
        unit.storage_path = destination

    def get(self, unit):
        """
        Get the content (bits) associated with the specified content unit from storage.

        Note: This method included for symmetry and to demonstrate
              the full potential of this model.

        :return: A file-like object used to stream the content.
        :rtype: file
        """
        pass


class SharedStorage(ContentStorage):
    """
    Direct shared storage.

    :ivar provider: A storage provider.
        This defines the storage mechanism and qualifies the storage_id.
    :type provider: str
    :ivar storage_id: A shared storage identifier.
    :ivar storage_id: str
    """

    def __init__(self, provider, storage_id):
        """
        :param provider: A storage provider.
            This defines the storage mechanism and qualifies the storage_id.
        :type provider: str
        :param storage_id: A shared storage identifier.
        :ivar storage_id: str
        """
        super(SharedStorage, self).__init__()
        self.storage_id = sha256(storage_id).hexdigest()
        self.provider = provider

    def put(self, unit, path=None):
        """
        Put the content (bits) associated with the specified content unit into storage.
        The file (or directory) at the specified *path* is transferred into storage.

        :param unit: The content unit to be stored.
        :type unit: pulp.server.db.models.ContentUnit
        :param path: The absolute path to the file (or directory) to be stored.
        :type path: str
        """
        self.link(unit)

    def get(self, unit):
        """
        Get the content (bits) associated with the specified content unit from storage.

        Note: This method included for symmetry and to demonstrate
              the full potential of this model.

        :return: A file-like object used to stream the content.
        :rtype: file
        """
        pass

    def open(self):
        """
        Open the shared storage.
        The shared storage location is created as needed.
        """
        mkdir(self.content_dir)
        mkdir(self.links_dir)

    @property
    def shared_dir(self):
        """
        The root location of the shared storage.

        :return: The absolute path to the shared storage.
        :rtype: str
        """
        return os.path.join(
            config.get('server', 'storage_dir'),
            'content',
            'shared',
            self.provider,
            self.storage_id)

    @property
    def content_dir(self):
        """
        The location within the shared storage for storing content.

        :return: The absolute path to the location within the
            shared storage for storing content.
        :rtype: str
        """
        path = os.path.join(self.shared_dir, 'content')
        return path

    @property
    def links_dir(self):
        """
        The location within the shared storage for links.

        :return: The absolute path to the location within the
            shared storage for storing links.
        :rtype: str
        """
        path = os.path.join(self.shared_dir, 'links')
        return path

    def link(self, unit):
        """
        Link the specified content unit (by id) to the shared content.

        :param unit: The content unit to be linked.
        :type unit: pulp.server.db.models.ContentUnit
        """
        target = self.content_dir
        link = os.path.join(self.links_dir, unit.id)
        try:
            os.symlink(target, link)
        except OSError, e:
            if e.errno == errno.EEXIST and os.path.islink(link) and os.readlink(link) == target:
                pass  # identical
            else:
                raise
        unit.storage_path = link
