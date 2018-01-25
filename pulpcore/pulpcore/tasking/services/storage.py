import os
import shutil

from gettext import gettext as _

from celery import task
from django.conf import settings


class WorkerDirectory:
    """
    Celery worker directory.

    Attributes:
        _path (str): The absolute path.
    """

    # Directory permissions.
    MODE = 0o700

    @staticmethod
    def _worker_path(hostname):
        """
        Get the root directory path for a worker by hostname.

        Args:
            hostname (str): The worker hostname.

        Returns:
            str: The absolute path to a worker's root directory.
        """
        root = settings.SERVER['working_directory']
        path = os.path.join(root, hostname)
        return path

    def __init__(self, hostname):
        """
        Args:
            hostname (str): The worker hostname.
        """
        self._path = self._worker_path(hostname)

    @property
    def path(self):
        """
        The absolute path to the directory.

        Returns:
            str: The absolute directory path.
        """
        return self._path

    def create(self):
        """
        Create the directory.

        The directory (tree) is deleted and recreated when already exist.
        """
        def create():
            os.makedirs(self.path, mode=self.MODE)
        try:
            create()
        except FileExistsError:
            self.delete()
            create()

    def delete(self):
        """
        Delete the directory (tree).

        On permission denied - an attempt is made to recursively fix the
        permissions on the tree and the delete is retried.
        """
        try:
            shutil.rmtree(self.path)
        except FileNotFoundError:
            pass
        except PermissionError:
            self._set_permissions()
            self.delete()

    def _set_permissions(self):
        """
        Set appropriate permissions on the directory tree.
        """
        for path in os.walk(self.path):
            os.chmod(path[0], mode=self.MODE)

    def __str__(self):
        return self.path


class TaskDirectory(WorkerDirectory):
    """
    Celery task directory.
    """

    @staticmethod
    def _hostname():
        """
        The worker hostname.

        Returns:
            str: The worker hostname.

        Raises:
            RuntimeError: When used outside of a celery task.
        """
        try:
            return task.current.request.hostname
        except AttributeError:
            raise RuntimeError(_('May only be used within a Task.'))

    @staticmethod
    def _task_id():
        """
        The current task ID.

        Returns:
            str: The current task ID.

        Raises:
            RuntimeError: When used outside of a celery task.
        """
        try:
            return task.current.request.id
        except AttributeError:
            raise RuntimeError(_('May only be used within a Task.'))

    def __init__(self):
        super().__init__(self._hostname())
        self._path = os.path.join(self._path, self._task_id())


class WorkingDirectory:
    """
    Celery task working directory context manager.

    Attributes:
        _task_dir (TaskDirectory): A task directory.

    Examples:
        >>>
        >>> with WorkingDirectory.create() as working_dir:
        >>>     ....
        >>>
    """

    @classmethod
    def create(cls):
        """
        Create a task working directory.

        Returns:
            pulpcore.tasking.service.WorkingDirectory: self
        """
        task_dir = TaskDirectory()
        task_dir.create()
        return cls(task_dir)

    def __init__(self, task_dir):
        """
        Args:
            task_dir (TaskDirectory): A task directory.
        """
        self._task_dir = task_dir

    def __enter__(self):
        """
        Create the directory and set the CWD to the path.

        Returns:
            pulpcore.tasking.service.WorkingDirectory: self

        Raises:
            OSError: On failure.
        """
        self._prev_dir = os.getcwd()
        os.chdir(self._task_dir.path)
        return self

    def __exit__(self, *unused):
        """
        Delete the directory (tree) and restore the original CWD.
        """
        os.chdir(self._prev_dir)
        self._task_dir.delete()
