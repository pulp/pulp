# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
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
This module contains models that are used by the resource manager to persist its state so that it
can survive being restarted.
"""
from pulp.server.db.model.base import DoesNotExist, Model


class AvailableQueue(Model):
    """
    Instances of this class represent existing Celery worker queues that are available for use by
    the resource manager for assigning tasks.

    :ivar name:             The name of the queue
    :type name:             unicode
    :ivar num_reservations: The number of outstanding reservations on the queue
    :type num_reservations: int
    :ivar missing_since:    A timestamp representing the time when the babysitter noticed that this
                            AvailableQueue's worker was missing. Set to None when the AvailableQueue
                            is not missing.
    :type missing_since:    datetime.datetime
    """
    collection_name = 'available_queues'
    unique_indices = ('_id',)
    # The compound index with _id and missing since will help the babysit() Task to be able to
    # retrieve the data it needs without accessing the disk
    search_indices = ('num_reservations', ('_id', 'missing_since'))

    def __init__(self, name, num_reservations=0, missing_since=None):
        """
        Initialize the AvailabeQueue. A new AvailableQueue always has a num_reservations of 0.

        :param name:             The name of the AvailableQueue, which should correspond to the name
                                 of a queue that a worker is assigned to.
        :type  name:             basestring
        :param num_reservations: The number of reservations in the AvailableQueue. Defaults to 0.
        :type  num_reservations: int
        :param missing_since:    A timestamp representing the time when the babysitter noticed that
                                 this AvailableQueue's worker was missing. Set to None when the
                                 AvailableQueue is not missing. Defaults to None.
        :type  missing_since:    datetime.datetime or None
        """
        super(AvailableQueue, self).__init__()

        self.name = name
        self.num_reservations = num_reservations
        self.missing_since = missing_since

        # We don't need these
        del self['_id']
        del self['id']

    def decrement_num_reservations(self):
        """
        Reduce self.num_reservations by one in the database, and update self with the current
        num_reservations (which could be different by more than one if another process also
        decremented it in between us). This method guarantees that num_reservations will not become
        negative.
        """
        # Perform the update in the database, but only if the value there is greater than 0.
        new_queue = self.get_collection().find_and_modify(
            query={'_id': self.name, 'num_reservations': {'$gt': 0}},
            update={'$inc': {'num_reservations': -1}}, new=True)

        if new_queue is None:
            # new_queue will be None if we asked Mongo to modify an object that didn't exist, or if
            # it did exist but its num_reservations was not greater than 0. Let's determine which of
            # these is the case.
            new_queue = self.get_collection().find_one({'_id': self.name})
            if new_queue is None:
                # Now we can be sure that no queue exists with this name
                raise DoesNotExist('AvailableQueue with name %s does not exist.' % self.name)

        # Update the attributes to match what was in the database
        self.num_reservations = new_queue['num_reservations']
        self.missing_since = new_queue['missing_since']

    def delete(self):
        """
        Delete this AvailableQueue from the database. Take no prisoners.
        """
        self.get_collection().remove({'_id': self.name})

    @classmethod
    def from_bson(cls, bson_queue):
        """
        Instantiate an AvailableQueue from the given bson. A Python dict can also be used in place
        of bson_queue.

        :param bson_queue: A bson object representing an AvailableQueue from the Mongo DB.
        :type  bson_queue: bson.BSON or dict
        :return:           An AvailableQueue representing the given bson
        :rtype:            pulp.server.db.model.resources.AvailableQueue
        """
        return cls(
            name=bson_queue['_id'],
            num_reservations=bson_queue.get('num_reservations', None),
            missing_since=bson_queue.get('missing_since', None))

    def increment_num_reservations(self):
        """
        Increase self.num_reservations by one in the database, and update self with the current
        num_reservations (which could be different by more than one if another process also
        incremented it in between us).
        """
        # Perform the update in the database, but only if the value there is greater than 0.
        new_queue = self.get_collection().find_and_modify(
            query={'_id': self.name},
            update={'$inc': {'num_reservations': 1}}, new=True)

        if new_queue is None:
            # We were asked to increment a queue that doesn't exist in the database.
            raise DoesNotExist('AvailableQueue with name %s does not exist.' % self.name)

        # Update the attributes to match what was in the database
        self.num_reservations = new_queue['num_reservations']
        self.missing_since = new_queue['missing_since']

    def save(self):
        """
        Save any changes made to this AvailableQueue to the database. If it doesn't exist, insert a
        new record to represent it.
        """
        self.get_collection().save(
            {'_id': self.name, 'num_reservations': self.num_reservations,
             'missing_since': self.missing_since},
            manipulate=False, safe=True)


class ReservedResource(Model):
    """
    Instances of this class represent resources that have been reserved through the resource
    manager.

    :ivar name:             The name of the reserved resource.
    :type name:             unicode
    :ivar assigned_queue:   The queue that this resource is assigned to
    :type assigned_queue:   unicode
    :ivar num_reservations: The number of outstanding reservations on this resource
    :type num_reservations: int
    """
    collection_name = 'reserved_resources'
    unique_indices = ('_id',)

    def __init__(self, name, assigned_queue=None, num_reservations=1):
        """
        Initialize the ReservedResource, storing the given state variables on it.

        :param name:             The name of the resource that has been reserved
        :type  name:             basestring
        :param assigned_queue:   The queue that the resource has been assigned to. Defaults to None.
        :type  assigned_queue:   basestring
        :param num_reservations: The number of outstanding reservations against this resource.
                                 Defaults to 1.
        :type  num_reservations: int
        """
        super(ReservedResource, self).__init__()

        self.name = name
        self.assigned_queue = assigned_queue
        self.num_reservations = num_reservations

        # We don't need these
        del self['_id']
        del self['id']

    def decrement_num_reservations(self):
        """
        Reduce self.num_reservations by one in the database, and update self with the current
        num_reservations (which could be different by more than one if another process also
        decremented it in between us) and the assigned_queue. If num_reservations is now 0, remove
        self from the database.
        """
        # Perform the update in the database, but only if the value there is greater than 0.
        new_resource = self.get_collection().find_and_modify(
            query={'_id': self.name, 'num_reservations': {'$gt': 0}},
            update={'$inc': {'num_reservations': -1}}, new=True)

        if new_resource is None:
            # new_resource will be None if we asked Mongo to modify an object that didn't exist, or
            # if it did exist but its num_reservations was not greater than 0. Let's determine which
            # of these is the case.
            new_resource = self.get_collection().find_one({'_id': self.name})
            if new_resource is None:
                # Now we can be sure that no queue exists with this name
                raise DoesNotExist('ReservedResource with name %s does not exist.' % self.name)

        # Update the instance attributes to reflect the value in the database
        self.assigned_queue = new_resource['assigned_queue']
        self.num_reservations = new_resource['num_reservations']
        if not self.num_reservations:
            self.delete()

    def delete(self):
        """
        Delete self from the DB, but only if the DB record that self represents has a
        num_reservations equal to 0. We can't rely on self.num_reservations, because someone else
        may have altered the DB record in the meantime.
        """
        self.get_collection().remove({'_id': self.name, 'num_reservations': 0})

    def increment_num_reservations(self):
        """
        Increase self.num_reservations by one in the database, and update self with the current
        num_reservations (which could be different by more than one if another process also
        incremented it in between us) and the assigned_queue.
        """
        # Perform the update in the database, but only if the value there is greater than 0.
        new_resource = self.get_collection().find_and_modify(
            query={'_id': self.name},
            update={'$inc': {'num_reservations': 1}}, new=True)

        if new_resource is None:
            # We were asked to increment a ReservedResource that does not exist.
            raise DoesNotExist('ReservedResource with name %s does not exist.' % self.name)

        # Update the instance attributes to reflect the value in the database
        self.assigned_queue = new_resource['assigned_queue']
        self.num_reservations = new_resource['num_reservations']

    def save(self):
        """
        Save any changes made to this ReservedResource to the database. If it doesn't exist, insert
        a new record to represent it.
        """
        self.get_collection().save(
            {'_id': self.name, 'assigned_queue': self.assigned_queue,
             'num_reservations': self.num_reservations}, safe=True)
