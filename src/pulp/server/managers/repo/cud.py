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
Contains the manager class and exceptions for operations surrounding the creation,
removal, and metadata update on a repository. This does not include importer
or distributor configuration.
"""

import logging
import os
import re
import shutil

from pulp.server.db.model.gc_repository import Repo, RepoDistributor, RepoImporter, RepoContentUnit, RepoSyncResult, RepoPublishResult
import pulp.server.managers.factory as manager_factory
import pulp.server.managers.repo._common as common_utils
from pulp.server.managers.repo._exceptions import MissingRepo, InvalidRepoId, InvalidRepoMetadata, DuplicateRepoId, RepoDeleteException

# -- constants ----------------------------------------------------------------

_REPO_ID_REGEX = re.compile(r'^[\-_A-Za-z0-9]+$') # letters, numbers, underscore, hyphen
_DISTRIBUTOR_ID_REGEX = _REPO_ID_REGEX # for now, use the same constraints

_LOG = logging.getLogger(__name__)

# -- manager ------------------------------------------------------------------

class RepoManager:
    """
    Performs repository related functions relating to both CRUD operations and
    actions performed on or by repositories.
    """

    def create_repo(self, repo_id, display_name=None, description=None, notes=None):
        """
        Creates a new Pulp repository that is not associated with any importers
        or distributors (those are added later through separate calls).

        @param repo_id: unique identifier for the repo
        @type  repo_id: str

        @param display_name: user-friendly name for the repo
        @type  display_name: str

        @param description: user-friendly text describing the repo's contents
        @type  description: str

        @param notes: key-value pairs to programmatically tag the repo
        @type  notes: dict

        @raises InvalidRepoId: if the repo ID is unacceptable
        @raises DuplicateRepoId: if there is already a repo with the requested ID
        @raises InvalidRepoMetadata: if any of the non-ID fields is unacceptable
        """

        # Validation
        if not is_repo_id_valid(repo_id):
            raise InvalidRepoId(repo_id)

        existing_repo = Repo.get_collection().find_one({'id' : repo_id})
        if existing_repo is not None:
            raise DuplicateRepoId(repo_id)

        if notes is not None and not isinstance(notes, dict):
            raise InvalidRepoMetadata(notes)

        # Use the ID for the display name if one was not specified
        display_name = display_name or repo_id

        # Creation
        create_me = Repo(repo_id, display_name, description, notes)
        Repo.get_collection().save(create_me, safe=True)

        return create_me

    def delete_repo(self, repo_id):
        """
        Deletes the given repository, optionally requesting the associated
        importer clean up any content in the repository.

        @param repo_id: identifies the repo being deleted
        @type  repo_id: str

        @raises MissingRepo: if the given repo does not exist
        @raises RepoDeleteException: if any part of the delete process fails;
                the exception will contain information on which sections failed
        """

        # Validation
        found = Repo.get_collection().find_one({'id' : repo_id})
        if found is None:
            raise MissingRepo(repo_id)

        # With so much going on during a delete, it's possible that a few things
        # could go wrong while others are successful. We track lesser errors
        # that shouldn't abort the entire process until the end and then raise
        # an exception describing the incompleteness of the delete. The user
        # will have to look at the server logs for more information.
        error_codes = []

        # Inform the importer
        importer_coll = RepoImporter.get_collection()
        importer_manager = manager_factory.repo_importer_manager()
        repo_importer = importer_coll.find_one({'repo_id' : repo_id})
        if repo_importer is not None:
            try:
                importer_manager.remove_importer(repo_id)
            except Exception:
                _LOG.exception('Error received removing importer [%s] from repo [%s]' % (repo_importer['importer_type_id'], repo_id))
                error_codes.append(RepoDeleteException.CODE_IMPORTER)

        # Inform all distributors
        distributor_coll = RepoDistributor.get_collection()
        distributor_manager = manager_factory.repo_distributor_manager()
        repo_distributors = list(distributor_coll.find({'repo_id' : repo_id}))
        for repo_distributor in repo_distributors:
            try:
                distributor_manager.remove_distributor(repo_id, repo_distributor['id'])
            except Exception:
                _LOG.exception('Error received removing distributor [%s] from repo [%s]' % (repo_distributor['id'], repo_id))
                error_codes.append(RepoDeleteException.CODE_DISTRIBUTOR)

        # Delete the repository working directory
        repo_working_dir = common_utils.repository_working_dir(repo_id, mkdir=False)
        if os.path.exists(repo_working_dir):
            try:
                shutil.rmtree(repo_working_dir)
            except Exception:
                _LOG.exception('Error while deleting repo working dir [%s] for repo [%s]' % (repo_working_dir, repo_id))
                error_codes.append(RepoDeleteException.CODE_WORKING_DIR)

        # Database Updates
        try:
            Repo.get_collection().remove({'id' : repo_id}, safe=True)

            # Remove all importers and distributors from the repo
            # This is likely already done by the calls to other methods in
            #   this manager, but in case those failed we still want to attempt
            #   to keep the database clean
            RepoDistributor.get_collection().remove({'repo_id' : repo_id}, safe=True)
            RepoImporter.get_collection().remove({'repo_id' : repo_id}, safe=True)

            RepoSyncResult.get_collection().remove({'repo_id' : repo_id}, safe=True)
            RepoPublishResult.get_collection().remove({'repo_id' : repo_id}, safe=True)

            # Remove all associations from the repo
            RepoContentUnit.get_collection().remove({'repo_id' : repo_id}, safe=True)
        except Exception:
            _LOG.exception('Error updating one or more database collections while removing repo [%s]' % repo_id)
            error_codes.append(RepoDeleteException.CODE_DATABASE)

        if len(error_codes) > 0:
            raise RepoDeleteException(error_codes)

    def update_repo(self, repo_id, delta):
        """
        Updates metadata about the given repository. Only the following
        fields may be updated through this call:
        * display_name
        * description

        Other fields found in delta will be ignored.

        @param repo_id: identifies the repo
        @type  repo_id: str

        @param delta: list of attributes and their new values to change
        @type  delta: dict

        @raises MissingRepo: if there is no repo with repo_id
        """

        repo_coll = Repo.get_collection()

        repo = repo_coll.find_one({'id' : repo_id})
        if repo is None:
            raise MissingRepo(repo_id)

        # There are probably all sorts of clever ways to not hard code the
        # fields here, but frankly, there are so few that this is just easier.
        # It also makes it very simple to ignore any rogue keys that are in delta.

        if 'display_name' in delta:
            repo['display_name'] = delta['display_name']

        if 'description' in delta:
            repo['description'] = delta['description']

        if 'notes' in delta:
            repo['notes'] = delta['notes']

        repo_coll.save(repo, safe=True)

        return repo

# -- functions ----------------------------------------------------------------

def is_repo_id_valid(repo_id):
    """
    @return: true if the repo ID is valid; false otherwise
    @rtype:  bool
    """
    result = _REPO_ID_REGEX.match(repo_id) is not None
    return result
