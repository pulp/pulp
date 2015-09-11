from pulp.plugins.model import AssociatedUnit, Unit


def to_pulp_unit(plugin_unit):
    """
    Uses the values in the plugin's unit object to create the unit metadata
    dictionary persisted by the content manager.

    @param plugin_unit: populated with values for the unit
    @type  plugin_unit: pulp.plugins.model.Unit

    @return: dictionary persisted by Pulp's content manager
    @rtype:  dict
    """

    pulp_unit = dict(plugin_unit.metadata)
    pulp_unit.update(plugin_unit.unit_key)
    pulp_unit['_storage_path'] = plugin_unit.storage_path

    return pulp_unit


def to_plugin_unit(pulp_unit, unit_type_id, unit_key_fields):
    """
    Parses the raw dictionary of a content unit into its plugin representation.

    :param pulp_unit: raw dictionary of unit metadata
    :type  pulp_unit: dict
    :param unit_type_id: unique identifier for the type of unit
    :type  unit_type_id: str
    :param unit_key_fields: collection of keys required for the type's unit key
    :type  unit_key_fields: list or tuple

    :return: plugin unit representation of the given unit
    :rtype:  pulp.plugins.model.Unit
    """

    # Copy so we don't mangle the original unit
    pulp_unit = dict(pulp_unit)

    unit_key = {}

    for k in unit_key_fields:
        unit_key[k] = pulp_unit.pop(k)

    storage_path = pulp_unit.pop('_storage_path', None)
    unit_id = pulp_unit.pop('_id', None)

    u = Unit(unit_type_id, unit_key, pulp_unit, storage_path)
    u.id = unit_id

    return u


def to_plugin_associated_unit(pulp_unit, unit_type_id, unit_key_fields):
    """
    Parses the raw dictionary of content unit associated to a repository into
    the plugin's object representation.

    :param pulp_unit: raw dictionary of unit metadata
    :type  pulp_unit: dict
    :param unit_type_id: unique identifier for the type of unit
    :type  unit_type_id: str
    :param unit_key_fields: collection of keys required for the type's unit key
    :type  unit_key_fields: list or tuple

    :return: plugin unit representation of the given unit
    :rtype:  pulp.plugins.model.AssociatedUnit
    """

    # Copy so we don't mangle the original unit
    # pymongo on RHEL6 doesn't seem to like deepcopy, so do this instead
    pulp_unit = dict(pulp_unit)
    pulp_unit['metadata'] = dict(pulp_unit['metadata'])

    unit_key = {}

    for k in unit_key_fields:
        unit_key[k] = pulp_unit['metadata'].pop(k)

    storage_path = pulp_unit['metadata'].pop('_storage_path', None)
    unit_id = pulp_unit.pop('unit_id', None)
    created = pulp_unit.pop('created', None)
    updated = pulp_unit.pop('updated', None)

    u = AssociatedUnit(unit_type_id, unit_key, pulp_unit['metadata'], storage_path,
                       created, updated)
    u.id = unit_id

    return u
