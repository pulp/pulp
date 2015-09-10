import mongoengine

from pulp.plugins.loader import api as plugin_api
from pulp.plugins.types import database as types_db
from pulp.plugins.util import misc


def find_units(units, pagination_size=50):
    """
    Query for units matching the unit key fields of an iterable of ContentUnit objects.

    This requires that all the ContentUnit objects are of the same content type.

    :param units: Iterable of content units with the unit key fields specified.
    :type units: iterable of pulp.server.db.model.ContentUnit
    :param pagination_size: How large a page size to use when querying units.
    :type pagination_size: int (default 50)

    :returns: unit models that pulp already knows about.
    :rtype: Generator of pulp.server.db.model.ContentUnit
    """
    # get the class from the first unit
    model_class = None

    for units_group in misc.paginate(units, pagination_size):
        q_object = mongoengine.Q()
        # Build a query for the units in this group
        for unit in units_group:
            if model_class is None:
                model_class = unit.__class__

            # Build the query for all the units, the | operator here
            # creates the equivalent of a mongo $or of all the unit keys
            unit_q_obj = mongoengine.Q(**unit.unit_key)
            q_object = q_object | unit_q_obj

        # Get this group of units
        query = model_class.objects(q_object)

        for found_unit in query:
            yield found_unit


def get_unit_key_fields_for_type(type_id):
    """
    Based on a unit type ID, determine the fields that compose that type's unit key.

    This supports both the new mongoengine models and the old "types_def" collection, so the caller
    need not worry about whether a type has been converted to use mongoengine or not.

    :param type_id: unique ID for a unit type
    :type  type_id: str

    :return:    tuple containing the name of each field in the unit key
    :rtype:     tuple

    :raises ValueError: if the type ID is not found
    """
    model_class = plugin_api.get_unit_model_by_id(type_id)
    if model_class is not None:
        return model_class.unit_key_fields

    type_def = types_db.type_definition(type_id)
    if type_def is not None:
        # this is an "old style" model
        return tuple(type_def['unit_key'])

    raise ValueError
