import os
import errno
import shutil
import tempfile

from hashlib import sha256

from pulp.server.config import config
from pulp.plugins.util import misc


class ContentStorage(object):
    """
    Base class for content storage.
    """

    def put(self, unit, path, location=None):
        """
        Put the content (bits) associated with the specified content unit into storage.
        The file (or directory) at the specified *path* is transferred into storage.

        :param unit: The content unit to be stored.
        :type unit: pulp.sever.db.model.ContentUnit
        :param path: The absolute path to the file (or directory) to be stored.
        :type path: str
        :param location: The (optional) location within the path
            where the content is to be stored.
        :type location: str
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
    Direct file storage.
    """

    @staticmethod
    def get_path(unit):
        """
        Get the appropriate storage path for the specified unit.
        The path is derived by hashing a string representation of the unit
        key and combining it with the storage directory and unit type as follows:
        <storage_dir>/content/units/<digest>[0:2]/<digest>[2:]/

        :param unit: A content unit.
        :type unit: pulp.server.db.model.FileContentUnit
        :return: An absolute path to where associated content files will be stored.
        :rtype: str
        """
        storage_dir = os.path.join(
            config.get('server', 'storage_dir'),
            'content',
            'units')
        digest = unit.unit_key_as_digest(sha256())
        return os.path.join(
            storage_dir,
            unit.type_id,
            digest[0:2],
            digest[2:])

    def put(self, unit, path, location=None):
        """
        Put the content defined by the content unit into storage.
        The file at the specified *path* is transferred into storage:
         - Copy file to the temporary file at its final directory.
         - If possible, verify size of the file to make sure that file is not corrupted.
         - Do atomic rename.

        :param unit: The content unit to be stored.
        :type unit: pulp.sever.db.model.ContentUnit
        :param path: The absolute path to the file (or directory) to be stored.
        :type path: str
        :param location: The (optional) location within the path
            where the content is to be stored.
        :type location: str
        """
        destination = unit.storage_path
        if location:
            destination = os.path.join(destination, location.lstrip('/'))
        misc.mkdir(os.path.dirname(destination))
        fd, temp_destination = tempfile.mkstemp(dir=os.path.dirname(destination))

        # to avoid a file descriptor leak, close the one opened by tempfile.mkstemp which we are not
        # going to use.
        os.close(fd)

        shutil.copy(path, temp_destination)

        try:
            unit.verify_size(temp_destination)
        except AttributeError:
            # verify_size method is not implemented for the unit
            pass
        except Exception:
            os.remove(temp_destination)
            raise

        os.rename(temp_destination, destination)

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

    def put(self, unit, path=None, location=None):
        """
        Put the content (bits) associated with the specified content unit into storage.
        The file (or directory) at the specified *path* is transferred into storage.

        :param unit: The content unit to be stored.
        :type unit: pulp.sever.db.model.ContentUnit
        :param path: The absolute path to the file (or directory) to be stored.
        :type path: str
        :param location: The (optional) location within the path
            where the content is to be stored.
        :type location: str
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
        misc.mkdir(self.content_dir)
        misc.mkdir(self.links_dir)

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
        :type unit: pulp.sever.db.model.ContentUnit
        :return: The absolute path to the link.
        :rtype: str
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
        return link
