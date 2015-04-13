from mongoengine import Document, IntField, StringField


class MigrationTracker(Document):
    """
    This is used to track state about our migrations package. There will be one object for each
    migration package in pulp.server.db.migrations, and we will track which migration version each
    of those packages have been advanced to.

    :ivar name:    Uniquely identifies the package, and is the name of the package
    :type name:    str
    :ivar version: The version that the migration package is currently at
    :type version: int
    """

    name = StringField(unique=True, required=True)
    version = IntField(default=0)
    # For backward compatibility
    _ns = StringField(default='migration_trackers')

    meta = {'collection': 'migration_trackers',
            'indexes': [],  # small collection, does not need an index
            'allow_inheritance': False}
