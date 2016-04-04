import copy
import logging
import os
import random
import shutil
import uuid
from collections import namedtuple
from gettext import gettext as _
from hashlib import sha256
from hmac import HMAC

from mongoengine import (BooleanField, DictField, Document, DynamicField, IntField,
                         ListField, StringField, UUIDField, ValidationError, QuerySetNoCache)
from mongoengine import signals

from pulp.common import constants, dateutils, error_codes
from pulp.common.plugins import importer_constants
from pulp.plugins.model import Repository as plugin_repo
from pulp.plugins.util import misc
from pulp.server import exceptions
from pulp.server.constants import LOCAL_STORAGE, SUPER_USER_ROLE
from pulp.server.content.storage import FileStorage, SharedStorage
from pulp.server.async.emit import send as send_taskstatus_message
from pulp.server.db.connection import UnsafeRetry
from pulp.server.compat import digestmod
from pulp.server.db.fields import ISO8601StringField, UTCDateTimeField
from pulp.server.db.model.reaper_base import ReaperMixin
from pulp.server.db.model import base
from pulp.server.db.querysets import CriteriaQuerySet, RepoQuerySet, RepositoryContentUnitQuerySet
from pulp.server.managers import factory
from pulp.server.util import Singleton
from pulp.server.webservices.views import serializers


_logger = logging.getLogger(__name__)


SYSTEM_ID = '00000000-0000-0000-0000-000000000000'
SYSTEM_LOGIN = u'SYSTEM'
PASSWORD_ITERATIONS = 5000


class AutoRetryDocument(Document):
    """
    Base class for mongoengine documents, includes auto retry functionality,
    if unsafe_autoretry is set to true in the server config.

    All classes inheriting from this class must define a _ns field.
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize a document and decorate the appropriate methods with the retry_decorator.
        """
        super(AutoRetryDocument, self).__init__(*args, **kwargs)
        UnsafeRetry.decorate_instance(instance=self, full_name=type(self))

    # QuerySetNoCache is used as the default QuerySet to ensure that all sub-classes
    # do not cache query results unless specifically requested by calling ``cache``.
    meta = {
        'abstract': True,
        'queryset_class': QuerySetNoCache,
    }

    def clean(self):
        """
        Provides custom validation that all Pulp mongoengine document must adhere to.

        Ensure a field named `_ns` is defined and raise a ValidationError if not. For backwards
        compatibility, each Pulp Document must have the collection name stored in the `_ns` field
        as a StringField. This is required in the Document definition and with a default so it
        never has to be explicitly set. For example:

           _ns = StringField(default='reserved_resources')

        """
        if not hasattr(self.__class__, '_ns'):
            raise ValidationError("Pulp Documents must define the '_ns' attribute")
        if not isinstance(self.__class__._ns, StringField):
            raise ValidationError("Pulp Documents must have '_ns' be a StringField")
        if self.__class__._ns.default is None:
            raise ValidationError("Pulp Documents must define a default value for the '_ns' field")


class Repository(AutoRetryDocument):
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
    :type last_unit_added: UTCDateTimeField
    :ivar last_unit_removed: Datetime of the most recent occurence of removing a unit from the repo
    :type last_unit_removed: UTCDateTimeField
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
    last_unit_added = UTCDateTimeField()
    last_unit_removed = UTCDateTimeField()

    # For backward compatibility
    _ns = StringField(default='repos')

    meta = {'collection': 'repos',
            'allow_inheritance': False,
            'indexes': [{'fields': ['-repo_id'], 'unique': True}],
            'queryset_class': RepoQuerySet}
    SERIALIZER = serializers.Repository

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
                        last_unit_removed=self.last_unit_removed, repo_obj=self)
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


class RepositoryContentUnit(AutoRetryDocument):
    """
    Represents the link between a repository and the units associated with it.

    Defines the schema for the documents in repo_content_units collection.

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
            ],
            'queryset_class': RepositoryContentUnitQuerySet
            }


class Importer(AutoRetryDocument):
    """
    Defines schema for an Importer in the `repo_importers` collection.
    """
    repo_id = StringField(required=True)
    importer_type_id = StringField(required=True)
    config = DictField()
    scratchpad = DictField(default=None)
    last_sync = ISO8601StringField()

    # For backward compatibility
    _ns = StringField(default='repo_importers')
    SERIALIZER = serializers.ImporterSerializer

    meta = {'collection': 'repo_importers',
            'allow_inheritance': False,
            'indexes': [{'fields': ['-repo_id', '-importer_type_id'], 'unique': True}],
            'queryset_class': CriteriaQuerySet}

    @classmethod
    def pre_delete(cls, sender, document, **kwargs):
        """
        Purge the lazy catalog of all entries for the importer being deleted.

        :param sender:   class of sender (unused)
        :type  sender:   object
        :param document: mongoengine document being deleted.
        :type  document: pulp.server.db.model.Importer
        """
        query_set = LazyCatalogEntry.objects(importer_id=str(document.id))
        _logger.debug(_('Deleting lazy catalog entries for the {repo} repository.').format(
            repo=document.repo_id))
        query_set.delete()

    def delete(self):
        """
        Delete the Importer. Remove any documents it has stored.
        """
        if os.path.exists(self._local_storage_path):
            shutil.rmtree(self._local_storage_path)
        super(Importer, self).delete()

    def save(self):
        """
        Save the Importer. Additionally, write any pki documents from its config into disk storage
        for use by requests.
        """
        super(Importer, self).save()
        # A map of Importer config key names to file paths for the TLS PEM settings.
        pem_keys_paths = (
            (importer_constants.KEY_SSL_CA_CERT, self.tls_ca_cert_path),
            (importer_constants.KEY_SSL_CLIENT_CERT, self.tls_client_cert_path),
            (importer_constants.KEY_SSL_CLIENT_KEY, self.tls_client_key_path))
        for key, path in pem_keys_paths:
            self._write_pem_file(key, path)

    @property
    def tls_ca_cert_path(self):
        """
        Return the path where the TLS CA certificate should be stored for this Importer.

        :rtype: basestring
        """
        return os.path.join(self._pki_path, 'ca.crt')

    @property
    def tls_client_cert_path(self):
        """
        Return the path where the TLS client certificate should be stored for this Importer.

        :rtype: basestring
        """
        return os.path.join(self._pki_path, 'client.crt')

    @property
    def tls_client_key_path(self):
        """
        Return the path where the TLS client key should be stored for this Importer.

        :rtype: basestring
        """
        return os.path.join(self._pki_path, 'client.key')

    @property
    def _local_storage_path(self):
        """
        Return the path that the Importer should use for local storage.

        :rtype: basestring
        """
        return os.path.join(
            LOCAL_STORAGE, 'importers',
            '{repo}-{importer_type}'.format(repo=self.repo_id, importer_type=self.importer_type_id))

    @property
    def _pki_path(self):
        """
        Return the path that all pki files should be stored within for this Importer.

        :rtype: basestring
        """
        return os.path.join(self._local_storage_path, 'pki')

    def _write_pem_file(self, config_key, path):
        """
        Write the PEM data from self.config[config_key] to the given path, if the key is defined and
        is "truthy".

        :param config_key: The key corresponding to a value in self.config to write to path.
        :type  config_key: basestring
        :param path:       The path to write the PEM data to.
        :type  path:       basestring
        """
        if config_key in self.config and self.config[config_key]:
            if not os.path.exists(self._pki_path):
                misc.mkdir(os.path.dirname(self._pki_path))
                os.mkdir(self._pki_path, 0700)
            with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT, 0600), 'w') as pem_file:
                pem_file.write(self.config[config_key])


signals.pre_delete.connect(Importer.pre_delete, sender=Importer)


class ReservedResource(AutoRetryDocument):
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


class Worker(AutoRetryDocument):
    """
    Represents a worker.

    Defines the schema for the documents in the worker collection.

    :ivar name:    worker name, in the form of "worker_type@hostname"
    :type name:    mongoengine.StringField
    :ivar last_heartbeat:  A timestamp of the last heartbeat from the Worker
    :type last_heartbeat:  UTCDateTimeField
    """
    name = StringField(primary_key=True)
    last_heartbeat = UTCDateTimeField()

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


class MigrationTracker(AutoRetryDocument):
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
    version = IntField(default=-1)
    # For backward compatibility
    _ns = StringField(default='migration_trackers')

    meta = {'collection': 'migration_trackers',
            'indexes': [],  # small collection, does not need an index
            'allow_inheritance': False}


class TaskStatus(AutoRetryDocument, ReaperMixin):
    """
    Represents a task.

    Defines the schema for the documents in task_status collection. The documents in this
    collection may be reaped, so it inherits from ReaperMixin.

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
    :ivar group_id:    The id used to identify which  group of tasks a task belongs to
    :type group_id:    uuid.UUID
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
    group_id = UUIDField(default=None)

    # These are deprecated, and will always be None
    exception = StringField()
    traceback = StringField()

    # For backward compatibility
    _ns = StringField(default='task_status')

    meta = {'collection': 'task_status',
            'indexes': ['-tags', '-state', {'fields': ['-task_id'], 'unique': True}, '-group_id'],
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


class _ContentUnitNamedTupleDescriptor(object):
    """A descriptor used to dynamically generate and cache the namedtuple type for a ContentUnit

    The generated namedtuple is cached, keyed to the class for which it was generated, so
    this property will return the same namedtuple for each class that inherits an instance
    of this descriptor. Furthermore, the namedtuple cache behaves as a singleton, so all instances
    of this descriptor use the same shared cache.

    In the class scope, descriptor __set__ methods are not used by the type metaclass,
    so instances of this class should only be bound to names that LOOK_LIKE_CONSTANTS,
    effectively making this a lazily-evaluated read-only class property.

    """
    _cache = {}

    def __get__(self, obj, cls):
        if cls not in self._cache:
            self._cache[cls] = namedtuple(cls._content_type_id.default, cls.unit_key_fields)
        return self._cache[cls]


class ContentUnit(AutoRetryDocument):
    """
    The base class for all content units.

    All classes inheriting from this class must define a _content_type_id and unit_key_fields.

    _content_type_id must be of type mongoengine.StringField and have a default value of the string
    name of the content type.

    unit_key_fields must be a tuple of strings, each of which is a valid field name of the subcalss.

    :ivar id: content unit id
    :type id: mongoengine.StringField
    :ivar pulp_user_metadata: Bag of User supplied data to go along with this unit
    :type pulp_user_metadata: mongoengine.DictField
    :ivar _last_updated: last time this unit was updated (since epoch, zulu time)
    :type _last_updated: mongoengine.IntField
    :ivar _storage_path: The absolute path to associated content files.
    :type _storage_path: mongoengine.StringField
    """

    id = StringField(primary_key=True, default=lambda: str(uuid.uuid4()))
    pulp_user_metadata = DictField()
    _last_updated = IntField(required=True)
    _storage_path = StringField()

    meta = {
        'abstract': True,
    }

    NAMED_TUPLE = _ContentUnitNamedTupleDescriptor()

    @classmethod
    def attach_signals(cls):
        """
        Attach the signals to this class.

        This is provided as a class method so it can be called on subclasses
        and all the correct signals will be applied.
        """
        signals.pre_save.connect(cls.pre_save_signal, sender=cls)

    @classmethod
    def validate_model_definition(cls):
        """
        Validate that all subclasses of ContentType define required fields correctly.

        Ensure a field named `_content_type_id` is defined and raise an AttributeError if not. Each
        subclass of ContentUnit must have the content type id stored in the `_content_type_id`
        field as a StringField. The field must be marked as required and have a default set. For
        example:

           _content_type_id = StringField(required=True, default='rpm')

        Ensure a field named `unit_key_fields` is defined and raise an AttributeError if not. Each
        subclass of ContentUnit must have the content type id stored in the `unit_key_fields`
        field as a tuple and must not be empty.

           unit_key_fields = ('author', 'name', 'version')

        :raises: AttributeError if a field or attribute is not defined
        :raises: ValueError if a field or attribute have incorrect values
        :raises: TypeError if a field or attribute has invalid type
        """
        # Validate the 'unit_key_fields' attribute

        if not hasattr(cls, 'unit_key_fields'):
            msg = _("The class %(class_name)s must define a 'unit_key_fields' attribute")\
                % {'class_name': cls.__name__}
            _logger.error(msg)
            raise AttributeError(msg)
        if not isinstance(cls.unit_key_fields, tuple):
            msg = _("The class %(class_name)s must define 'unit_key_fields' to be a tuple")\
                % {'class_name': cls.__name__}
            _logger.error(msg)
            raise TypeError(msg)
        if len(cls.unit_key_fields) == 0:
            msg = _("The field 'unit_key_fields' on class %(class_name)s must have length > 0")\
                % {'class_name': cls.__name__}
            _logger.error(msg)
            raise ValueError(msg)

        # Validate the '_content_type_id' field
        if not hasattr(cls, '_content_type_id'):
            msg = _("The class %(class_name)s must define a '_content_type_id' attribute")\
                % {'class_name': cls.__name__}
            _logger.error(msg)
            raise AttributeError(msg)

        if not isinstance(cls._content_type_id, StringField):
            msg = _("The class %(class_name)s must define '_content_type_id' to be a StringField")\
                % {'class_name': cls.__name__}
            _logger.error(msg)
            raise TypeError(msg)
        if cls._content_type_id.default is None:
            msg = _("The class %(class_name)s must define a default value "
                    "for the '_content_type_id' field") % {'class_name': cls.__name__}
            _logger.error(msg)
            raise ValueError(msg)
        if cls._content_type_id.required is False:
            msg = _("The class %(class_name)s must require the '_content_type_id' field")\
                % {'class_name': cls.__name__}
            _logger.error(msg)
            raise ValueError(msg)

    @classmethod
    def pre_save_signal(cls, sender, document, **kwargs):
        """
        The signal that is triggered before a unit is saved, this is used to
        support the legacy behavior of generating the unit id and setting
        the _last_updated timestamp

        :param sender: sender class
        :type sender: object
        :param document: Document that sent the signal
        :type document: ContentUnit
        """
        document._last_updated = dateutils.now_utc_timestamp()

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
    def storage_path(self):
        """
        The content storage path.

        :return: The absolute path to stored content.
        :rtype: str
        """
        return self._storage_path

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
        return self.unit_key_as_digest()

    @property
    def unit_key_as_named_tuple(self):
        """
        The unit key represented as a named_tuple by field name
        """
        return self.NAMED_TUPLE(**self.unit_key)

    def to_id_dict(self):
        """
        Returns identity info as a dict.

        Returns a dict with the identity information (type ID and unit key) for this unit. The
        primary intention of this method is as a means to convert these units into a JSON
        serializable format.

        :return: Identity information (type ID and unit key)
        :rtype: dict
        """

        return {'type_id': self._content_type_id, 'unit_key': self.unit_key}

    @property
    def type_id(self):
        """
        Backwards compatible interface for _content_type_id

        The pre-mongoengine units used type_id to track what is stored in _content_type_id. This
        provides internal backwards compatibility allowing code to not be updated until all models
        are converted to mongoengine and able to use the new name exclusively.

        This should be removed once the old, non-mongoengine code paths are removed.
        """
        return self._content_type_id

    def unit_key_as_digest(self, algorithm=None):
        """
        The digest (hash) of the unit key.

        :param algorithm: A hashing algorithm object. Uses SHA256 when not specified.
        :type algorithm: hashlib.algorithm
        :return: The hex digest of the unit key.
        :rtype: str
        """
        _hash = algorithm or sha256()
        for key, value in sorted(self.unit_key.items()):
            _hash.update(key)
            if not isinstance(value, basestring):
                _hash.update(str(value))
            else:
                _hash.update(value)
        return _hash.hexdigest()

    def list_files(self):
        """
        List absolute paths to files associated with this unit.

        This *must* be overridden by multi-file unit subclasses. Units without files can use the
        default implementation.

        :return: A list of absolute file paths.
        :rtype: list
        """
        if self._storage_path and not os.path.isdir(self._storage_path):
            return [self._storage_path]
        else:
            return []

    def __hash__(self):
        """
        This should provide a consistent and unique hash where units of the same
        type and the same unit key will get the same hash value.
        """
        return hash(self.type_id + self.unit_key_as_digest())


class FileContentUnit(ContentUnit):
    """
    A content unit representing content that is of type *file*.

    :ivar downloaded: Indicates whether all of the files associated with the
        unit have been downloaded.
    :type downloaded: bool
    """

    downloaded = BooleanField(default=True)

    meta = {
        'abstract': True,
        'indexes': [
            'downloaded'
        ]
    }

    @classmethod
    def pre_save_signal(cls, sender, document, **kwargs):
        """
        The signal that is triggered before a unit is saved.
        Ensures the _storage_path is populated.

        :param sender: sender class
        :type sender: object
        :param document: Document that sent the signal
        :type document: FileContentUnit
        """
        super(FileContentUnit, cls).pre_save_signal(sender, document, **kwargs)
        if not document._storage_path:
            document.set_storage_path()

    def set_storage_path(self, filename=None):
        """
        Set the storage path.
        This is a total hack to support existing single-file units with a
        _storage_path that includes the file name.

        :param filename: An optional filename to appended to the path.
        :rtype filename: str
        """
        path = FileStorage.get_path(self)
        if filename:
            if not os.path.isabs(filename):
                path = os.path.join(path, filename)
            else:
                raise ValueError(_('must be relative path'))
        self._storage_path = path

    def import_content(self, path, location=None):
        """
        Import a content file into platform storage.
        The (optional) *location* may be used to specify a path within the unit
        storage where the content is to be stored.
        For example:
          import_content('/tmp/file') will store 'file' at: _storage_path
          import_content('/tmp/file', 'a/b/c) will store 'file' at: _storage_path/a/b/c

        :param path: The absolute path to the file to be imported.
        :type path: str
        :param location: The (optional) location within the unit storage path
            where the content is to be stored.
        :type location: str

        :raises ImportError: if the unit has not been saved.
        :raises PulpCodedException: PLP0037 if *path* is not an existing file.
        """
        if not self._last_updated:
            raise ImportError("Content unit must be saved before associated content"
                              " files can be imported.")
        if not os.path.isfile(path):
            raise exceptions.PulpCodedException(error_code=error_codes.PLP0037, path=path)
        with FileStorage() as storage:
            storage.put(self, path, location)

    def save_and_import_content(self, path, location=None):
        """
        Saves this unit to the database, then calls safe_import_content.

        :param path: The absolute path to the file to be imported
        :type path: str
        :param location: The (optional) location within the unit storage path
            where the content is to be stored.
        :type location: str
        """
        self.save()
        self.safe_import_content(path, location)

    def safe_import_content(self, path, location=None):
        """
        If import_content raises exception, cleanup and raise the exception

        :param path: The absolute path to the file to be imported
        :type path: str
        :param location: The (optional) location within the unit storage path
            where the content is to be stored.
        :type location: str
        """
        try:
            self.import_content(path, location)
        except:
            self.clean_orphans()
            raise

    def clean_orphans(self):
        """
        Exposes the ability to clean up this unit as an orphan.
        """
        orphan_manger = factory.content_orphan_manager()
        orphan_manger.delete_orphan_content_units_by_type(self._content_type_id, self.id)


class SharedContentUnit(ContentUnit):
    """
    A content unit representing content that is stored in a
    shared storage facility.
    """

    meta = {
        'abstract': True,
    }

    @property
    def storage_provider(self):
        """
        The storage provider.
        This defines the storage mechanism and qualifies the storage_id.

        :return: The storage provider.
        :rtype: str
        """
        raise NotImplementedError()

    @property
    def storage_id(self):
        """
        The identifier for the shared storage location.

        :return: An identifier for shared storage.
        :rtype: str
        """
        raise NotImplementedError()

    @classmethod
    def pre_save_signal(cls, sender, document, **kwargs):
        """
        The signal that is triggered before a unit is saved.
        Set the _storage_path on the document and add the symbolic link.

        :param sender: sender class
        :type sender: object
        :param document: Document that sent the signal
        :type document: SharedContentUnit
        """
        super(SharedContentUnit, cls).pre_save_signal(sender, document, **kwargs)
        with SharedStorage(document.storage_provider, document.storage_id) as storage:
            document._storage_path = storage.link(document)


class CeleryBeatLock(AutoRetryDocument):
    """
    Single document collection which gives information about the current celerybeat lock.

    :ivar celerybeat_name: string representing the celerybeat instance name
    :type celerybeat_name: basestring
    :ivar timestamp: The timestamp(UTC) at which lock is acquired
    :type timestamp: datetime.datetime
    :ivar lock: A unique key set to "locked" when lock is acquired.
    :type lock: basestring
    :ivar _ns: (Deprecated), Contains the name of the collection this model represents
    :type _ns: mongoengine.StringField
    """
    celerybeat_name = StringField(required=True)
    timestamp = UTCDateTimeField(required=True)
    lock = StringField(required=True, default="locked", unique=True)

    # For backward compatibility
    _ns = StringField(default='celery_beat_lock')


class LazyCatalogEntry(AutoRetryDocument):
    """
    A catalog of content that can be downloaded by the specified plugin.

    :ivar path: The content unit storage path.
    :type path: str
    :ivar importer_id: The ID of the plugin that contributed the catalog entry.
        This plugin participates in the downloading of content when requested by the streamer.
    :type importer_id: str
    :ivar unit_id: The associated content unit ID.
    :type unit_id: str
    :ivar unit_type_id: The associated content unit type.
    :type unit_type_id: str
    :ivar url: The *real* download URL.
    :type url: str
    :ivar checksum: The checksum of the file associated with the
        content unit. Used for validation.
    :type checksum: str
    :ivar checksum_algorithm: The algorithm used to generate the checksum.
    :type checksum_algorithm: str
    :ivar revision: The revision is used to group collections of entries.
    :type revision: int
    :ivar data: Arbitrary information stored with the entry.
        Managed by the plugin.
    :type data: dict
    """

    ALG_REGEX = r'(md5|sha1|sha224|sha256|sha384|sha512)'

    meta = {
        'collection': 'lazy_content_catalog',
        'allow_inheritance': False,
        'indexes': [
            'importer_id',
            {
                'fields': [
                    '-path',
                    '-importer_id',
                    '-revision',
                ],
                'unique': True
            },
        ],
    }

    # For backward compatibility
    _ns = StringField(default=meta['collection'])

    path = StringField(required=True)
    importer_id = StringField(required=True)
    unit_id = StringField(required=True)
    unit_type_id = StringField(required=True)
    url = StringField(required=True)
    checksum = StringField()
    checksum_algorithm = StringField(regex=ALG_REGEX)
    revision = IntField(default=0)
    data = DictField()

    def save_revision(self):
        """
        Add the entry using the next revision number.
        Previous revisions are deleted.
        """
        revisions = set([0])
        query = dict(
            importer_id=self.importer_id,
            path=self.path
        )
        # Find revisions
        qs = LazyCatalogEntry.objects.filter(**query)
        for revision in qs.distinct('revision'):
            revisions.add(revision)
        # Add new revision
        last_revision = max(revisions)
        self.revision = last_revision + 1
        self.save()
        # Delete previous revisions
        qs = LazyCatalogEntry.objects.filter(revision__in=revisions, **query)
        qs.delete()


class DeferredDownload(AutoRetryDocument):
    """
    A collection of units that have been handled by the streamer in the
    passive lazy workflow that Pulp should download.

    :ivar unit_id:      The associated content unit ID.
    :type unit_id:      str
    :ivar unit_type_id: The associated content unit type.
    :type unit_type_id: str
    """
    meta = {
        'collection': 'deferred_download',
        'indexes': [
            {
                'fields': ['unit_id', 'unit_type_id'],
                'unique': True
            }
        ]
    }

    unit_id = StringField(required=True)
    unit_type_id = StringField(required=True)

    # For backward compatibility
    _ns = StringField(default='deferred_download')


class User(AutoRetryDocument):
    """
    :ivar login: user's login name, must be unique for each user
    :type login: basestring
    :ivar name: user's full name
    :type name: basestring
    :ivar password: encrypted password for login credentials
    :type password: basestring
    :ivar roles: list of roles user belongs to
    :type roles: list of str
    :ivar _ns: (Deprecated), Contains the name of the collection this model represents
    :type _ns: mongoengine.StringField
    """

    login = StringField(required=True, regex=r'^[.\-_A-Za-z0-9]+$')
    name = StringField()
    password = StringField()
    roles = ListField(StringField())

    # For backward compatibility
    _ns = StringField(default='users')

    meta = {'collection': 'users',
            'allow_inheritance': False,
            'indexes': ['-roles', {'fields': ['-login', '-name'], 'unique': True}],
            'queryset_class': CriteriaQuerySet}

    SERIALIZER = serializers.User

    def is_superuser(self):
        """
        Return True if the user with given login is a super user

        :return: True if the user is a super user, False otherwise
        :rtype:  bool
        """
        return SUPER_USER_ROLE in self.roles

    def set_password(self, plain_password):
        """
        Sets the user's password to a hashed version of the plain_password. This does not save the
        object.

        :param plain_password: plain password, not hashed.
        :type  plain_password: str

        :raises pulp_exceptions.InvalidValue: if password is not a string
        """
        if plain_password is not None and not isinstance(plain_password, basestring):
            raise exceptions.InvalidValue('password')
        self.password = self._hash_password(plain_password)

    def check_password(self, plain_password):
        """
        Checks a plaintext password against the hashed password stored on the User object.

        :param plain_password: plaintext password to check against the stored hashed password
        :type  plain_password: str

        :return: True if password is correct, False otherwise
        :rtype:  bool
        """
        salt, hashed_password = self.password.split(",")
        salt = salt.decode("base64")
        hashed_password = hashed_password.decode("base64")
        pbkdbf = self._pbkdf_sha256(plain_password, salt, PASSWORD_ITERATIONS)
        return hashed_password == pbkdbf

    def _hash_password(self, plain_password):
        """
        Creates a hashed password from a plaintext password.

        _hash_password, check_password, _random_bytes, and _pbkdf_sha256 were taken from this
        stackoverflow.com : http://tinyurl.com/2f6gx7s

        :param plain_password: plaintext password to be hashed
        :type  plain_password: str

        :return: salt concatenated with the hashed password
        :rtype:  str
        """
        salt = self._random_bytes(8)  # 64 bits
        hashed_password = self._pbkdf_sha256(str(plain_password), salt, PASSWORD_ITERATIONS)
        return salt.encode("base64").strip() + "," + hashed_password.encode("base64").strip()

    def _random_bytes(self, num_bytes):
        """
        Generate a string of random characters of the specified length.

        :param num_bytes: number of bytes (characters) to generate
        :type  num_bytes: int

        :return: string of random characters with length <num_bytes>
        :rtype:  str
        """
        return "".join(chr(random.randrange(256)) for i in xrange(num_bytes))

    def _pbkdf_sha256(self, password, salt, iterations):
        """
        Apply the salt to the password some number of times to increase randomness.

        :param password: plaintext password
        :type  password: str
        :param salt: random set of characters to encode the password
        :type  salt: str
        :param iterations: number of times to apply the salt
        :type  iterations: int

        :return: hashed password
        :rtype:  str
        """
        result = password
        for i in xrange(iterations):
            result = HMAC(result, salt, digestmod).digest()  # use HMAC to apply the salt
        return result


class Distributor(AutoRetryDocument):
    """
    Defines schema for a Distributor in the 'repo_distributors' collection.
    """
    repo_id = StringField(required=True)
    distributor_id = StringField(required=True, regex=r'^[\-_A-Za-z0-9]+$')
    distributor_type_id = StringField(required=True)
    config = DictField()
    auto_publish = BooleanField(default=False)
    last_publish = UTCDateTimeField()
    scratchpad = DictField()

    _ns = StringField(default='repo_distributors')
    SERIALIZER = serializers.Distributor

    meta = {'collection': 'repo_distributors',
            'allow_inheritance': False,
            'indexes': [{'fields': ['-repo_id', '-distributor_id'], 'unique': True}],
            'queryset_class': CriteriaQuerySet}

    @property
    def resource_tag(self):
        """
        :return: a globally unique identifier for the repo and distributor that
                 can be used in cross-type comparisons.
        :rtype:  basestring
        """
        return 'pulp:distributor:{0}:{1}'.format(self.repo_id, self.distributor_id)


class SystemUser(base.Model):
    """
    Singleton user class that represents the "system" user (i.e. no user).

    The entire point of this singleton class is that you can generate any number of new ones, and
    if it is initialized with the same args, then SystemUser(same_args) is SystemUser(same_args)
    returns True.

    This class cannot inherrit from the Users mongoengine document because the metaclasss
    does not play well with the mongoengine metaclasses. Fortunately, the only functionality
    required is access to user instance variables.

    :ivar login: login of the system user
    :type login: str
    :ivar password: Password of the system user, is always None
    :type password: NoneType
    :ivar roles: roles associated with the system user, is always empty
    :type roles: list
    :ivar id: id of the system user
    :type id: str
    :ivar _id: id of the system user
    :type _id: str
    """

    __metaclass__ = Singleton

    def __init__(self):
        """
        Initialize a system user.
        """
        self.login = SYSTEM_LOGIN
        self.password = None
        self.name = SYSTEM_LOGIN
        self.roles = []
        self._id = self.id = SYSTEM_ID
