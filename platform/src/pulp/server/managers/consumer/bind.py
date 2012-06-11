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

from pymongo.errors import DuplicateKeyError
from pulp.server.db.model.gc_consumer import Consumer, Bind
from pulp.server.exceptions import InvalidValue, MissingResource
from pulp.server.managers import factory
from logging import getLogger


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
        manager = factory.consumer_manager()
        manager.get_consumer(consumer_id)
        manager = factory.repo_distributor_manager()
        distributor = manager.get_distributor(repo_id, distributor_id)
        bind = Bind(consumer_id, repo_id, distributor_id)
        collection = Bind.get_collection()
        try:
            collection.save(bind, safe=True)
            bind = self.get_bind(consumer_id, repo_id, distributor_id)
        except DuplicateKeyError:
            # idempotent
            pass
        manager = factory.consumer_agent_manager()
        manager.bind(consumer_id, repo_id)
        consumer_event_details = {'repo_id':repo_id, 'distributor_id':distributor_id}
        factory.consumer_history_manager().record_event(consumer_id, 'repo_bound', consumer_event_details)
        return bind

    def unbind(self, consumer_id, repo_id, distributor_id):
        """
        Unbind consumer to a specifiec distirbutor associated with
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
        query = dict(
            consumer_id=consumer_id,
            repo_id=repo_id,
            distributor_id=distributor_id)
        collection = Bind.get_collection()
        bind = collection.find_one(query)
        if bind is None:
            # idempotent
            return
        collection.remove(bind, safe=True)
        manager = factory.consumer_agent_manager()
        manager.unbind(consumer_id, repo_id)
        consumer_event_details = {'repo_id':repo_id, 'distributor_id':distributor_id}
        factory.consumer_history_manager().record_event(consumer_id, 'repo_unbound', consumer_event_details)
        return bind
        
    def consumer_deleted(self, id):
        """
        Notification that a consumer has been deleted.
        Associated binds are removed.
        @param id: A consumer ID.
        @type id: str
        """
        collection = Bind.get_collection()
        agent_manager = factory.consumer_agent_manager()
        for bind in self.find_by_consumer(id):
            collection.remove(bind, safe=True)
            repo_id = bind['repo_id']
            agent_manager.unbind(id, repo_id)
    
    def repo_deleted(self, repo_id):
        """
        Notification that a repository has been deleted.
        Associated binds are removed.
        @param repo_id: A repo ID.
        @type repo_id: str
        """
        collection = Bind.get_collection()
        agent_manager = factory.consumer_agent_manager()
        for bind in self.find_by_repo(repo_id):
            collection.remove(bind, safe=True)
            consumer_id = bind['consumer_id']
            agent_manager.unbind(consumer_id, repo_id)

    def distributor_deleted(self, repo_id, distributor_id):
        """
        Notification that a distributor has been deleted.
        Associated binds are removed.
        @param repo_id: A Repo ID.
        @type repo_id: str
        @param distributor_id: A Distributor ID.
        @type distributor_id: str
        """
        collection = Bind.get_collection()
        agent_manager = factory.consumer_agent_manager()
        for bind in self.find_by_distributor(repo_id, distributor_id):
            collection.remove(bind, safe=True)
            consumer_id = bind['consumer_id']
            agent_manager.unbind(consumer_id, repo_id)

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
            distributor_id=distributor_id)
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
        cursor = collection.find({})
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
            query = dict(consumer_id=id, repo_id=repo_id)
        else:
            query = dict(consumer_id=id)
        cursor = collection.find(query)
        return list(cursor)

    def find_by_repo(self, id):
        """
        Find all binds by Repo ID.
        @param id: A Repo ID.
        @type id: str
        @return: A list of Bind.
        @rtype: list
        """
        collection = Bind.get_collection()
        query = dict(repo_id=id)
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
            distributor_id=distributor_id)
        cursor = collection.find(query)
        return list(cursor)