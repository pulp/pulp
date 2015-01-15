"""
This migration adds a new pulp_user_metadata field to every Unit of all types. The new field is
initialized as an empty dictionary.
"""
from pulp.plugins.types import database
from pulp.server import constants
from pulp.server.managers import factory


def migrate(*args, **kwargs):
    """
    Perform the migration as described in this module's docblock.

    :param args:   unused
    :type  args:   list
    :param kwargs: unused
    :type  kwargs: dict
    """
    plugin_manager = factory.plugin_manager()
    types = plugin_manager.types()

    for content_type in types:
        collection = database.type_units_collection(content_type['id'])
        collection.update({constants.PULP_USER_METADATA_FIELDNAME: {'$exists': False}},
                          {'$set': {constants.PULP_USER_METADATA_FIELDNAME: {}}}, multi=True)
