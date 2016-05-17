
"""
Provides common classes used to migrate content unit storage to
the standard path format introduced in pulp 2.8. Each plugin needs
to add a migration using these classes.
For example:

from pulp.plugins.migration.standard_storage_path import Migration, Plan
from pulp.server.db import connection


def migrate(*args, **kwargs):
    key_fields = (.,..,.)
    collection = connection.get_collection('units_rpm')
    migration = Migration()
    plan = Plan(collection, key_fields)
    migration.add(plan)
    migration()
"""
import os
import shutil

from collections import namedtuple
from hashlib import sha256
from itertools import chain

from pulp.plugins.util.misc import mkdir
from pulp.server.config import config


# stored in the Batch
Item = namedtuple(
    'Item',
    [
        'plan',
        'unit_id',
        'storage_path',
        'new_path'
    ]
)


class Batch(object):
    """
    A batch of units to be migrated.

    :ivar items: A dictionary of Item keyed by storage path.
    :type items: dict
    """

    # The number of items in each batch.
    # Using 500k based on memory profile of 100 mb / 100k.
    LIMIT = 500000

    def __init__(self):
        self.items = {}

    def add(self, unit):
        """
        Add the specified unit to the batch.

        :param unit: A unit to add.
        :type unit: Unit
        """
        item = Item(unit.plan, unit.id, unit.storage_path, unit.new_path)
        self.items[unit.storage_path] = item

    def reset(self):
        """
        Reset the batch by clearing added units.
        """
        self.items = {}

    def _relink(self):
        """
        Update (relink) symlinks to reflect the storage path of migrated units.
        Foreach symlink found, find the *new* path using the plan.  Then,
        re-create the symlink with the updated target.
        """
        root = Migration.publish_dir()
        for path, directories, files in os.walk(root):
            for name in chain(files, directories):
                abs_path = os.path.join(path, name)
                try:
                    target = os.readlink(abs_path)
                except OSError:
                    continue
                unit = self.items.get(target)
                if not unit:
                    continue
                os.unlink(abs_path)
                os.symlink(unit.new_path, abs_path)

    def _migrate(self):
        """
        Migrate the units referenced in the batch.
          1. Move the content files.
          2. Update the unit in the DB.
        """
        for item in self.items.itervalues():
            Unit.migrate(item.plan, item.unit_id, item.storage_path, item.new_path)

    def __call__(self):
        """
        Execute the batch.
          1. Update published links to reference the new path.
          2. Move the content to the new path.
          2. Update _storage_path on the unit and saved.
        """
        if self.items:
            self._relink()
            self._migrate()
            self.reset()

    def __len__(self):
        return len(self.items)


class Plan(object):
    """
    The Unit migration plan contains all that is necessary
    to migrate a specific type of content unit.  This includes the collection,
    the list of unit keys (needed to calculate the new storage path) and an
    indication of whether the storage path references a file or directory.

    :ivar collection: A DB collection.
    :type collection: pymongo.collection.Collection
    :ivar key_fields: Tuple of fields that make up the unit key.
    :type key_fields: tuple
    :ivar join_leaf: Join the existing path leaf (filename) to the new path.
    :type join_leaf: bool
    :ivar fields: Additional *non-key* unit fields.
    :type fields: set
    """

    # Base unit fields
    BASE_FIELDS = (
        '_storage_path',
        '_content_type_id'
    )

    def __init__(self, collection, key_fields, join_leaf=True):
        """
        :param collection: A DB collection.
        :type collection: pymongo.collection.Collection
        :param key_fields: Tuple of fields that make up the unit key.
        :type key_fields: tuple
        :param join_leaf: Join the existing path leaf (filename) to the new path.
        :type join_leaf: bool
        """
        self.collection = collection
        self.key_fields = key_fields
        self.join_leaf = join_leaf
        self.fields = set()

    def _new_path(self, unit):
        """
        Determine the *new* storage path for the specified unit.

        :param unit: A unit being migrated.
        :type unit: Unit
        :return: The new storage path.
        :rtype: str
        """
        digest = unit.key_digest()
        path = os.path.join(
            os.path.join(Migration.content_dir(), 'units'),
            unit.type_id,
            digest[0:2],
            digest[2:])
        if self.join_leaf:
            path = os.path.join(path, os.path.basename(unit.storage_path))
        return path

    def __iter__(self):
        """
        Get an iterable of units planned to be migrated.

        :return: Unit planned to be migrated.
        :rtype: generator
        :
        """
        fields = dict(
            (k, True) for k in chain(Plan.BASE_FIELDS, self.fields, self.key_fields)
        )
        for document in self.collection.find(projection=fields):
            unit = Unit(self, document)
            unit.new_path = self._new_path(unit)
            if not unit.needs_migration():
                continue
            yield unit


class Migration(object):
    """
    Migration of unit `storage_path` to the standardized path
    introduced in Pulp 2.8.
      1. Execute each plan.
      2. Prune content tree of empty directories.
    """

    @staticmethod
    def storage_dir():
        """
        The root storage path.

        :return: The root storage path.
        :rtype: str
        """
        return config.get('server', 'storage_dir')

    @staticmethod
    def content_dir():
        """
        The root content storage path.

        :return: The root content storage path.
        :rtype: str
        """
        return os.path.join(Migration.storage_dir(), 'content')

    @staticmethod
    def publish_dir():
        """
        The root published path.

        :return: The root storage path.
        :rtype: str
        """
        return os.path.join(Migration.storage_dir(), 'published')

    @staticmethod
    def _prune():
        """
        Delete empty directories in the content storage tree.
        The migration will create empty directories.
        """
        root = Migration.content_dir()
        for path, directories, files in os.walk(root, topdown=False):
            if not os.listdir(path):
                os.rmdir(path)

    def __init__(self):
        self.plans = []

    def add(self, plan):
        """
        Add a migration plan.

        :param plan: A plan to add.
        :type plan: Plan
        """
        self.plans.append(plan)

    def __call__(self):
        """
        Do the migration as follows:
          1. Batch the migration.
          2. Delete empty directories created by the migration.
        """
        batch = Batch()
        for unit in chain(*self.plans):
            batch.add(unit)
            if len(batch) >= Batch.LIMIT:
                batch()
        batch()
        self._prune()


class Unit(object):
    """
    A generic content unit.

    :ivar plan: A plan object.
    :type plan: Plan
    :ivar document: A content unit document fetched from the DB.
    :type document: dict
    :ivar new_path: The *new* storage path.
    :type new_path: str
    """

    def __init__(self, plan, document):
        """
        :param plan: A plan object.
        :type plan: Plan
        :param document: A content unit document fetched from the DB.
        :type document: dict
        """
        self.plan = plan
        self.document = document
        self.new_path = None

    @property
    def id(self):
        """
        The document['_id'].
        """
        return self.document['_id']

    @property
    def type_id(self):
        """
        The document['_content_type_id'].
        """
        return self.document['_content_type_id']

    @property
    def storage_path(self):
        """
        The document['_storage_path'].
        """
        return self.document['_storage_path']

    @property
    def key(self):
        """
        The unit key property.
        """
        return dict([(k, self.document[k]) for k in self.plan.key_fields])

    def needs_migration(self):
        """
        Get whether the unit needs to be migrated.

        :return: True if needs to be migrated.
        :rtype: bool
        """
        return self.storage_path != self.new_path

    def key_digest(self):
        """
        Get the sha256 hex digest for the unit key.

        :return: The sha256 hex digest for the unit key.
        :rtype: str
        """
        _hash = sha256()
        for key, value in sorted(self.key.items()):
            _hash.update(key)
            if not isinstance(value, basestring):
                _hash.update(str(value))
            else:
                _hash.update(value)
        return _hash.hexdigest()

    @staticmethod
    def migrate(plan, unit_id, path, new_path):
        """
        Migrate the unit.
          1. move content
          2. update the DB

        :param plan: A plan object.
        :type plan: Plan
        :param unit_id: A unit UUID.
        :type unit_id: str
        :param path: The current storage path.
        :type path: str
        :param new_path: The new storage path.
        :type new_path: str
        """
        if os.path.exists(path):
            mkdir(os.path.dirname(new_path))
            shutil.move(path, new_path)
        plan.collection.update_one(
            filter={
                '_id': unit_id
            },
            update={
                '$set': {'_storage_path': new_path}
            })
