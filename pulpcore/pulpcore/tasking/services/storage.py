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
        Create the directory on the Filesystem.

        The directory (tree) is deleted and recreated when already exist.

        Returns:
            pulpcore.tasking.services.storage.WorkingDirectory: The created directory.
        """
        path = cls._build_path()
        try:
            os.makedirs(path, mode=cls.MODE)
        except FileExistsError:
            _dir = cls(path)
            _dir.delete()
            os.makedirs(path, mode=cls.MODE)
            return _dir
        else:
            return cls(path)

    @staticmethod
    def _build_path():
        """
        Build the directory path using format: <root>/<worker-name>/<task_id>

        Returns:
            str: The absolute directory path.

        Raises:
            RuntimeError: When used outside a Celery task.
        """
        root = settings.SERVER['working_directory']
        try:
            return os.path.join(
                root,
                task.current.request.hostname,
                task.current.request.id)
        except AttributeError:
            raise RuntimeError(_('WorkingDirectory may only be used within a Task.'))

    def __init__(self, path):
        """
        Args:
            The absolute path to the directory.

        Raises:
            RuntimeError: When used outside a Celery task.
        """
        self._path = path
        assert os.path.isdir(path), _('{p} must be real directory'.format(p=path))

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
