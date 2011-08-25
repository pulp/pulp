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
Contains the manager class and exceptions for all repository related functionality.
"""

from gettext import gettext as _
import logging
import re

from pulp.server.db.model.gc_repository import Repo, RepoDistributor, RepoImporter

# -- constants ----------------------------------------------------------------

_REPO_ID_REGEX = re.compile(r'^[\-_A-Za-z0-9]+$') # letters, numbers, underscore, hyphen

_LOG = logging.getLogger(__name__)

# -- exceptions ---------------------------------------------------------------

class InvalidRepoId(Exception):
    """
    Indicates a given repository ID was invalid.
    """
    def __init__(self, invalid_repo_id):
        Exception.__init__(self)
        self.invalid_repo_id = invalid_repo_id

    def __str__(self):
        return _('Invalid repository ID [%(repo_id)s]') % {'repo_id' : self.invalid_repo_id}

class InvalidRepoMetadata(Exception):
    """
    Indicates one or more metadata fields on a repository were invalid, either
    in a create or update operation. The invalid value will be included in
    the exception.
    """
    def __init__(self, invalid_data):
        Exception.__init__(self)
        self.invalid_data = invalid_data

    def __str__(self):
        return _('Invalid repo metadata [%(data)s]' % {'data' : str(self.invalid_data)})

class DuplicateRepoId(Exception):
    """
    Raised when a repository create conflicts with an existing repository ID.
    """
    def __init__(self, duplicate_id):
        Exception.__init__(self)
        self.duplicate_id = duplicate_id

    def __str__(self):
        return _('Existing repository with ID [%(repo_id)s]') % {'repo_id' : self.duplicate_id}

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

        existing_repo = list(Repo.get_collection().find({'id' : repo_id}))
        if len(existing_repo) > 0:
            raise DuplicateRepoId(repo_id)

        if notes is not None and not isinstance(notes, dict):
            raise InvalidRepoMetadata(notes)

        # Use the ID for the display name if one was not specified
        display_name = display_name or repo_id

        # Creation
        create_me = Repo(repo_id, display_name, description, notes)
        Repo.get_collection().save(create_me, safe=True)

    def delete_repo(self, repo_id, delete_content=True):
        """
        Deletes the given repository, optionally requesting the associated
        importer clean up any content in the repository. If there is no
        repository with the given ID, this call does nothing.

        @param repo_id: identifies the repo being deleted
        @type  repo_id: str

        @param delete_content: indicates if the repository's content should
                               be deleted as well
        @type  delete_content: bool
        """

        # Validation
        found = list(Repo.get_collection().find({'id' : repo_id}))
        if len(found) is 0:
            _LOG.warn('Delete called on a non-existent repository [%(id)s]. Nothing to do.' % {'id' : repo_id})
            return

        # TODO: call to importer to delete content

        # Database Update
        Repo.get_collection().remove({'id' : repo_id})

def is_repo_id_valid(repo_id):
    """
    @return: true if the repo ID is valid; false otherwise
    @rtype:  bool
    """
    result = _REPO_ID_REGEX.match(repo_id) is not None
    return result
