# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License
# (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied, including the
# implied warranties of MERCHANTABILITY, NON-INFRINGEMENT, or FITNESS FOR A
# PARTICULAR PURPOSE.
# You should have received a copy of GPLv2 along with this software; if not,
# see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

import logging
import os
import shutil
import sys

from celery import task
from pymongo.errors import DuplicateKeyError

from pulp.common.plugins import distributor_constants
from pulp.server import exceptions as pulp_exceptions
from pulp.server.async.tasks import Task
from pulp.server.db.model.repo_group import RepoGroup
from pulp.server.db.model.repository import Repo
from pulp.server.managers.repo import _common as common_utils
from pulp.server.managers.repo.group.distributor import RepoGroupDistributorManager


logger = logging.getLogger(__name__)


class RepoGroupManager(object):
    @staticmethod
    def create_repo_group(group_id, display_name=None, description=None, repo_ids=None, notes=None):
        """
        Create a new repo group.
        :param group_id: unique id of the repo group
        :param display_name: display name of the repo group
        :type  display_name: str or None
        :param description: description of the repo group
        :type  description: str or None
        :param repo_ids: list of ids for repos initially belonging to the repo group
        :type  repo_ids: list or None
        :param notes: notes for the repo group
        :type  notes: dict or None
        :return: SON representation of the repo group
        :rtype: bson.SON
        """
        collection = RepoGroup.get_collection()
        repo_group = RepoGroup(group_id, display_name, description, repo_ids, notes)
        try:
            collection.insert(repo_group, safe=True)
        except DuplicateKeyError:
            raise pulp_exceptions.DuplicateResource(group_id), None, sys.exc_info()[2]
        group = collection.find_one({'id': group_id})
        return group

    @staticmethod
    def create_and_configure_repo_group(group_id, display_name=None, description=None,
                                        repo_ids=None, notes=None, distributor_list=None):
        """
        Create a new repository group and add distributors in a single call. This is equivalent to
        calling RepoGroupManager.create_repo_group and then
        RepoGroupDistributorManager.add_distributor for each distributor in the distributor list.

        :param group_id: unique id of the repository group
        :type group_id: str
        :param display_name: user-friendly name of the repository id
        :type display_name: str or None
        :param description: description of the repository group
        :type description: str or None
        :param repo_ids: the list of repository ids in this repository group
        :type repo_ids: list of str or None
        :param notes: A collection of key=value pairs
        :type notes: dict or None
        :param distributor_list: A list of dictionaries used to add distributors. The following keys
                                 are expected: from pulp.common.constants: DISTRIBUTOR_TYPE_ID_KEY,
                                 DISTRIBUTOR_CONFIG_KEY, and DISTRIBUTOR_ID_KEY, which should hold
                                 values str, dict, and str or None
        :type distributor_list: list of dict
        :return: SON representation of the repo group
        :rtype: bson.SON
        """
        if distributor_list is None:
            distributor_list = ()

        # Validate the distributor list before creating a repo group
        if not isinstance(distributor_list, (list, tuple)) or not \
                all(isinstance(dist, dict) for dist in distributor_list):
            raise pulp_exceptions.InvalidValue(['distributor_list'])

        # Create the repo group using the vanilla group create method
        repo_group = RepoGroupManager.create_repo_group(group_id, display_name, description,
                                                        repo_ids, notes)

        for distributor in distributor_list:
            try:
                # Attempt to add the distributor to the group.
                type_id = distributor.get(distributor_constants.DISTRIBUTOR_TYPE_ID_KEY)
                plugin_config = distributor.get(distributor_constants.DISTRIBUTOR_CONFIG_KEY)
                distributor_id = distributor.get(distributor_constants.DISTRIBUTOR_ID_KEY)
                RepoGroupDistributorManager.add_distributor(group_id, type_id, plugin_config,
                                                            distributor_id)
            except Exception, e:
                # If an exception occurs, pass it on after cleaning up the repository group
                logger.exception('Exception adding distributor to repo group [%s]; the group will'
                               ' be deleted' % group_id)
                RepoGroupManager.delete_repo_group(group_id)
                raise e, None, sys.exc_info()[2]

        return repo_group

    @staticmethod
    def update_repo_group(group_id, **updates):
        """
        Update an existing repo group.
        Valid keyword arguments are:
         * display_name
         * description
         * notes

        For notes, provide a dict with key:value pairs for changes only. It is
        not necessary to provide the entire field value. If a value is empty or
        otherwise evaluates to False, that key will be unset.

        @param group_id: unique id of the repo group to update
        @type group_id: str
        @param updates: keyword arguments of attributes to update
        @return: SON representation of the updated repo group
        @rtype:  L{bson.SON}
        """
        collection = validate_existing_repo_group(group_id)
        keywords = updates.keys()
        # validate keywords
        valid_keywords = set(('display_name', 'description', 'notes'))
        invalid_keywords = set(keywords) - valid_keywords
        if invalid_keywords:
            raise pulp_exceptions.InvalidValue(list(invalid_keywords))

        # handle notes as a delta against the existing notes attribute
        notes = updates.pop('notes', None)
        if notes:
            unset_dict = {}
            for key, value in notes.iteritems():
                newkey = 'notes.%s' % key
                if value:
                    updates[newkey] = value
                else:
                    unset_dict[newkey] = value

            if unset_dict:
                collection.update({'id': group_id}, {'$unset': unset_dict},
                    safe=True)

        if updates:
            collection.update({'id': group_id}, {'$set': updates}, safe=True)
        group = collection.find_one({'id': group_id})
        return group

    @staticmethod
    def delete_repo_group(group_id):
        """
        Delete a repo group.
        @param group_id: unique id of the repo group to delete
        @type group_id: str
        """
        collection = validate_existing_repo_group(group_id)

        # Delete all distributors on the group
        distributors = RepoGroupDistributorManager.find_distributors(group_id)
        for distributor in distributors:
            RepoGroupDistributorManager.remove_distributor(group_id, distributor['id'])

        # Delete the working directory for the group
        working_dir = common_utils.repo_group_working_dir(group_id)
        if os.path.exists(working_dir):
            try:
                shutil.rmtree(working_dir)
            except Exception:
                logger.exception('Error while deleting working dir [%s] for repo group [%s]' % (working_dir, group_id))
                raise

        # Delete from the database
        collection.remove({'id': group_id}, safe=True)

    def remove_repo_from_groups(self, repo_id, group_ids=None):
        """
        Remove a repo from the list of repo groups provided.
        If no repo groups are specified, remove the repo from all repo groups
        its currently in.
        (idempotent: useful when deleting repositories)
        @param repo_id: unique id of the repo to remove from repo groups
        @type  repo_id: str
        @param group_ids: list of repo group ids to remove the repo from
        @type  group_ids: list of None
        """
        spec = {}
        if group_ids is not None:
            spec = {'id': {'$in': group_ids}}
        collection = RepoGroup.get_collection()
        collection.update(spec, {'$pull': {'repo_ids': repo_id}}, multi=True, safe=True)

    @staticmethod
    def associate(group_id, criteria):
        """
        Associate a set of repos, that match the passed in criteria, to a repo group.
        @param group_id: unique id of the group to associate repos to
        @type  group_id: str
        @param criteria: Criteria instance representing the set of repos to associate
        @type  criteria: L{pulp.server.db.model.criteria.Criteria}
        """
        group_collection = validate_existing_repo_group(group_id)
        repo_collection = Repo.get_collection()
        cursor = repo_collection.query(criteria)
        repo_ids = [r['id'] for r in cursor]
        if not repo_ids:
            return
        group_collection.update({'id': group_id},
                                {'$addToSet': {'repo_ids': {'$each': repo_ids}}},
                                safe=True)

    @staticmethod
    def unassociate(group_id, criteria):
        """
        Unassociate a set of repos, that match the passed in criteria, from a repo group.
        @param group_id: unique id of the group to unassociate repos from
        @type  group_id: str
        @param criteria: Criteria instance representing the set of repos to unassociate
        @type  criteria: L{pulp.server.db.model.criteria.Criteria}
        """
        group_collection = validate_existing_repo_group(group_id)
        repo_collection = Repo.get_collection()
        cursor = repo_collection.query(criteria)
        repo_ids = [r['id'] for r in cursor]
        if not repo_ids:
            return
        group_collection.update({'id': group_id},
                                # for some reason, pymongo 1.9 doesn't like this
                                #{'$pull': {'repo_ids': {'$in': repo_ids}}},
                                {'$pullAll': {'repo_ids': repo_ids}},
                                safe=True)

    def add_notes(self, group_id, notes):
        """
        Add a set of notes to a repo group.
        @param group_id: unique id of the group to add notes to
        @type  group_id: str
        @param notes: notes to add to the repo group
        @type  notes: dict
        """
        group_collection = validate_existing_repo_group(group_id)
        set_doc = dict(('notes.' + k, v) for k, v in notes.items())
        group_collection.update({'id': group_id}, {'$set': set_doc}, safe=True)

    def remove_notes(self, group_id, keys):
        """
        Remove a set of notes from a repo group.
        @param group_id: unique id of the group to remove notes from
        @type  group_id: str
        @param keys: list of note keys to remove
        @type  keys: list
        """
        group_collection = validate_existing_repo_group(group_id)
        unset_doc = dict(('notes.' + k, 1) for k in keys)
        group_collection.update({'id': group_id}, {'$unset': unset_doc}, safe=True)

    def set_note(self, group_id, key, value):
        """
        Set a single key and value pair in a repo group's notes.
        @param group_id: unique id of the repo group to set a note on
        @type  group_id: str
        @param key: note key
        @type  key: immutable
        @param value: note value
        """
        self.add_notes(group_id, {key: value})

    def unset_note(self, group_id, key):
        """
        Unset a single key and value pair in a repo group's notes.
        @param group_id: unique id of the repo group to unset a note on
        @type  group_id: str
        @param key: note key
        @type  key: immutable
        """
        self.remove_notes(group_id, [key])


associate = task(RepoGroupManager.associate, base=Task, ignore_result=True)
create_and_configure_repo_group = task(RepoGroupManager.create_and_configure_repo_group, base=Task)
delete_repo_group = task(RepoGroupManager.delete_repo_group, base=Task, ignore_result=True)
unassociate = task(RepoGroupManager.unassociate, base=Task, ignore_result=True)
update_repo_group = task(RepoGroupManager.update_repo_group, base=Task)


def validate_existing_repo_group(group_id):
    """
    Validate the existence of a repo group, given its id.
    Returns the repo group db collection upon successful validation,
    raises an exception upon failure
    @param group_id: unique id of the repo group to validate
    @type  group_id: str
    @return: repo group db collection
    @rtype:  L{pulp.server.db.connection.PulpCollection}
    @raise:  L{pulp.server.exceptions.MissingResource}
    """
    collection = RepoGroup.get_collection()
    repo_group = collection.find_one({'id': group_id})
    if repo_group is not None:
        return collection
    raise pulp_exceptions.MissingResource(repo_group=group_id)
