"""
This module contains models that are used by the resource manager to persist its state so that it
can survive being restarted.
"""
from pulp.server.db.model.base import Model


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
