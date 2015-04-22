import logging

from mongoengine import Document, StringField, DictField, DateTimeField

from pulp.server.db.model.fields import ISO8601StringField


_logger = logging.getLogger(__name__)


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
    :ivar metadata: arbitrary data that describes the contents of the repo;
                    the values may change as the contents of the repo change,
                    either set by the user or by an importer or distributor
    :type metadata: mongoengine.DictField
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
