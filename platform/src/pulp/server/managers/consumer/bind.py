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
        bind = Bind(consumer_id, repo_id, distributor_id)
        collection = Bind.get_collection()
        try:
            collection.save(bind, safe=True)
            bind = self.get_bind(consumer_id, repo_id, distributor_id)
        except DuplicateKeyError:
            # idempotent
            pass
        details = {'repo_id':repo_id, 'distributor_id':distributor_id}
        manager = factory.consumer_history_manager()
        manager.record_event(consumer_id, 'repo_bound', details)
        return bind

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
        for bind in collection.find(query):
            self.delete(bind['consumer_id'], bind['repo_id'], bind['distributor_id'])

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
        pending = collection.find({'consumer_requests.status':'pending'})
        if len(list(pending)):
            raise Exception, 'Bind with outstanding consumer requests may not be deleted'
        query = dict(
            consumer_id=consumer_id,
            repo_id=repo_id,
            distributor_id=distributor_id,
            deleted=True)
        collection.remove(query, safe=True)

    def request_pending(self, consumer_id, repo_id, distributor_id, request_id):
        """
        Add (pending) request for tracking.
        @param consumer_id: uniquely identifies the consumer.
        @type consumer_id: str
        @param repo_id: uniquely identifies the repository.
        @type repo_id: str
        @param distributor_id: uniquely identifies a distributor.
        @type distributor_id: str
        @param request_id: The ID of the request to begin tracking.
        @type request_id: str
        """
        collection = Bind.get_collection()
        entry = dict(request_id=request_id, status='pending')
        update = {'$push':{'consumer_requests':entry}}
        bind_id = dict(
            consumer_id=consumer_id,
            repo_id=repo_id,
            distributor_id=distributor_id)
        collection.update(bind_id, update, safe=True)

    def request_succeeded(self, consumer_id, repo_id, distributor_id, request_id):
        """
        A tracked consumer request has succeeded.
        @param consumer_id: uniquely identifies the consumer.
        @type consumer_id: str
        @param repo_id: uniquely identifies the repository.
        @type repo_id: str
        @param distributor_id: uniquely identifies a distributor.
        @type distributor_id: str
        @param request_id: The ID of the request to begin tracking.
        @type request_id: str
        """
        collection = Bind.get_collection()
        bind_id = dict(
            consumer_id=consumer_id,
            repo_id=repo_id,
            distributor_id=distributor_id)
        # delete the request
        update = {'$pull':{'consumer_requests':{'request_id':request_id}}}
        collection.update(bind_id, update, safe=True)
        # purge all failed requests
        update = {'$pull':{'consumer_requests':{'status':'failed'}}}
        collection.update(bind_id, update, safe=True)

    def request_failed(self, consumer_id, repo_id, distributor_id, request_id):
        """
        A tracked consumer request has failed.
        @param consumer_id: uniquely identifies the consumer.
        @type consumer_id: str
        @param repo_id: uniquely identifies the repository.
        @type repo_id: str
        @param distributor_id: uniquely identifies a distributor.
        @type distributor_id: str
        @param request_id: The ID of the request to begin tracking.
        @type request_id: str
        """
        collection = Bind.get_collection()
        query = dict(
            consumer_id=consumer_id,
            repo_id=repo_id,
            distributor_id=distributor_id)
        query['consumer_requests.request_id'] = request_id
        update = {'$set':{'consumer_requests.$.status':'failed'}}
        collection.update(query, update, safe=True)