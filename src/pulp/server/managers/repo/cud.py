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
import uuid

from pulp.server.db.model.gc_repository import Repo, RepoDistributor, RepoImporter
import pulp.server.content.manager as content_manager

# -- constants ----------------------------------------------------------------

_REPO_ID_REGEX = re.compile(r'^[\-_A-Za-z0-9]+$') # letters, numbers, underscore, hyphen
_DISTRIBUTOR_ID_REGEX = _REPO_ID_REGEX # for now, use the same constraints

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

class InvalidDistributorId(Exception):
    """
    Indicates a given distributor ID was invalid.
    """
    def __init__(self, invalid_distributor_id):
        Exception.__init__(self)
        self.invalid_distributor_id = invalid_distributor_id

    def __str__(self):
        return _('Invalid distributor ID [%(id)s]' % {'id' : self.invalid_distributor_id})

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

class MissingRepo(Exception):
    """
    Indicates an operation was requested against a repo that doesn't exist.
    """
    def __init__(self, repo_id):
        Exception.__init__(self)
        self.repo_id = repo_id

    def __str__(self):
        return _('No repository with ID [%(id)s]' % {'id' : self.repo_id})

class MissingImporter(Exception):
    """
    Indicates an importer was requested that does not exist.
    """
    def __init__(self, importer_name):
        Exception.__init__(self)
        self.importer_name = importer_name

    def __str__(self):
        return _('No importer with name [%(name)s]' % {'name' : self.importer_name})

class MissingDistributor(Exception):
    """
    Indicates a distributor was requested that does not exist.
    """
    def __init__(self, distributor_name):
        Exception.__init__(self)
        self.distributor_name = distributor_name

    def __str__(self):
        return _('No distributor with name [%(name)s]' % {'name' : self.distributor_name})

# -- manager ------------------------------------------------------------------

class RepoManager:
    """
    Performs repository related functions relating to both CRUD operations and
    actions performed on or by repositories.
    """

    # -- creation and configuration -------------------------------------------

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

    def set_importer(self, repo_id, importer_type_name, importer_config):
        """
        Configures an importer to be used for the given repository.

        Keep in mind this method is written assuming single importer for a repo.
        The domain model technically supports multiple importers, but this
        call is what enforces the single importer behavior.

        @param repo_id: identifies the repo
        @type  repo_id; str

        @param importer_type_name: identifies the type of importer being added;
                                   must correspond to an importer loaded at
                                   server startup
        @type  importer_type_name: str

        @param importer_config: configuration values for the importer; may be None
        @type  importer_config: dict

        @raises MissingRepo: if repo_id does not represent a valid repo
        @raises MissingImporter: if there is no importer with importer_type_name
        """

        repo_coll = Repo.get_collection()
        importer_coll = RepoImporter.get_collection()

        # Validation
        repo = repo_coll.find_one({'id' : repo_id})
        if repo is None:
            raise MissingRepo(repo_id)

        if not content_manager.is_valid_importer(importer_type_name):
            raise MissingImporter(importer_type_name)

        # Remove old importer if one exists
        existing_repo_importers = list(importer_coll.find({'repo_id' : repo_id}))
        if len(existing_repo_importers) > 0:
            for importer in existing_repo_importers:
                importer_coll.remove(importer, safe=True)

        # Database Update
        importer_id = importer_type_name # use the importer name as its repo ID

        importer = RepoImporter(repo_id, importer_id, importer_type_name, importer_config)
        importer_coll.save(importer, safe=True)

    def add_distributor(self, repo_id, distributor_type_id, distributor_config,
                        auto_distribute, distributor_id=None):
        """
        Adds an association from the given repository to a distributor. The
        association will be tracked through the distributor_id; each distributor
        on a given repository must have a unique ID. If this is not specified,
        one will be generated. If a distributor already exists on the repo for
        the given ID, the existing one will be removed and replaced with the
        newly configured one.

        @param repo_id: identifies the repo
        @type  repo_id: str

        @param distributor_type_id: identifies the distributor; must correspond
                                    to a distributor loaded at server startup
        @type  distributor_type_id: str

        @param distributor_config: configuration the repo will use with this
                                   distributor; may be None
        @type distributor_config:  dict

        @param auto_distribute: if true, this distributor will be invoked at
                                the end of every sync
        @type  auto_distribute: bool

        @param distributor_id: unique ID to refer to this distributor for this repo
        @type  distributor_id: str

        @return: ID assigned to the distributor (only valid in conjunction with the repo)

        @raises MissingRepo: if the given repo_id does not refer to a valid repo
        @raises MissingDistributor: if the given distributor type ID does not
                                    refer to a valid distributor
        @raises InvalidDistributorId: if the distributor ID is provided and unacceptable
        """

        repo_coll = Repo.get_collection()
        distributor_coll = RepoDistributor.get_collection()

        # Validation
        repo = repo_coll.find_one({'id' : repo_id})
        if repo is None:
            raise MissingRepo(repo_id)

        if not content_manager.is_valid_distributor(distributor_type_id):
            raise MissingDistributor(distributor_type_id)

        # Determine the ID for this distributor on this repo; will be
        # unique for all distributors on this repository but not globally
        if distributor_id is None:
            distributor_id = str(uuid.uuid4())
        else:
            # Validate if one was passed in
            if not is_distributor_id_valid(distributor_id):
                raise InvalidDistributorId(distributor_id)

        # If a distributor already exists at that ID, remove it from the database
        # as it will be replaced in this method
        existing_distributor = distributor_coll.find_one({'repo_id' : repo_id, 'id' : distributor_id})
        if existing_distributor is not None:
            distributor_coll.remove(existing_distributor, safe=True)

        # Database Update
        distributor = RepoDistributor(repo_id, distributor_id, distributor_type_id, distributor_config, auto_distribute)
        distributor_coll.save(distributor, safe=True)

        return distributor_id

    def remove_distributor(self, repo_id, distributor_id):
        """
        Removes a distributor from a repository, optionally requesting the
        distributor to unpublish the repository first. If there is no
        distributor with the given ID on the repository, this call has no effect
        and will not raise an error.

        @param repo_id: identifies the repo
        @type  repo_id: str

        @param distributor_id: identifies the distributor to delete
        @type  distributor_id: str

        @raises MissingRepo: if repo_id doesn't correspond to a valid repo
        """

        repo_coll = Repo.get_collection()
        distributor_coll = RepoDistributor.get_collection()

        # Validation
        repo = repo_coll.find_one({'id' : repo_id})
        if repo is None:
            raise MissingRepo(repo_id)

        distributor = distributor_coll.find_one({'repo_id' : repo_id, 'id' : distributor_id})

        # TODO: add call to unpublish on the distributor if indicated

        # Database Update
        distributor_coll.remove(distributor, safe=True)

# -- functions ----------------------------------------------------------------

def is_repo_id_valid(repo_id):
    """
    @return: true if the repo ID is valid; false otherwise
    @rtype:  bool
    """
    result = _REPO_ID_REGEX.match(repo_id) is not None
    return result

def is_distributor_id_valid(distributor_id):
    """
    @return: true if the distributor ID is valid; false otherwise
    @rtype:  bool
    """
    result = _DISTRIBUTOR_ID_REGEX.match(distributor_id) is not None
    return result