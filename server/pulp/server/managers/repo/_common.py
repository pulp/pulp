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

from pulp.plugins.model import RelatedRepository, RepositoryGroup, RelatedRepositoryGroup


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
