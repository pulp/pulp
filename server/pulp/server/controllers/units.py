import mongoengine

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
