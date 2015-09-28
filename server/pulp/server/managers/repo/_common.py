"""
Contains functionality common across all repository-related managers.

= Working Directories =
Working directories are used as staging or temporary file storage by importers and distributors.
Now that this work is performed inside of celery tasks, each celery worker gets a working
directory. Each task executed by a worker is able to get a working directory inside the workers
root working directory.

The root of the working directories is specified with 'working_directory' setting in
/etc/pulp/server.conf.  The default value is /var/cache/pulp
"""

import os
import shutil

from celery import task

from pulp.common import dateutils, error_codes
from pulp.plugins.model import Repository, RelatedRepository, RepositoryGroup, \
    RelatedRepositoryGroup
from pulp.server import config as pulp_config
from pulp.server.exceptions import PulpCodedException


def to_transfer_repo(repo_data):
    """
    Converts the given database representation of a repository into a plugin
    repository transfer object, including any other fields that need to be
    included.

    @param repo_data: database representation of a repository
    @type  repo_data: dict

    @return: transfer object used in many plugin API calls
    @rtype:  pulp.plugins.model.Repository}
    """
    r = Repository(repo_data['id'], repo_data['display_name'], repo_data['description'],
                   repo_data['notes'], content_unit_counts=repo_data['content_unit_counts'],
                   last_unit_added=dateutils.ensure_tz(repo_data.get('last_unit_added')),
                   last_unit_removed=dateutils.ensure_tz(repo_data.get('last_unit_removed')))
    return r


def to_related_repo(repo_data, configs):
    """
    Converts the given database representation of a repository into a plugin's
    representation of a related repository. The list of configurations for
    the repository's plugins will be included in the returned type.

    @param repo_data: database representation of a repository
    @type  repo_data: dict

    @param configs: list of configurations for all relevant plugins on the repo
    @type  configs: list

    @return: transfer object used in many plugin API calls
    @rtype:  pulp.plugins.model.RelatedRepository
    """
    r = RelatedRepository(repo_data['id'], configs, repo_data['display_name'],
                          repo_data['description'], repo_data['notes'])
    return r


def to_transfer_repo_group(group_data):
    """
    Converts the given database representation of a repository group into a
    plugin transfer object.

    @param group_data: database representation of the group
    @type  group_data: dict

    @return: transfer object used in plugin calls
    @rtype:  pulp.plugins.model.RepositoryGroup
    """
    g = RepositoryGroup(group_data['id'], group_data['display_name'],
                        group_data['description'], group_data['notes'],
                        group_data['repo_ids'])
    return g


def to_related_repo_group(group_data, configs):
    """
    Converts the given database representation of a repository group into a
    plugin transfer object. The list of configurations for the requested
    group plugins are included in the returned type.

    @param group_data: database representation of the group
    @type  group_data: dict

    @param configs: list of plugin configurations to include
    @type  configs: list

    @return: transfer object used in plugin calls
    @rtype:  pulp.plugins.model.RelatedRepositoryGroup
    """
    g = RelatedRepositoryGroup(group_data['id'], configs, group_data['display_name'],
                               group_data['description'], group_data['notes'])
    return g


def _working_dir_root(worker_name):
    """
    Returns the path to the working directory of a worker

    :param worker_name:     Name of worker for which path is requested
    :type  name:            basestring
    :return working_directory setting from server config
    :rtype  str
    """
    working_dir = pulp_config.config.get('server', 'working_directory')
    dir_root = os.path.join(working_dir, worker_name)
    return dir_root


def create_worker_working_directory(worker_name):
    """
    Creates a working directory inside the working_directory as specified in /etc/pulp/server.conf
    default path for working_directory is /var/cache/pulp

    :param worker_name:     Name of worker that uses the working directory created
    :type  name:            basestring
    :return Path to the working directory for a worker
    :rtype  str
    """
    working_dir_root = _working_dir_root(worker_name)
    os.mkdir(working_dir_root)


def delete_worker_working_directory(worker_name):
    """
    Deletes a working directory inside the working_directory as specified in /etc/pulp/server.conf
    default path for working_directory is /var/cache/pulp

    :param worker_name:     Name of worker that uses the working directory being deleted
    :type  name:            basestring
    """
    working_dir_root = _working_dir_root(worker_name)
    if os.path.exists(working_dir_root):
        shutil.rmtree(working_dir_root)


def _working_directory_path():
    """
    Gets the path for a task's working directory inside a workers working directory

    @return: full path on disk to the working directory for current task
    @rtype:  str
    """
    current_task = task.current
    if (current_task and current_task.request and current_task.request.id and
            current_task.request.hostname):
        worker_name = current_task.request.hostname
        task_id = current_task.request.id
        worker_dir_root = _working_dir_root(worker_name)
        working_dir_root = os.path.join(worker_dir_root, task_id)
    else:
        return None

    return working_dir_root


def get_working_directory():
    """
    Creates a working directory with task id as name. This directory resides inside a particular
    worker's working directory. The 'working_directory' setting in [server] section of
    /etc/pulp/server.conf defines the local path to the root of working directories. The directory
    is created only once per task. The path to the existing working directory is returned for all
    subsequent calls for that task.

    @return: full path on disk to the working directory for current task
    @rtype:  str
    """
    working_dir_root = _working_directory_path()

    if working_dir_root:
        if os.path.exists(working_dir_root):
            return working_dir_root
        os.mkdir(working_dir_root)
        return working_dir_root
    else:
        # If path is None, this method is called outside of an asynchronous task
        raise PulpCodedException(error_codes.PLP0033)


def delete_working_directory():
    """
    Deletes working directory for a particular task.

    @return: None
    @rtype:  None
    """
    working_dir_root = _working_directory_path()

    if working_dir_root and os.path.exists(working_dir_root):
        shutil.rmtree(working_dir_root)
