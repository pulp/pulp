"""
This module contains models that are used by the resource manager to persist its state so that it
can survive being restarted.
"""
from pulp.server.db.model.base import DoesNotExist, Model


class Worker(Model):
    """
    Instances of this class represent known Celery workers that are available for use by
    the resource manager for assigning tasks.

    :ivar name:             The name of the queue
    :type name:             unicode
    :ivar last_heartbeat:   A timestamp of the last heartbeat from the Worker
    :type last_heartbeat:   datetime.datetime
    """
    collection_name = 'workers'
    unique_indices = tuple()
    # The compound index with _id and last_heartbeat will help the
    # async.scheduler.WorkerTimeoutMonitor to be able to retrieve the data it needs without
    # accessing the disk
    search_indices = (('_id', 'last_heartbeat'),)

    def __init__(self, name, last_heartbeat):
        """
        Initialize the Worker.

        :param name:             The name of the Worker.
        :type  name:             basestring
        :param last_heartbeat:   A timestamp of the last heartbeat from the Worker
        :type  last_heartbeat:   datetime.datetime
        """
        super(Worker, self).__init__()

        self.name = name
        self.last_heartbeat = last_heartbeat

        # We don't need these
        del self['_id']
        del self['id']

    def delete(self):
        """
        Delete this Worker from the database. Take no prisoners.
        """
        self.get_collection().remove({'_id': self.name})
        # Also delete ReservedResources referencing this Worker's queue. This will prevent new
        # tasks from using existing reservations to enter this deleted Worker's queue.
        ReservedResource.get_collection().remove({'assigned_queue': self.queue_name})

    @classmethod
    def from_bson(cls, bson_worker):
        """
        Instantiate a Worker from the given bson. A Python dict can also be used in place
        of bson_worker.

        :param bson_worker: A bson object or a dict representing a Worker.
        :type  bson_worker: bson.BSON or dict
        :return:            A Worker representing the given bson_worker
        :rtype:             pulp.server.db.model.resources.Worker
        """
        return cls(
            name=bson_worker['_id'],
            last_heartbeat=bson_worker.get('last_heartbeat', None))

    @property
    def queue_name(self):
        """
        This property is a convenience for getting the queue_name that Celery assigns to this
        Worker.

        :return: The name of the queue that this Worker is uniquely subcribed to.
        :rtype:  basestring
        """
        return "%(name)s.dq" % {'name': self.name}

    def save(self):
        """
        Save any changes made to this Worker to the database. If it doesn't exist, insert a
        new record to represent it.
        """
        self.get_collection().save(
            {'_id': self.name,
             'last_heartbeat': self.last_heartbeat},
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
    unique_indices = tuple()

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
