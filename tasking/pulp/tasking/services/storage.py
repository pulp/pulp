import errno
import os
import shutil
import stat
from contextlib import suppress

from celery import task
from django.conf import settings as pulp_settings


def _working_dir_root(worker_name):
    """Return the path to the working directory of a worker.

    :param worker_name:     Name of worker for which path is requested
    :type  worker_name:     basestring

    :returns: working_directory setting from server config
    :rtype:   str
    """
    return os.path.join(pulp_settings.SERVER['working_directory'], worker_name)


def create_worker_working_directory(worker_name):
    """Create a working directory for a worker.

    Create a working directory inside the worker working_directory as specified in the setting file.

    :param worker_name:     Name of worker that uses the working directory created
    :type  worker_name:     basestring

    :returns: Path to the working directory for a worker
    :rtype:   str
    """
    working_dir_root = _working_dir_root(worker_name)
    os.mkdir(working_dir_root)
    return working_dir_root


def delete_worker_working_directory(worker_name):
    """Delete worker's working directory.

    Delete a working directory inside the working_directory as specified in the setting file.

    :param worker_name:     Name of worker that uses the working directory being deleted
    :type  worker_name:     basestring
    """
    _rmtree(_working_dir_root(worker_name))


def _working_directory_path():
    """Get path of task working directory.

    Get the path for a task working directory inside a workers working directory.

    :returns: full path on disk to the working directory for current task
    :rtype:   basestring
    """
    current_task = task.current
    with suppress(AttributeError):
        task_id = current_task.request.id
    worker_name = current_task.request.hostname
    if current_task and current_task.request and task_id and worker_name:
        return os.path.join(_working_dir_root(worker_name), task_id)


def delete_working_directory():
    """Delete working directory for a particular task."""
    _rmtree(_working_directory_path())


def get_working_directory():
    """Create a working directory with task id as name.

    This directory resides inside a particular worker's working directory.
    The 'working_directory' setting in ``server`` section of settings defines the local path
    to the root of working directories.

    The directoryis created only once per task. The path to the existing working directory
    is returned for all subsequent calls for that task.

    :returns: full path on disk to the working directory for current task
    :rtype:  str
    """
    working_dir_root = _working_directory_path()

    if working_dir_root:
        try:
            os.mkdir(working_dir_root)
        except OSError as error:
            if error.errno is errno.EEXIST:
                return working_dir_root
            else:
                raise
        else:
            return working_dir_root
    else:
        # If path is None, this method is called outside of an asynchronous task
        raise RuntimeError("Working Directory requested outside of asynchronous task.")


def _rmtree(path):
    """Delete if exists an entire directory tree in path.

    Uses _rmtree_fix_permissions but suppresses 'No such file or directory' Exception.
    """
    if path is None:
        return
    try:
        _rmtree_fix_permissions(path)
    except OSError as error:
        if error.errno is errno.ENOENT:
            pass
        else:
            raise


def _rmtree_fix_permissions(directory_path):
    """Delete an entire directory tree in path.

    Recursively remove a directory. If permissions on the directory or it's contents
    block removal, attempt to fix the permissions to allow removal and attempt the removal
    again.

    :param directory_path: The directory to remove
    :type directory_path: str
    """
    try:
        shutil.rmtree(directory_path)
    except OSError as error:
        # if perm denied (13) add rwx permissions to all directories and retry
        # so that we are not blocked by users creating directories with no permissions
        if error.errno is errno.EACCES:
            for root, dirs, files in os.walk(directory_path):
                for dir_path in dirs:
                    os.chmod(os.path.join(root, dir_path),
                             stat.S_IXUSR | stat.S_IWUSR | stat.S_IREAD)
            shutil.rmtree(directory_path)
        else:
            raise
