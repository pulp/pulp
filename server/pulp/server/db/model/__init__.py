import copy
import logging

from mongoengine import (DateTimeField, DictField, Document, DynamicField, IntField,
                         ListField, StringField)
from mongoengine import signals

from pulp.common import constants
from pulp.server.async.emit import send as send_taskstatus_message
from pulp.server.db.model.base import CriteriaQuerySet
from pulp.server.db.model.fields import ISO8601StringField
from pulp.server.db.model.reaper_base import ReaperMixin


_logger = logging.getLogger(__name__)


class Repository(Document):
    """
    Defines schema for a pulp repository in the `repos` collection.

    :ivar repo_id: unique across all repos
    :type repo_id: mongoengine.StringField
    :ivar display_name: user-readable name of the repository
    :type display_name: mongoengine.StringField
    :ivar description: free form text provided by the user to describe the repo
    :type description: mongoengine.StringField
    :ivar notes: arbitrary key-value pairs programmatically describing the repo;
                 these are intended as a way to describe the repo usage or
                 organizational purposes and should not vary depending on the
                 actual content of the repo
    :type notes: mongoengine.DictField
    :ivar content_unit_counts: key-value pairs of number of units associated with this repo.
                               This is different than the number of associations, since a
                               unit may be associated multiple times.
    :type content_unit_counts: mongoengine.DictField
    :ivar scratchpad: Field used to persistently store arbitrary information from the plugins
                      across multiple operations.
    :type scratchpad: mongoengine.DictField
    :ivar last_unit_added: Datetime of the most recent occurence of adding a unit to the repo
    :type last_unit_added: mongoengine.DateTimeField
    :ivar last_unit_removed: Datetime of the most recent occurence of removing a unit from the repo
    :type last_unit_removed: mongoengine.DateTimeField
    :ivar _ns: (Deprecated) Namespace of repo, included for backwards compatibility.
    :type _is: mongoengine.StringField
    """

    # This field is named `repo_id` because `id`  cannot be accessed using the normal mongoengine
    # idiom of `obj.id` because `obj.id` has been aliased (internally in mongoengine) to reference
    # obj._id. So we name this field `repo_id`, and temporarily continue to store it in the db as
    # `id` for backwards compatibility. This should be migrated to `repo_id` in a future X release.
    repo_id = StringField(db_field='id', required=True)
    display_name = StringField(required=True)
    description = StringField()
    notes = DictField()
    scratchpad = DictField()
    content_unit_counts = DictField()
    last_unit_added = DateTimeField()
    last_unit_removed = DateTimeField()

    # For backward compatibility
    _ns = StringField(default='repos')

    meta = {'collection': 'repos',
            'allow_inheritance': False,
            'indexes': [{'fields': ['-repo_id'], 'unique': True}]}


class RepositoryContentUnit(Document):
    """
    Represents the link between a repository and the units associated with it.

    This inherits from mongoengine.Document and defines the schema for the documents
    in repo_content_units collection.


    :ivar repo_id: string representation of the repository id
    :type repo_id: mongoengine.StringField
    :ivar unit_id: string representation of content unit id
    :type unit_id: mongoengine.StringField
    :ivar unit_type_id: string representation of content unit type
    :type unit_type_id: mongoengine.StringField
    :ivar created: ISO8601 representation of the time the association was created
    :type created: pulp.server.db.model.fields.ISO8601StringField
    :ivar updated: ISO8601 representation of last time a copy, sync, or upload ensured that
                   the association existed
    :type updated: pulp.server.db.model.fields.ISO8601StringField
    :ivar _ns: The namespace field (Deprecated), reading
    :type _ns: mongoengine.StringField
    """

    repo_id = StringField(required=True)
    unit_id = StringField(required=True)
    unit_type_id = StringField(required=True)
    created = ISO8601StringField(required=True)
    updated = ISO8601StringField(required=True)

    # For backward compatibility
    _ns = StringField(default='repo_content_units')

    meta = {'collection': 'repo_content_units',
            'allow_inheritance': False,
            'indexes': [
                {
                    'fields': ['repo_id', 'unit_type_id', 'unit_id'],
                    'unique': True
                },
                {
                    # Used for reverse lookup of units to repositories
                    'fields': ['unit_id']
                }
            ]}


class ReservedResource(Document):
    """
    Instances of this class represent resources that have been reserved.

    :ivar task_id:       The uuid of the task associated with this reservation
    :type task_id:       mongoengine.StringField
    :ivar worker_name:   The name of the worker associated with this reservation.
    :type worker_name:   mongoengine.StringField
    :ivar resource_id:   The name of the resource reserved for the task.
    :type resource_id:   mongoengine.StringField
    :ivar _ns: The namespace field (Deprecated), reading
    :type _ns: mongoengine.StringField
    """

    task_id = StringField(db_field='_id', primary_key=True)
    worker_name = StringField()
    resource_id = StringField()

    # For backward compatibility
    _ns = StringField(default='reserved_resources')

    meta = {'collection': 'reserved_resources',
            'indexes': ['-worker_name', '-resource_id'],
            'allow_inheritance': False}


class Worker(Document):
    """
    Represents a worker.

    This inherits from mongoengine.Document and defines the schema for the documents
    in the worker collection.

    :ivar name:    worker name, in the form of "worker_type@hostname"
    :type name:    mongoengine.StringField
    :ivar last_heartbeat:  A timestamp of the last heartbeat from the Worker
    :type last_heartbeat:  mongoengine.DateTimeField
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


class MigrationTracker(Document):
    """
    This is used to track state about our migrations package. There will be one object for each
    migration package in pulp.server.db.migrations, and we will track which migration version each
    of those packages have been advanced to.

    :ivar name:    Uniquely identifies the package, and is the name of the package
    :type name:    mongoengine.StringField
    :ivar version: The version that the migration package is currently at
    :type version: mongoengine.IntField
    :ivar _ns: The namespace field (Deprecated), reading
    :type _ns: mongoengine.StringField
    """

    name = StringField(unique=True, required=True)
    version = IntField(default=0)
    # For backward compatibility
    _ns = StringField(default='migration_trackers')

    meta = {'collection': 'migration_trackers',
            'indexes': [],  # small collection, does not need an index
            'allow_inheritance': False}


class TaskStatus(Document, ReaperMixin):
    """
    Represents a task.
    This inherits from mongoengine.Document and defines the schema for the documents
    in task_status collection. The documents in this collection may be reaped,
    so it inherits from ReaperMixin.

    :ivar task_id:     identity of the task this status corresponds to
    :type task_id:     basestring
    :ivar worker_name: The name of the worker that the Task is in
    :type worker_name: basestring
    :ivar tags:        custom tags on the task
    :type tags:        list
    :ivar state:       state of callable in its lifecycle
    :type state:       basestring
    :ivar error: Any errors or collections of errors that occurred while this task was running
    :type error: dict (created from a PulpException)
    :ivar spawned_tasks: List of tasks that were spawned during the running of this task
    :type spawned_tasks: list of str
    :ivar progress_report: A report containing information about task's progress
    :type progress_report: dict
    :ivar task_type:   the fully qualified (package/method) type of the task
    :type task_type:   basestring
    :ivar start_time:  ISO8601 representation of the time the task started executing
    :type start_time:  basestring
    :ivar finish_time: ISO8601 representation of the time the task completed
    :type finish_time: basestring
    :ivar result:      return value of the callable, if any
    :type result:      any
    :ivar exception:   Deprecated. This is always None.
    :type exception:   None
    :ivar traceback:   Deprecated. This is always None.
    :type traceback:   None
    """

    task_id = StringField(unique=True, required=True)
    worker_name = StringField()
    tags = ListField(StringField())
    state = StringField(choices=constants.CALL_STATES, default=constants.CALL_WAITING_STATE)
    error = DictField(default=None)
    spawned_tasks = ListField(StringField())
    progress_report = DictField()
    task_type = StringField()
    start_time = ISO8601StringField()
    finish_time = ISO8601StringField()
    result = DynamicField()

    # These are deprecated, and will always be None
    exception = StringField()
    traceback = StringField()

    # For backward compatibility
    _ns = StringField(default='task_status')

    meta = {'collection': 'task_status',
            'indexes': ['-task_id', '-tags', '-state'],
            'allow_inheritance': False,
            'queryset_class': CriteriaQuerySet}

    def save_with_set_on_insert(self, fields_to_set_on_insert):
        """
        Save the current state of the TaskStatus to the database, using an upsert operation.
        The upsert operation will only set those fields if this becomes an insert operation,
        otherwise those fields will be ignored. This also validates the fields according to the
        schema above.

        This is required because the current mongoengine version we are using does not support
        upsert with set_on_insert through mongoengine queries. Once we update to the version
        which supports this, this method can be deleted and it's usages can be replaced
        with mongoengine upsert queries.

        :param fields_to_set_on_insert: A list of field names that should be updated with Mongo's
                                        $setOnInsert operator.
        :type  fields_to_set_on_insert: list
        """

        # If fields_to_set_on_insert is None or empty, just save
        if not fields_to_set_on_insert:
            self.save()
            return

        # This will be used in place of superclass' save method, so we need to call validate()
        # explicitly.
        self.validate()

        stuff_to_update = dict(copy.deepcopy(self._data))

        # Let's pop the $setOnInsert attributes out of the copy of self so that we can pass the
        # remaining attributes to the $set operator in the query below.
        set_on_insert = {}
        for field in fields_to_set_on_insert:
            set_on_insert[field] = stuff_to_update.pop(field)
        task_id = stuff_to_update.pop('task_id')

        update = {'$set': stuff_to_update,
                  '$setOnInsert': set_on_insert}
        TaskStatus._get_collection().update({'task_id': task_id}, update, upsert=True)

    @classmethod
    def post_save(cls, sender, document, **kwargs):
        """
        Send a taskstatus message on save.

        :param sender: class of sender (unused)
        :type  sender: class
        :param document: mongoengine document
        :type  document: mongoengine.Document

        """
        send_taskstatus_message(document, routing_key="tasks.%s" % document['task_id'])


signals.post_save.connect(TaskStatus.post_save, sender=TaskStatus)
