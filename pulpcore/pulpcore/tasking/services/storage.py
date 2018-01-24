import os
import shutil

from gettext import gettext as _

from celery import task
from django.conf import settings


class WorkingDirectory:
    """
    A context manager used to manage a Celery task's working directory.

    Examples:
        >>>
        >>> with WorkingDirectory.create() as working_dir:
        >>>     ...
        >>>
    """

    # Directory permissions.
    MODE = 0o700

    @classmethod
    def create(cls):
        """
        Create a working directory for a running Celery task on the Filesystem.

        The directory (tree) is deleted and recreated when already exist.

        Returns:
            pulpcore.tasking.services.storage.WorkingDirectory: The created directory.
        """
        def mkdir(p):
            os.makedirs(p, mode=cls.MODE)
        path = cls.task_path()
        try:
            mkdir(path)
        except FileExistsError:
            _dir = cls(path)
            _dir.delete()
            mkdir(path)
            return _dir
        else:
            return cls(path)

    @classmethod
    def for_worker(cls, hostname):
        """
        Factory method for building a WorkingDirectory object for a worker by name.

        Args:
            hostname (str): The worker hostname.

        Returns:
            pulpcore.tasking.services.storage.WorkingDirectory: The created directory.

        Raises:
            FileNotFoundError: When directory not found.
        """
        path = cls.worker_path(hostname)
        return cls(path)

    @staticmethod
    def worker_path(hostname):
        """
        Get the root directory path for a worker by hostname.

        Args:
            hostname (str): The worker hostname.

        Returns:
            str: The absolute path to a worker's root working directory.
        """
        root = settings.SERVER['working_directory']
        path = os.path.join(root, hostname)
        return path

    @staticmethod
    def task_path():
        """
        Get the directory path for a running Celery task.

        Format: <root>/<worker-name>/<task_id>

        Returns:
            str: The absolute directory path.

        Raises:
            RuntimeError: When used outside a Celery task.
        """
        try:
            return os.path.join(
                WorkingDirectory.worker_path(task.current.request.hostname),
                task.current.request.id)
        except AttributeError:
            raise RuntimeError(_('WorkingDirectory may only be used within a Task.'))

    def __init__(self, path):
        """
        Args:
            The absolute path to the directory.

        Raises:
            FileNotFound: When path is not a directory.
        """
        self._path = path
        if not os.path.isdir(path):
            raise FileNotFoundError('{p} must be a directory'.format(p=path))

    @property
    def path(self):
        """
        The absolute path to the directory.

        Returns:
            str: The absolute directory path.
        """
        return self._path

    def delete(self):
        """
        Delete the directory (tree).

        On permission denied - an attempt is made to recursively fix the
        permissions on the tree and the delete is retried.
        """
        try:
            shutil.rmtree(self.path)
        except PermissionError:
            self._set_permissions()
            self.delete()

    def _set_permissions(self):
        """
        Set appropriate permissions on the directory tree.
        """
        for path in os.walk(self.path):
            os.chmod(path[0], mode=self.MODE)

    def __enter__(self):
        """
        Create the directory and set the CWD to the path.

        Returns:
            WorkingDirectory: self

        Raises:
            OSError: On failure.
        """
        self._prev_dir = os.getcwd()
        os.chdir(self.path)
        return self

    def __exit__(self, *unused):
        """
        Delete the directory (tree) and restore the original CWD.
        """
        os.chdir(self._prev_dir)
        self.delete()

    def __str__(self):
        return self.path
