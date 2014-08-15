# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
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
Contains binding management classes
"""

from logging import getLogger
from time import time

from celery import task
from pymongo.errors import DuplicateKeyError

from pulp.server.async.tasks import Task
from pulp.server.db.model.consumer import Bind
from pulp.server.exceptions import MissingResource, InvalidValue
from pulp.server.managers import factory


_LOG = getLogger(__name__)


class BindManager(object):
    """
    Manage consumer repo/distributor bind.
    Both bind/unbind collaboration with the agent is done
    as "best effort".  Reliability is achieved though a
    combination of notifications originated here and agent
    initiated efforts to ensure accurate reflection of binds.
    """

    @staticmethod
    def bind_id(consumer_id, repo_id, distributor_id):
        return dict(
            consumer_id=consumer_id,
            repo_id=repo_id,
            distributor_id=distributor_id,
        )

    @staticmethod
    def bind(consumer_id, repo_id, distributor_id, notify_agent, binding_config):
        """
        Bind consumer to a specific distributor associated with
        a repository.  This call is idempotent.
        :param consumer_id: uniquely identifies the consumer.
        :type  consumer_id: str
        :param repo_id: uniquely identifies the repository.
        :type  repo_id: str
        :param distributor_id: uniquely identifies a distributor.
        :type  distributor_id: str

        :return: The Bind object
        :rtype:  SON

        :raise MissingResource: when given consumer does not exist.
        :raise InvalidValid:    when the repository or distributor id is invalid, or
        if the notify_agent value is invalid
        """
        # Validation
        missing_values = BindManager._validate_consumer_repo(consumer_id, repo_id, distributor_id)
        if missing_values:
            if 'consumer_id' in missing_values:
                # This is passed in via the URL so a 404 should be raised
                raise MissingResource(consumer_id=missing_values['consumer_id'])
            else:
                # Everything else is a parameter so raise a 400
                raise InvalidValue(missing_values.keys())

        # ensure notify_agent is a boolean
        if not isinstance(notify_agent, bool):
            raise InvalidValue(['notify_agent'])

        # perform the bind
        collection = Bind.get_collection()
        try:
            bind = Bind(consumer_id, repo_id, distributor_id, notify_agent, binding_config)
            collection.save(bind, safe=True)
        except DuplicateKeyError:
            BindManager._update_binding(consumer_id, repo_id, distributor_id, notify_agent,
                                        binding_config)
            BindManager._reset_bind(consumer_id, repo_id, distributor_id)
        # fetch the inserted/updated bind
        bind = BindManager.get_bind(consumer_id, repo_id, distributor_id)
        # update history
        details = {'repo_id':repo_id, 'distributor_id':distributor_id}
        manager = factory.consumer_history_manager()
        manager.record_event(consumer_id, 'repo_bound', details)
        return bind

    @staticmethod
    def _update_binding(consumer_id, repo_id, distributor_id, notify_agent, binding_config):
        """
        Workaround to the way bindings rely on a duplicate key error for supporting rebind.
        This call makes sure the existing binding is updated with the new values for
        notifying the agent and the binding's configuration.

        The parameters are the values passed to the bind() call.
        """

        collection = Bind.get_collection()
        query = BindManager.bind_id(consumer_id, repo_id, distributor_id)
        binding = collection.find_one(query)
        binding['notify_agent'] = notify_agent
        binding['binding_config'] = binding_config
        collection.save(binding, safe=True)

    @staticmethod
    def _reset_bind(consumer_id, repo_id, distributor_id):
        """
        Reset the bind.
        This means resetting the deleted flag and consumer requests.
        Only deleted bindings will be reset.
        @param consumer_id: uniquely identifies the consumer.
        @type consumer_id: str
        @param repo_id: uniquely identifies the repository.
        @type repo_id: str
        @param distributor_id: uniquely identifies a distributor.
        @type distributor_id: str
        """
        collection = Bind.get_collection()
        query = BindManager.bind_id(consumer_id, repo_id, distributor_id)
        query['deleted'] = True
        update = {'$set':{'deleted':False, 'consumer_actions':[]}}
        collection.update(query, update, safe=True)

    @staticmethod
    def unbind(consumer_id, repo_id, distributor_id):
        """
        Unbind a consumer from a specific distributor associated with
        a repository.  This call is idempotent.

        :param consumer_id:     uniquely identifies the consumer.
        :type  consumer_id:     str
        :param repo_id:         uniquely identifies the repository.
        :type  repo_id:         str
        :param distributor_id:  uniquely identifies a distributor.
        :type  distributor_id:  str

        :return: The Bind object
        :rtype:  SON

        :raise MissingResource: if the binding does not exist
        """
        # Validate that the binding exists at all before continuing.
        # This will raise an exception if it it does not.
        BindManager.get_bind(consumer_id, repo_id, distributor_id)

        collection = Bind.get_collection()
        query = BindManager.bind_id(consumer_id, repo_id, distributor_id)
        query['deleted'] = False
        bind = collection.find_one(query)
        if bind is None:
            # idempotent
            return
        BindManager.mark_deleted(consumer_id, repo_id, distributor_id)
        details = {
            'repo_id':repo_id,
            'distributor_id':distributor_id
        }
        manager = factory.consumer_history_manager()
        manager.record_event(consumer_id, 'repo_unbound', details)
        return bind

    def consumer_deleted(self, consumer_id):
        """
        Removes all bindings associated with the specified consumer.
        @param consumer_id: A consumer ID.
        @type consumer_id: str
        """
        collection = Bind.get_collection()
        query = dict(consumer_id=consumer_id)
        collection.remove(query)

    @staticmethod
    def get_bind(consumer_id, repo_id, distributor_id):
        """
        Get a specific bind.
        This method ignores the deleted flag.

        :param consumer_id:     uniquely identifies the consumer.
        :type  consumer_id:     str
        :param repo_id:         uniquely identifies the repository.
        :type  repo_id:         str
        :param distributor_id:  uniquely identifies a distributor.
        :type  distributor_id:  str

        :return: A specific bind.
        :rtype:  SON

        :raise MissingResource: if the binding doesn't exist
        """
        collection = Bind.get_collection()
        bind_id = BindManager.bind_id(consumer_id, repo_id, distributor_id)
        bind = collection.find_one(bind_id)
        if bind is None:
            # If the binding doesn't exist, report which values are not present
            missing_values = BindManager._validate_consumer_repo(consumer_id, repo_id, distributor_id)
            if missing_values:
                raise MissingResource(**missing_values)
            else:
                # In this case, every resource is present, but the consumer isn't bound to that repo/distributor
                raise MissingResource(bind_id=bind_id)
        return bind

    def find_all(self):
        """
        Find all binds where deleted is False.
        @return: A list of all non-deleted bindings
        @rtype: list
        """
        collection = Bind.get_collection()
        query = dict(deleted=False)
        cursor = collection.find(query)
        return list(cursor)

    def find_by_consumer(self, id, repo_id=None):
        """
        Find all non-deleted bindings by Consumer ID.
        @param id: A consumer ID.
        @type id: str
        @param repo_id: An (optional) repository ID.
        @type repo_id: str
        @return: A list of Bind.
        @rtype: list
        """
        collection = Bind.get_collection()
        if repo_id:
            query = dict(consumer_id=id, repo_id=repo_id, deleted=False)
        else:
            query = dict(consumer_id=id, deleted=False)
        cursor = collection.find(query)
        return list(cursor)

    def find_by_repo(self, id):
        """
        Find all non-deleted bindings by Repo ID.
        @param id: A Repo ID.
        @type id: str
        @return: A list of Bind.
        @rtype: list
        """
        collection = Bind.get_collection()
        query = dict(repo_id=id, deleted=False)
        cursor = collection.find(query)
        return list(cursor)

    def find_by_distributor(self, repo_id, distributor_id):
        """
        Find all non-deleted binds by Distributor ID.
        @param repo_id: A Repo ID.
        @type repo_id: str
        @param distributor_id: A Distributor ID.
        @type distributor_id: str
        @return: A list of Bind.
        @rtype: list
        """
        collection = Bind.get_collection()
        query = dict(
            repo_id=repo_id,
            distributor_id=distributor_id,
            deleted=False)
        cursor = collection.find(query)
        return list(cursor)

    def find_by_criteria(self, criteria):
        """
        Find bindings that match criteria.
        @param criteria: A Criteria object representing a search you want to perform
        @type  criteria: pulp.server.db.model.criteria.Criteria
        @return: list of Bind objects
        @rtype: list
        """
        collection = Bind.get_collection()
        bindings = collection.query(criteria)
        return list(bindings)

    @staticmethod
    def mark_deleted(consumer_id, repo_id, distributor_id):
        """
        Mark the bind as deleted.
        @param consumer_id: uniquely identifies the consumer.
        @type consumer_id: str
        @param repo_id: uniquely identifies the repository.
        @type repo_id: str
        @param distributor_id: uniquely identifies a distributor.
        @type distributor_id: str
        """
        # validate
        BindManager.get_bind(consumer_id, repo_id, distributor_id)
        # update document
        collection = Bind.get_collection()
        query = BindManager.bind_id(consumer_id, repo_id, distributor_id)
        collection.update(query, {'$set':{'deleted':True}}, safe=True)

    @staticmethod
    def delete(consumer_id, repo_id, distributor_id, force=False):
        """
        Delete the bind.
        @param consumer_id: uniquely identifies the consumer.
        @type consumer_id: str
        @param repo_id: uniquely identifies the repository.
        @type repo_id: str
        @param distributor_id: uniquely identifies a distributor.
        @type distributor_id: str
        @param force: Delete without validation.
        @type force: bool
        """
        collection = Bind.get_collection()
        bind_id = BindManager.bind_id(consumer_id, repo_id, distributor_id)
        if not force:
            query = {
                '$and': [
                    bind_id,
                    {'consumer_actions.status': {'$in': [Bind.Status.PENDING, Bind.Status.FAILED]}}
                ]
            }
            pending = collection.find(query)
            if len(list(pending)):
                raise Exception, 'outstanding actions, not deleted'
        if not force:
            bind_id['deleted'] = True
        collection.remove(bind_id, safe=True)

    def action_pending(self, consumer_id, repo_id, distributor_id, action, action_id):
        """
        Add pending action for tracking.
        @param consumer_id: uniquely identifies the consumer.
        @type consumer_id: str
        @param repo_id: uniquely identifies the repository.
        @type repo_id: str
        @param distributor_id: uniquely identifies a distributor.
        @type distributor_id: str
        @param action: The action (bind|unbind).
        @type action: str
        @param action_id: The ID of the action to begin tracking.
        @type action_id: str
        @see Bind.Action
        """
        collection = Bind.get_collection()
        assert action in (Bind.Action.BIND, Bind.Action.UNBIND)
        bind_id = self.bind_id(consumer_id, repo_id, distributor_id)
        entry = dict(
            id=action_id,
            timestamp=time(),
            action=action,
            status=Bind.Status.PENDING)
        update = {'$push':{'consumer_actions':entry}}
        collection.update(bind_id, update, safe=True)

    def action_succeeded(self, consumer_id, repo_id, distributor_id, action_id):
        """
        A tracked consumer action has succeeded.
        Since consumer actions are queue to the agent and performed
        in the order, previous actions are considered irrelevant and thus purged.
        @param consumer_id: uniquely identifies the consumer.
        @type consumer_id: str
        @param repo_id: uniquely identifies the repository.
        @type repo_id: str
        @param distributor_id: uniquely identifies a distributor.
        @type distributor_id: str
        @param action_id: The ID of the action to begin tracking.
        @type action_id: str
        """
        collection = Bind.get_collection()
        bind_id = self.bind_id(consumer_id, repo_id, distributor_id)
        action = self.find_action(action_id)
        if action is None:
            _LOG.warn('action %s not found', action_id)
            return
        # delete the action
        update = {'$pull':{'consumer_actions':{'id':action_id}}}
        collection.update(bind_id, update, safe=True)
        # purge all previous actions
        update = {'$pull':
            {'consumer_actions':{'timestamp':{'$lt':action['timestamp']}}}
        }
        collection.update(bind_id, update, safe=True)

    def action_failed(self, consumer_id, repo_id, distributor_id, action_id):
        """
        A tracked consumer action has failed.
        @param consumer_id: uniquely identifies the consumer.
        @type consumer_id: str
        @param repo_id: uniquely identifies the repository.
        @type repo_id: str
        @param distributor_id: uniquely identifies a distributor.
        @type distributor_id: str
        @param action_id: The ID of the request to begin tracking.
        @type action_id: str
        """
        collection = Bind.get_collection()
        query = self.bind_id(consumer_id, repo_id, distributor_id)
        query['consumer_actions.id'] = action_id
        update = {'$set':{'consumer_actions.$.status':Bind.Status.FAILED}}
        collection.update(query, update, safe=True)

    def find_action(self, action_id):
        """
        Find a consumer action by ID.
        @param action_id: An action ID.
        @type action_id: str
        @return: The action if found, else None
        """
        collection = Bind.get_collection()
        query = {'consumer_actions.id':action_id}
        binding = collection.find_one(query)
        if binding is None:
            return
        for action in binding['consumer_actions']:
            if action['id'] == action_id:
                return action

    @staticmethod
    def _validate_consumer_repo(consumer_id, repo_id, distributor_id):
        """
        Validate that the given consumer, repository, and distributor are present.
        Rather than raising an exception, this method returns a dictionary of missing
        values and allows the caller to decide what exception to raise.

        :param consumer_id:     The consumer id to validate
        :type  consumer_id:     str
        :param repo_id:         The repository id to validate
        :type  repo_id:         str
        :param distributor_id:  The distributor_id to validate
        :type  distributor_id:  str

        :return: A dictionary containing the missing values, or an empty dict if everything is valid
        :rtype:  dict
        """
        missing_values = {}

        try:
            factory.consumer_manager().get_consumer(consumer_id)
        except MissingResource:
            missing_values['consumer_id'] = consumer_id
        try:
            factory.repo_query_manager().get_repository(repo_id)
        except MissingResource:
            missing_values['repo_id'] = repo_id
        try:
            factory.repo_distributor_manager().get_distributor(repo_id, distributor_id)
        except MissingResource:
            missing_values['distributor_id'] = distributor_id

        return missing_values


bind = task(BindManager.bind, base=Task)
delete = task(BindManager.delete, base=Task)
unbind = task(BindManager.unbind, base=Task)
