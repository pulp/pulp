import logging

from mongoengine import Document, StringField

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
