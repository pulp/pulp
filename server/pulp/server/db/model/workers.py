import logging

from mongoengine import Document, StringField, DateTimeField

from pulp.server.db.model.base import CriteriaQuerySet


_logger = logging.getLogger(__name__)


class Worker(Document):
    """
    Represents a worker.

    This inherits from mongoengine.Document and defines the schema for the documents
    in the worker collection.

    :ivar name:    worker name, in the form of "worker_type@hostname"
    :type name:    basestring
    :ivar last_heartbeat:  A timestamp of the last heartbeat from the Worker
    :type last_heartbeat:  datetime.datetime
    """
    name = StringField(primary_key=True)
    last_heartbeat = DateTimeField()

    meta = {'collection': 'workers',
            'indexes': [],  # this is a small collection that does not need an index
            'allow_inheritance': False,
            'queryset_class': CriteriaQuerySet}

    @property
    def queue_name(self):
        """
        This property is a convenience for getting the queue_name that Celery assigns to this
        Worker.

        :return: The name of the queue that this Worker is uniquely subcribed to.
        :rtype:  basestring
        """
        return "%(name)s.dq" % {'name': self.name}
