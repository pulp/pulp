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

from gettext import gettext as _
import logging
import os
import re
import shutil
import sys

from celery import task
import pymongo

from pulp.server.async.tasks import Task
from pulp.server.db.model.repository import (Repo, RepoDistributor, RepoImporter, RepoContentUnit,
                                             RepoSyncResult, RepoPublishResult)
from pulp.server.dispatch import factory as dispatch_factory
from pulp.server.exceptions import DuplicateResource, InvalidValue, MissingResource, \
    PulpExecutionException, MultipleOperationsPostponed
from pulp.server.itineraries.repository import distributor_update_itinerary
from pulp.server.webservices import execution
import pulp.server.managers.factory as manager_factory
import pulp.server.managers.repo._common as common_utils


_REPO_ID_REGEX = re.compile(r'^[.\-_A-Za-z0-9]+$') # letters, numbers, underscore, hyphen
_DISTRIBUTOR_ID_REGEX = _REPO_ID_REGEX # for now, use the same constraints


logger = logging.getLogger(__name__)


class RepoManager(object):
    """
    Performs repository related functions relating to both CRUD operations and
    actions performed on or by repositories.
    """
    @staticmethod
    def create_repo(repo_id, display_name=None, description=None, notes=None):
        """
        Creates a new Pulp repository that is not associated with any importers
        or distributors (those are added later through separate calls).

        :param repo_id: unique identifier for the repo
        :type  repo_id: str

        :param display_name: user-friendly name for the repo
        :type  display_name: str

        :param description: user-friendly text describing the repo's contents
        :type  description: str

        :param notes: key-value pairs to programmatically tag the repo
        :type  notes: dict

        :raise DuplicateResource: if there is already a repo with the requested ID
        :raise InvalidValue: if any of the fields are unacceptable
        """

        existing_repo = Repo.get_collection().find_one({'id' : repo_id})
        if existing_repo is not None:
            raise DuplicateResource(repo_id)

        if repo_id is None or not is_repo_id_valid(repo_id):
            raise InvalidValue(['repo_id'])

        if notes is not None and not isinstance(notes, dict):
            raise InvalidValue(['notes'])

        # Use the ID for the display name if one was not specified
        display_name = display_name or repo_id

        # Creation
        create_me = Repo(repo_id, display_name, description, notes)
        Repo.get_collection().save(create_me, safe=True)

        # Retrieve the repo to return the SON object
        created = Repo.get_collection().find_one({'id' : repo_id})

        return created

    @staticmethod
    def create_and_configure_repo(repo_id, display_name=None, description=None,
                                  notes=None, importer_type_id=None,
                                  importer_repo_plugin_config=None, distributor_list=()):
        """
        Aggregate method that will create a repository and add importers and
        distributors in a single call. If there is an issue adding any of
        the importers or distributors,

        This call will aggregate calls to RepoImporterManager.set_importer
        and RepoDistributorManager.add_distributor. Documentation for those
        methods should be consulted for more information on the parameters to
        this method that correspond to those calls.

        Multiple distributors can be created in this call. Each distributor
        is specified as a dict with the following keys:

          distributor_type - ID of the type of distributor being added
          distributor_config - values sent to the distributor when used by
                               this repository
          auto_publish - boolean indicating if the distributor should automatically
                         publish with every sync; defaults to False
          distributor_id - used to refer to the distributor later; if omitted,
                           one will be generated

        :param repo_id: unique identifier for the repo
        :type  repo_id: str

        :param display_name: user-friendly name for the repo
        :type  display_name: str

        :param description: user-friendly text describing the repo's contents
        :type  description: str

        :param notes: key-value pairs to programmatically tag the repo
        :type  notes: dict

        :param importer_type_id: if specified, an importer with this type ID will
               be added to the repo
        :type  importer_type_id: str

        :param distributor_list: list of dicts describing the distributors to
               add; more details in the docstring above
        :type  distributor_list: list

        :raise DuplicateResource: if there is already a repo with the requested ID
        :raise InvalidValue: if any of the non-ID fields is unacceptable
        """

        # Let any exceptions out of this call simply bubble up, there's nothing
        # special about this step.
        repo = RepoManager.create_repo(repo_id, display_name=display_name, description=description,
                                       notes=notes)

        # Add the importer if it's specified. If that fails, delete the repository
        # before re-raising the exception.
        if importer_type_id is not None:
            importer_manager = manager_factory.repo_importer_manager()
            try:
                importer_manager.set_importer(repo_id, importer_type_id,
                                              importer_repo_plugin_config)
            except Exception, e:
                logger.exception(
                    'Exception adding importer to repo [%s]; the repo will be deleted' % repo_id)
                RepoManager.delete_repo(repo_id)
                raise e, None, sys.exc_info()[2]

        # Regardless of how many distributors are successfully added, or if an
        # importer was added, we only need a single call to delete_repo in the
        # error block. That call will take care of all of the cleanup.
        distributor_manager = manager_factory.repo_distributor_manager()

        if distributor_list is not None and not isinstance(distributor_list, (list, tuple)):
            RepoManager.delete_repo(repo_id)
            raise InvalidValue(['distributor_list'])

        for distributor in distributor_list or []:
            if not isinstance(distributor, dict):
                RepoManager.delete_repo(repo_id)
                raise InvalidValue(['distributor_list'])

            try:
                # Don't bother with any validation here, the manager will run it
                type_id = distributor.get('distributor_type')
                plugin_config = distributor.get('distributor_config')
                auto_publish = distributor.get('auto_publish', False)
                distributor_id = distributor.get('distributor_id')

                distributor_manager.add_distributor(repo_id, type_id, plugin_config, auto_publish,
                                                    distributor_id)
            except Exception, e:
                logger.exception('Exception adding distributor to repo [%s]; the repo will be deleted' % repo_id)
                RepoManager.delete_repo(repo_id)
                raise e, None, sys.exc_info()[2]

        return repo

    @staticmethod
    def delete_repo(repo_id):
        """
        Deletes the given repository, optionally requesting the associated
        importer clean up any content in the repository.

        :param repo_id: identifies the repo being deleted
        :type  repo_id: str

        :raise MissingResource: if the given repo does not exist
        :raise OperationFailed: if any part of the delete process fails;
               the exception will contain information on which sections failed
        """

        # Validation
        found = Repo.get_collection().find_one({'id' : repo_id})
        if found is None:
            raise MissingResource(repo_id)

        # With so much going on during a delete, it's possible that a few things
        # could go wrong while others are successful. We track lesser errors
        # that shouldn't abort the entire process until the end and then raise
        # an exception describing the incompleteness of the delete. The exception
        # arguments are captured as the second element in the tuple, but the user
        # will have to look at the server logs for more information.
        error_tuples = [] # tuple of failed step and exception arguments

        # Remove any scheduled activities
        scheduler = dispatch_factory.scheduler()

        importer_manager = manager_factory.repo_importer_manager()
        importers = importer_manager.get_importers(repo_id)
        if importers:
            for schedule_id in importer_manager.list_sync_schedules(repo_id):
                scheduler.remove(schedule_id)

        distributor_manager = manager_factory.repo_distributor_manager()
        for distributor in distributor_manager.get_distributors(repo_id):
            for schedule_id in distributor_manager.list_publish_schedules(repo_id,
                                                                          distributor['id']):
                scheduler.remove(schedule_id)

        # Inform the importer
        importer_coll = RepoImporter.get_collection()
        repo_importer = importer_coll.find_one({'repo_id' : repo_id})
        if repo_importer is not None:
            try:
                importer_manager.remove_importer(repo_id)
            except Exception, e:
                logger.exception('Error received removing importer [%s] from repo [%s]' % (
                    repo_importer['importer_type_id'], repo_id))
                error_tuples.append( (_('Importer Delete Error'), e.args) )

        # Inform all distributors
        distributor_coll = RepoDistributor.get_collection()
        repo_distributors = list(distributor_coll.find({'repo_id' : repo_id}))
        for repo_distributor in repo_distributors:
            try:
                distributor_manager.remove_distributor(repo_id, repo_distributor['id'])
            except Exception, e:
                logger.exception('Error received removing distributor [%s] from repo [%s]' % (
                    repo_distributor['id'], repo_id))
                error_tuples.append( (_('Distributor Delete Error'), e.args))

        # Delete the repository working directory
        repo_working_dir = common_utils.repository_working_dir(repo_id, mkdir=False)
        if os.path.exists(repo_working_dir):
            try:
                shutil.rmtree(repo_working_dir)
            except Exception, e:
                logger.exception('Error while deleting repo working dir [%s] for repo [%s]' % (
                    repo_working_dir, repo_id))
                error_tuples.append( (_('Filesystem Cleanup Error'), e.args))

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
        except Exception, e:
            msg = _('Error updating one or more database collections while removing repo [%(r)s]')
            msg = msg % {'r': repo_id}
            logger.exception(msg)
            error_tuples.append( (_('Database Removal Error'), e.args))

        # remove the repo from any groups it was a member of
        group_manager = manager_factory.repo_group_manager()
        group_manager.remove_repo_from_groups(repo_id)

        if len(error_tuples) > 0:
            raise PulpExecutionException(error_tuples)

    @staticmethod
    def update_repo(repo_id, delta):
        """
        Updates metadata about the given repository. Only the following
        fields may be updated through this call:
        * display_name
        * description

        Other fields found in delta will be ignored.

        :param repo_id: identifies the repo
        :type  repo_id: str

        :param delta: list of attributes and their new values to change
        :type  delta: dict

        :raise MissingResource: if there is no repo with repo_id
        """

        repo_coll = Repo.get_collection()

        repo = repo_coll.find_one({'id' : repo_id})
        if repo is None:
            raise MissingResource(repo_id)

        # There are probably all sorts of clever ways to not hard code the
        # fields here, but frankly, there are so few that this is just easier.
        # It also makes it very simple to ignore any rogue keys that are in delta.

        if 'display_name' in delta:
            repo['display_name'] = delta['display_name']

        if 'description' in delta:
            repo['description'] = delta['description']

        if 'notes' in delta:

            # Merge in the notes included in the delta using the following rules:
            # * If the delta value is non-None, set/overwrite the value in the
            #   repo's note
            # * If the delta valus is None, remove the note from the repo's note

            existing_notes = repo['notes'] or {}

            for k, v in delta['notes'].items():
                if v is None:
                    existing_notes.pop(k, None)
                else:
                    existing_notes[k] = v

            repo['notes'] = existing_notes

        repo_coll.save(repo, safe=True)

        return repo

    @staticmethod
    def update_unit_count(repo_id, unit_type_id, delta):
        """
        Updates the total count of units associated with the repo. Each repo has
        an attribute 'content_unit_counts' which is a dict where keys are
        content type IDs, and values are the number of content units of that
        type in the repository.

        {'rpm': 12, 'srpm': 3}

        :param repo_id: identifies the repo
        :type  repo_id: str

        :param unit_type_id: identifies the unit type to update
        :type  unit_type_id: str

        :param delta: amount by which to change the total count
        :type  delta: int
        """
        spec = {'id' : repo_id}
        operation = {'$inc' : {'content_unit_counts.%s' % unit_type_id: delta}}
        repo_coll = Repo.get_collection()

        if delta:
            try:
                repo_coll.update(spec, operation, safe=True)
            except pymongo.errors.OperationFailure:
                message = 'There was a problem updating repository %s' % repo_id
                raise PulpExecutionException(message), None, sys.exc_info()[2]

    @staticmethod
    def update_repo_and_plugins(repo_id, repo_delta, importer_config,
                                distributor_configs):
        """
        Aggregate method that will update one or more of the following:
        * Repository metadata
        * Importer config
        * Zero or more distributors on the repository

        All of the above pieces do not need to be specified. If a piece is
        omitted it's configuration is not touched, nor is it removed from
        the repository. The same holds true for the distributor_configs dict,
        not every distributor must be represented.

        This call will attempt the updates in the order listed above. If an
        exception occurs during any of these steps, the updates stop and the
        exception is immediately raised. Any updates that have already taken
        place are not rolled back.

        This call will call out to RepoImporterManager.update_importer_config.
        Documentation for that method, especially possible exceptions, should be
        consulted for more information.

        Distributor updates will happen asynchronously as there could be a
        very large number of consumers to update and the repo update call
        is usually made synchronously.

        :param repo_id: unique identifier for the repo
        :type  repo_id: str

        :param repo_delta: list of attributes and their new values to change;
               if None, no attempt to update the repo's metadata will be made
        :type  repo_delta: dict, None

        :param importer_config: new configuration to use for the repo's importer;
               if None, no attempt will be made to update the importer
        :type  importer_config: dict, None

        :param distributor_configs: mapping of distributor ID to the new configuration
               to set for it
        :type  distributor_configs: dict, None

        :return: updated repository object, same as returned from update_repo
        """

        # Repo Update
        if repo_delta is None:
            repo_delta = {}
        repo = RepoManager.update_repo(repo_id, repo_delta)

        # Importer Update
        if importer_config is not None:
            importer_manager = manager_factory.repo_importer_manager()
            importer_manager.update_importer_config(repo_id, importer_config)

        # Distributor Update
        if distributor_configs is not None:
            distributor_manager = manager_factory.repo_distributor_manager()
            for dist_id, dist_config in distributor_configs.items():
                # Update the distributor config to ensure that errors are reported immediately
                distributor_manager.update_distributor_config(repo_id, dist_id, dist_config)
                # Use the itinerary to update the bindings on the consumers.
                # This will duplicate the distributor update command.
                # The duplication should be removed once we have a tasking system that
                # supports a better method of tracking grouped tasks
                call_requests = distributor_update_itinerary(repo_id, dist_id, dist_config)
                # The requests may not run immediately which is fine.  Since we have
                # no overall tracking of these requests we  have to eat the exception.
                try:
                    execution.execute_multiple(call_requests)
                except MultipleOperationsPostponed:
                    pass

        return repo

    def get_repo_scratchpad(self, repo_id):
        """
        Retrieves the contents of the given repository's scratchpad.

        :param repo_id: identifies the repo
        :type  repo_id: str

        :raise MissingResource: if there is no repo with repo_id
        """

        repo_coll = Repo.get_collection()
        repo = repo_coll.find_one({'id' : repo_id})

        if repo is None:
            raise MissingResource(repo_id)

        return dict(repo['scratchpad'])

    def set_repo_scratchpad(self, repo_id, scratchpad):
        """
        Saves the given contents to the repository's scratchpad. There is no
        attempt to merge in the provided with the current scratchpad, it is
        simply overridden.  When possible, use update_scratchpad() instead.

        :param repo_id: identifies the repo
        :type  repo_id: str

        :param scratchpad: new value to save in the scratchpad; must be a dict.

        :raise MissingResource: if there is no repo with repo_id
        """
        if not isinstance(scratchpad, dict):
            raise ValueError('scratchpad must be a dict')
        collection = Repo.get_collection()
        result = collection.update({'id': repo_id}, {'$set': {'scratchpad': scratchpad}}, safe=True)
        if result['n'] == 0:
            raise MissingResource(repo_id=repo_id)

    def update_repo_scratchpad(self, repo_id, scratchpad):
        """
        Update the repository scratchpad with the specified key-value pairs.
        New keys are added, existing keys are updated.

        :param repo_id: A repository ID
        :type repo_id: str

        :param scratchpad: a dict used to update the scratchpad.
        :type scratchpad: dict

        :raise MissingResource: if there is no repo with repo_id
        """
        properties = {}
        for k, v in scratchpad.items():
            key = 'scratchpad.%s' % k
            properties[key] = v
        collection = Repo.get_collection()
        result = collection.update({'id': repo_id}, {'$set': properties}, safe=True)
        if result['n'] == 0:
            raise MissingResource(repo_id=repo_id)

    @staticmethod
    def rebuild_content_unit_counts(repo_ids=None):
        """
        WARNING: This might take a long time, and it should not be used unless
        absolutely necessary. Not responsible for melted servers.

        This will iterate through the given repositories, which defaults to ALL
        repositories, and recalculate the content unit counts for each content
        type.

        This method is called from platform migration 0004, so consult that
        migration before changing this method.

        :param repo_ids:    list of repository IDs. DEFAULTS TO ALL REPO IDs!!!
        :type  repo_ids:    list
        """
        association_collection = RepoContentUnit.get_collection()
        repo_collection = Repo.get_collection()

        # default to all repos if none were specified
        if not repo_ids:
            repo_ids = [repo['id'] for repo in repo_collection.find(fields=['id'])]

        logger.info('regenerating content unit counts for %d repositories' % len(repo_ids))

        for repo_id in repo_ids:
            logger.debug('regenerating content unit count for repository "%s"' % repo_id)
            counts = {}
            cursor = association_collection.find({'repo_id':repo_id})
            type_ids = cursor.distinct('unit_type_id')
            cursor.close()
            for type_id in type_ids:
                spec = {'repo_id': repo_id, 'unit_type_id': type_id}
                counts[type_id] = association_collection.find(spec).count()
            repo_collection.update({'id': repo_id}, {'$set':{'content_unit_counts': counts}}, safe=True)


create_and_configure_repo = task(RepoManager.create_and_configure_repo, base=Task)
delete_repo = task(RepoManager.delete_repo, base=Task, ignore_result=True)
update_repo_and_plugins = task(RepoManager.update_repo_and_plugins, base=Task)


def is_repo_id_valid(repo_id):
    """
    :return: true if the repo ID is valid; false otherwise
    :rtype:  bool
    """
    result = _REPO_ID_REGEX.match(repo_id) is not None
    return result
