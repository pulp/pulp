"""
This module contains models that are used by the resource manager to persist its state so that it
can survive being restarted.
"""
from pulp.server.db.model.base import Model


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
    Instances of this class represent resources that have been reserved.

    :ivar task_id:       The uuid of the task associated with this reservation
    :type task_id:       basestring
    :ivar worker_name:   The name of the worker associated with this reservation.
    :type worker_name:   basestring
    :ivar resource_id:   The name of the resource reserved for the task.
    :type resource_id:   basestring
    """
    collection_name = 'reserved_resources'
    unique_indices = tuple()
    search_indices = ('worker_name', 'resource_id')

    def __init__(self, task_id, worker_name, resource_id):
        """
        :param task_id:       The uuid of the task associated with this reservation
        :type task_id:        basestring
        :param worker_name:   The name of the worker associated with this reservation.
        :type worker_name:    basestring
        :param resource_id:   The name of the resource reserved for the task.
        :type resource_id:    basestring
        """
        super(ReservedResource, self).__init__()

        self.task_id = task_id
        self.worker_name = worker_name
        self.resource_id = resource_id

        # We don't need these
        del self['_id']
        del self['id']

    def delete(self):
        """
        Delete self from the DB
        """
        self.get_collection().remove({'_id': self.task_id})

    def save(self):
        """
        Save any changes made to this ReservedResource to the database. If it doesn't exist, insert
        a new record to represent it.
        """
        self.get_collection().save(
            {'_id': self.task_id, 'resource_id': self.resource_id, 'worker_name': self.worker_name},
            safe=True)
