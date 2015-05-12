import copy
import errno
import logging
import os
import shutil
import uuid
from collections import namedtuple

from mongoengine import (DateTimeField, DictField, Document, DynamicField, IntField,
                         ListField, StringField)
from mongoengine import signals

from pulp.common import constants, dateutils, error_codes
from pulp.plugins.model import Repository as plugin_repo
from pulp.server import config, exceptions
from pulp.server.async.emit import send as send_taskstatus_message
from pulp.server.db.fields import ISO8601StringField
from pulp.server.db.model.reaper_base import ReaperMixin
from pulp.server.db.querysets import CriteriaQuerySet, RepoQuerySet
from pulp.server.webservices.views.serializers import Repository as RepoSerializer


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

    # Previously, this field was 'id'. This field is required to be unique, but the previous index
    # was '-id'. Setting unique=True here would generate a new 'repo_id' index. Instead, we set the
    # index in meta and enforce uniqueness there.
    repo_id = StringField(required=True, regex=r'^[.\-_A-Za-z0-9]+$')
    display_name = StringField()
    description = StringField()
    notes = DictField()
    scratchpad = DictField(default={})
    content_unit_counts = DictField(default={})
    last_unit_added = DateTimeField()
    last_unit_removed = DateTimeField()

    # For backward compatibility
    _ns = StringField(default='repos')

    meta = {'collection': 'repos',
            'allow_inheritance': False,
            'indexes': [{'fields': ['-repo_id'], 'unique': True}],
            'queryset_class': RepoQuerySet}
    serializer = RepoSerializer

    def to_transfer_repo(self):
        """
        Converts the given database representation of a repository into a plugin repository transfer
        object, including any other fields that need to be included.

        Note: In the transfer unit, the repo_id is accessed with obj.id for backwards compatability.

        :return: transfer object used in many plugin API calls
        :rtype:  pulp.plugins.model.Repository}
        """
        r = plugin_repo(self.repo_id, self.display_name, self.description, self.notes,
                        content_unit_counts=self.content_unit_counts,
                        last_unit_added=self.last_unit_added,
                        last_unit_removed=self.last_unit_removed)
        return r

    def update_from_delta(self, repo_delta):
        """
        Update the repository's fields from a delta. Keys that are not fields will be ignored.

        :param delta: key value pairs that represent the new values
        :type  delta: dict
        """

        # Notes is done seperately to only change notes fields that are specified. If a notes
        # field is set to None, remove it.
        if 'notes' in repo_delta:
            for key, value in repo_delta.pop('notes').items():
                if value is None:
                    self.notes.pop(key)
                else:
                    self.notes[key] = value

        # These keys may not be changed.
        prohibited = ['content_unit_counts', 'repo_id', 'last_unit_added', 'last_unit_removed']
        [setattr(self, key, value) for key, value in repo_delta.items() if key not in prohibited]


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
    :type created: pulp.server.db.fields.ISO8601StringField
    :ivar updated: ISO8601 representation of last time a copy, sync, or upload ensured that
                   the association existed
    :type updated: pulp.server.db.fields.ISO8601StringField
    :ivar _ns: The namespace field (Deprecated), reading
    :type _ns: mongoengine.StringField
    """

    repo_id = StringField(required=True)
    unit_id = StringField(required=True)
    unit_type_id = StringField(required=True)

    created = ISO8601StringField(
        required=True,
        default=lambda: dateutils.format_iso8601_utc_timestamp(
            dateutils.now_utc_timestamp())
    )
    updated = ISO8601StringField(
        required=True,
        default=lambda: dateutils.format_iso8601_utc_timestamp(
            dateutils.now_utc_timestamp())
    )

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

    # For backward compatibility
    _ns = StringField(default='workers')

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

    task_id = StringField(required=True)
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
            'indexes': ['-tags', '-state', {'fields': ['-task_id'], 'unique': True}],
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


class ContentUnit(Document):
    """
    The base class for all content units.

    All classes inheriting from this class must override the unit_type_id and _ns to ensure
    they are populated properly.

    :ivar id: content unit id
    :type id: mongoengine.StringField
    :ivar last_updated: last time this unit was updated (since epoch, zulu time)
    :type last_updated: mongoengine.IntField
    :ivar user_metadata: Bag of User supplied data to go along with this unit
    :type user_metadata: mongoengine.DictField
    :ivar storage_path: Location on disk where the content associated with this unit lives
    :type storage_path: mongoengine.StringField

    :ivar _ns: (Deprecated), Contains the name of the collection this model represents
    :type _ns: mongoengine.StringField
    :ivar unit_type_id: content unit type
    :type unit_type_id: mongoengine.StringField
    """

    id = StringField(primary_key=True)
    last_updated = IntField(db_field='_last_updated', required=True)
    user_metadata = DictField(db_field='pulp_user_metadata')
    storage_path = StringField(db_field='_storage_path')

    # For backward compatibility
    _ns = StringField(required=True)
    unit_type_id = StringField(db_field='_content_type_id', required=True)

    meta = {
        'abstract': True,
    }

    _NAMED_TUPLE = None

    def __init__(self, *args, **kwargs):
        super(ContentUnit, self).__init__(*args, **kwargs)
        self._source_location = None
        self._relative_path = None

    @classmethod
    def attach_signals(cls):
        """
        Attach the signals to this class.

        This is provided as a class method so it can be called on subclasses
        and all the correct signals will be applied.
        """
        signals.post_init.connect(cls.post_init_signal, sender=cls)
        signals.pre_save.connect(cls.pre_save_signal, sender=cls)
        # Create the named tuple here so it happens during server startup
        cls.NAMED_TUPLE = namedtuple(cls.unit_type_id.default, cls.unit_key_fields)

    @classmethod
    def post_init_signal(cls, sender, document):
        """
        The signal that is triggered before a unit is initialized

        This is used to validate that the unit_key_fields attribute is set properly

        :param sender: sender class
        :type sender: object
        :param document: Document that sent the signal
        :type document: ContentUnit
        :raises: PLP0035 if the unit_key_fields attribute has not been defined
        """
        if not hasattr(document, 'unit_key_fields'):
            class_name = type(document).__name__
            raise exceptions.PulpCodedException(error_codes.PLP0035, class_name=class_name)

    @classmethod
    def pre_save_signal(cls, sender, document, **kwargs):
        """
        The signal that is triggered before a unit is saved, this is used to
        support the legacy behavior of generating the unit id and setting
        the last_updated timestamp

        :param sender: sender class
        :type sender: object
        :param document: Document that sent the signal
        :type document: ContentUnit
        """
        if not document.id:
            document.id = str(uuid.uuid4())
        document.last_updated = dateutils.now_utc_timestamp()

        # If content was set on this unit, copy the content into place
        if document._source_location:
            server_storage_dir = config.config.get('server', 'storage_dir')
            platform_storage_location = os.path.join(server_storage_dir, 'units',
                                                     document.unit_type_id,
                                                     str(document.id)[0],
                                                     str(document.id)[1:3],
                                                     str(document.id))
            # Make if source is a directory, recursively copy it, otherwise copy the file
            if os.path.isdir(document._source_location):
                shutil.copytree(document._source_location, platform_storage_location)
            else:
                target_file_name = os.path.basename(document._source_location)
                # Make sure the base directory exists
                try:
                    os.makedirs(platform_storage_location)
                except OSError as e:
                    if e.errno != errno.EEXIST:
                        raise
                # Copy the file
                document_full_storage_location = os.path.join(platform_storage_location,
                                                              target_file_name)
                shutil.copy(document._source_location, document_full_storage_location)
                platform_storage_location = document_full_storage_location
            document.storage_path = platform_storage_location

    def set_content(self, source_location):
        """
        Store the source of the content for the unit and the relative path
        where it should be stored within the plugin content directory.

        :param source_location: The absolute path to the content in the plugin working directory.
        :type source_location: str

        :raises PulpCodedException: PLP0036 if the source_location doesn't exist.
        """
        if not os.path.exists(source_location):
            raise exceptions.PulpCodedException(error_code=error_codes.PLP0036,
                                                source_location=source_location)
        self._source_location = source_location

    def get_repositories(self):
        """
        Get an iterable of Repository models for all the repositories that contain this unit

        :return: Repositories that contain this content unit
        :rtype: iterable of Repository
        """
        content_list = RepositoryContentUnit.objects(unit_id=self.id)
        id_list = [item.repo_id for item in content_list]
        return Repository.objects(repo_id__in=id_list)

    @property
    def unit_key(self):
        """
        Dictionary representation of the unit key
        """
        return dict((key, getattr(self, key)) for key in self.unit_key_fields)

    @property
    def unit_key_str(self):
        """
        The unit key represented as a string ordered by unit key fields alphabetically
        """
        return str(sorted([getattr(self, key) for key in self.unit_key_fields]))

    @property
    def unit_key_as_named_tuple(self):
        """
        The unit key represented as a named_tuple by field name
        """
        return self.NAMED_TUPLE(**self.unit_key)

    def __hash__(self):
        """
        This should provide a consistent and unique hash where units of the same
        type and the same unit key will get the same hash value.
        """
        return hash(self.unit_type_id + self.unit_key_str)
