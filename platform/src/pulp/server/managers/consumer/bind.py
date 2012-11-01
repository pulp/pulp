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
Contains bind management classes
"""

from logging import getLogger

from pymongo.errors import DuplicateKeyError

from pulp.server.db.model.consumer import Bind
from pulp.server.exceptions import MissingResource
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

    def bind(self, consumer_id, repo_id, distributor_id):
        """
        Bind consumer to a specific distributor associated with
        a repository.  This call is idempotent.
        @param consumer_id: uniquely identifies the consumer.
        @type consumer_id: str
        @param repo_id: uniquely identifies the repository.
        @type repo_id: str
        @param distributor_id: uniquely identifies a distributor.
        @type distributor_id: str
        @return: The Bind object
        @rtype: SON
        @raise MissingResource: when given consumer does not exist.
        """
        # ensure the consumer is valid
        manager = factory.consumer_manager()
        manager.get_consumer(consumer_id)
        # ensure the repository & distributor are valid
        manager = factory.repo_distributor_manager()
        manager.get_distributor(repo_id, distributor_id)
        # perform the bind
        collection = Bind.get_collection()
        try:
            bind = Bind(consumer_id, repo_id, distributor_id)
            collection.save(bind, safe=True)
        except DuplicateKeyError:
            self.__reset_bind(consumer_id, repo_id, distributor_id)
        # fetch the inserted/updated bind
        bind = self.get_bind(consumer_id, repo_id, distributor_id)
        # update history
        details = {'repo_id':repo_id, 'distributor_id':distributor_id}
        manager = factory.consumer_history_manager()
        manager.record_event(consumer_id, 'repo_bound', details)
        return bind

    def __reset_bind(self, consumer_id, repo_id, distributor_id):
        """
        Rest the bind.
        This means resetting the (deleted) flag and consumer requests.
        @param consumer_id:
        @param repo_id:
        @param distributor_id:
        """
        collection = Bind.get_collection()
        query = dict(
            consumer_id=consumer_id,
            repo_id=repo_id,
            distributor_id=distributor_id
        )
        update = {'$set':{'deleted':False, 'consumer_actions':[]}}
        collection.update(query, update, safe=True)

    def unbind(self, consumer_id, repo_id, distributor_id):
        """
        Unbind consumer to a specific distributor associated with
        a repository.  This call is idempotent.
        @param consumer_id: uniquely identifies the consumer.
        @type consumer_id: str
        @param repo_id: uniquely identifies the repository.
        @type repo_id: str
        @param distributor_id: uniquely identifies a distributor.
        @type distributor_id: str
        @return: The Bind object
        @rtype: SON
        """
        collection = Bind.get_collection()
        query = dict(
            consumer_id=consumer_id,
            repo_id=repo_id,
            distributor_id=distributor_id,
            deleted=False)
        bind = collection.find_one(query)
        if bind is None:
            # idempotent
            return
        self.mark_deleted(consumer_id, repo_id, distributor_id)
        details = {
            'repo_id':repo_id,
            'distributor_id':distributor_id
        }
        manager = factory.consumer_history_manager()
        manager.record_event(consumer_id, 'repo_unbound', details)
        return bind

    def consumer_deleted(self, id):
        """
        Notification that a consumer has been deleted.
        Associated binds are removed.
        @param id: A consumer ID.
        @type id: str
        """
        collection = Bind.get_collection()
        query = dict(consumer_id=id)
        collection.remove(query)

    def get_bind(self, consumer_id, repo_id, distributor_id):
        """
        Find a specific bind.
        @param consumer_id: uniquely identifies the consumer.
        @type consumer_id: str
        @param repo_id: uniquely identifies the repository.
        @type repo_id: str
        @param distributor_id: uniquely identifies a distributor.
        @type distributor_id: str
        @return: A specific bind.
        @rtype: SON
        @raise MissingResource: When not found
        """
        collection = Bind.get_collection()
        query = dict(
            consumer_id=consumer_id,
            repo_id=repo_id,
            distributor_id=distributor_id,
            deleted=False)
        bind = collection.find_one(query)
        if bind is None:
            key = '.'.join((consumer_id, repo_id, distributor_id))
            raise MissingResource(key)
        return bind

    def find_all(self):
        """
        Find all binds
        @return: A list of all bind
        @rtype: list
        """
        collection = Bind.get_collection()
        query = dict(deleted=False)
        cursor = collection.find(query)
        return list(cursor)

    def find_by_consumer(self, id, repo_id=None):
        """
        Find all binds by Consumer ID.
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

    def find_by_consumer_list(self, consumer_ids):
        """
        Given a list of consumer ids, return a dictionary whose keys are the
        consumer ids, and whose values are each a list of bindings for the
        given consumer.
        @param consumer_ids: list of consumer ids
        @type  consumer_ids: list
        @return: a dictionary whose keys are the consumer ids, and whose
            values are each a list of bindings for the given consumer.
        @rtype: dict
        """
        collection = Bind.get_collection()
        result = dict([(consumer_id, []) for consumer_id in consumer_ids])
        query = {'consumer_id': {'$in': consumer_ids}, 'deleted':False}
        cursor = collection.find(query)
        for bind in cursor:
            consumer_id = bind['consumer_id']
            result[consumer_id].append(bind)
        return result

    def find_by_repo(self, id):
        """
        Find all binds by Repo ID.
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
        Find all binds by Distributor ID.
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

    def mark_deleted(self, consumer_id, repo_id, distributor_id):
        """
        Mark the bind as deleted.
        @param consumer_id: uniquely identifies the consumer.
        @type consumer_id: str
        @param repo_id: uniquely identifies the repository.
        @type repo_id: str
        @param distributor_id: uniquely identifies a distributor.
        @type distributor_id: str
        """
        collection = Bind.get_collection()
        query = dict(
            consumer_id=consumer_id,
            repo_id=repo_id,
            distributor_id=distributor_id,
            deleted=False)
        collection.update(query, {'$set':{'deleted':True}}, safe=True)

    def delete(self, consumer_id, repo_id, distributor_id):
        """
        Delete the bind.
        @param consumer_id: uniquely identifies the consumer.
        @type consumer_id: str
        @param repo_id: uniquely identifies the repository.
        @type repo_id: str
        @param distributor_id: uniquely identifies a distributor.
        @type distributor_id: str
        """
        collection = Bind.get_collection()
        query = {
            'consumer_actions.status':{
                '$in':[Bind.Status.PENDING, Bind.Status.FAILED]}
        }
        pending = collection.find(query)
        if len(list(pending)):
            raise Exception, 'Bind with outstanding consumer requests may not be deleted'
        query = dict(
            consumer_id=consumer_id,
            repo_id=repo_id,
            distributor_id=distributor_id,
            deleted=True)
        collection.remove(query, safe=True)

    def action_pending(self, consumer_id, repo_id, distributor_id, action, action_id):
        """
        Add (pending) action for tracking.
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
        """
        collection = Bind.get_collection()
        assert action in (Bind.Action.BIND, Bind.Action.UNBIND)
        bind_id = dict(
            consumer_id=consumer_id,
            repo_id=repo_id,
            distributor_id=distributor_id)
        entry = dict(
            id=action_id,
            action=action,
            status=Bind.Status.PENDING)
        update = {'$push':{'consumer_actions':entry}}
        collection.update(bind_id, update, safe=True)

    def action_succeeded(self, consumer_id, repo_id, distributor_id, action_id):
        """
        A tracked consumer action has succeeded.
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
        bind_id = dict(
            consumer_id=consumer_id,
            repo_id=repo_id,
            distributor_id=distributor_id)
        # delete the request
        update = {'$pull':{'consumer_actions':{'id':action_id}}}
        collection.update(bind_id, update, safe=True)
        # purge all failed requests
        update = {'$pull':{'consumer_actions':{'status':Bind.Status.FAILED}}}
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
        query = dict(
            consumer_id=consumer_id,
            repo_id=repo_id,
            distributor_id=distributor_id)
        query['consumer_actions.id'] = action_id
        update = {'$set':{'consumer_actions.$.status':Bind.Status.FAILED}}
        collection.update(query, update, safe=True)