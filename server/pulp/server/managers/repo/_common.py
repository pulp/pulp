# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""
Contains functionality common across all repository-related managers.

= Working Directories =
Working directories are as staging or temporary file storage by importers
and distributors. Each directory is unique to the repository and plugin
combination.

The directory structure for plugin working directories is as follows:
<pulp_storage>/working/<repo_id>/[importers|distributors]/<plugin_type_id>

For example, for importer "foo" and repository "bar":
/var/lib/pulp/working/bar/importers/foo

The rationale is to simplify cleanup on repository delete; the repository's
working directory is simply deleted.
"""

import os

from pulp.server import config as pulp_config
from pulp.plugins.model import Repository, RelatedRepository, RepositoryGroup, RelatedRepositoryGroup

# -- single repo calls --------------------------------------------------------

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
    r = Repository(repo_data['id'], repo_data['display_name'], repo_data['description'], repo_data['notes'])
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
    r = RelatedRepository(repo_data['id'], configs, repo_data['display_name'], repo_data['description'], repo_data['notes'])
    return r

def repository_working_dir(repo_id, mkdir=True):
    """
    Determines the repository's working directory. Individual plugin working
    directories will be placed under this. If the mkdir argument is set to true,
    the directory will be created as part of this call.

    See the module-level docstrings for more information on the directory
    structure.

    @param mkdir: if true, this call will create the directory; otherwise the
                  full path will just be generated
    @type  mkdir: bool

    @return: full path on disk
    @rtype:  str
    """
    working_dir = os.path.join(_repo_working_dir(), repo_id)

    if mkdir and not os.path.exists(working_dir):
        os.makedirs(working_dir)

    return working_dir

def importer_working_dir(importer_type_id, repo_id, mkdir=True):
    """
    Determines the working directory for an importer to use for a repository.
    If the mkdir argument is set to true, the directory will be created as
    part of this call.

    See the module-level docstrings for more information on the directory
    structure.

    @param mkdir: if true, this call will create the directory; otherwise the
                  full path will just be generated
    @type  mkdir: bool

    @return: full path on disk to the directory the importer can use for the
             given repository
    @rtype:  str
    """
    repo_working_dir = repository_working_dir(repo_id, mkdir)
    working_dir = os.path.join(repo_working_dir, 'importers', importer_type_id)

    if mkdir and not os.path.exists(working_dir):
        os.makedirs(working_dir)

    return working_dir

def distributor_working_dir(distributor_type_id, repo_id, mkdir=True):
    """
    Determines the working directory for an distributor to use for a repository.
    If the mkdir argument is set to true, the directory will be created as
    part of this call.

    See the module-level docstrings for more information on the directory
    structure.

    @param mkdir: if true, this call will create the directory; otherwise the
                  full path will just be generated
    @type  mkdir: bool

    @return: full path on disk to the directory the distributor can use for the
             given repository
    @rtype:  str
    """
    repo_working_dir = repository_working_dir(repo_id, mkdir)
    working_dir = os.path.join(repo_working_dir, 'distributors', distributor_type_id)

    if mkdir and not os.path.exists(working_dir):
        os.makedirs(working_dir)

    return working_dir

# -- repository group calls ---------------------------------------------------

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

def repo_group_working_dir(group_id, mkdir=True):
    """
    Determines the repo group's working directory. Individual plugin working
    directories will be placed under this. If the mkdir argument is set to
    true, the directory will be created as part of this call.

    @param group_id: identifies the repo group
    @type  group_id: str

    @param mkdir: if true, the call will create the directory; otherwise the
                  full path will just be generated and returned
    @type  mkdir: bool

    @return: full path on disk
    @rtype:  str
    """
    working_dir = os.path.join(_repo_group_working_dir(), group_id)

    if mkdir and not os.path.exists(working_dir):
        os.makedirs(working_dir)

    return working_dir

def group_importer_working_dir(importer_type_id, group_id, mkdir=True):
    """
    Determines the working directory for an importer to use for a repository
    group. If the mkdir argument is set to true, the directory will be created
    as part of this call.

    @param mkdir: if true, the call will create the directory; otherwise the
                  full path will just be generated and returned
    @type  mkdir: bool

    @return: full path on disk
    @rtype:  str
    """
    group_working_dir = repo_group_working_dir(group_id, mkdir)
    working_dir = os.path.join(group_working_dir, 'importers', importer_type_id)

    if mkdir and not os.path.exists(working_dir):
        os.makedirs(working_dir)

    return working_dir

def group_distributor_working_dir(distributor_type_id, group_id, mkdir=True):
    """
    Determines the working directory for an importer to use for a repository
    group. If the mkdir argument is set to true, the directory will be created
    as part of this call.

    @param mkdir: if true, the call will create the directory; otherwise the
                  full path will just be generated and returned
    @type  mkdir: bool

    @return: full path on disk
    @rtype:  str
    """
    group_working_dir = repo_group_working_dir(group_id, mkdir)
    working_dir = os.path.join(group_working_dir, 'distributors', distributor_type_id)

    if mkdir and not os.path.exists(working_dir):
        os.makedirs(working_dir)

    return working_dir


def _working_dir_root():
    storage_dir = pulp_config.config.get('server', 'storage_dir')
    dir_root = os.path.join(storage_dir, 'working')
    return dir_root

def _repo_working_dir():
    dir = os.path.join(_working_dir_root(), 'repos')
    return dir

def _repo_group_working_dir():
    dir = os.path.join(_working_dir_root(), 'repo_groups')
    return dir
