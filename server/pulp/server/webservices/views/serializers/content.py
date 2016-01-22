"""
Module for content serialization.
"""
import logging

from pulp.common import dateutils
from pulp.server.controllers import units
from pulp.server.webservices import http
from pulp.server.webservices.views.serializers import db

_logger = logging.getLogger(__name__)
CONTENT_URI_PATH = http.API_V2_HREF + '/content'


def remap_fields_with_serializer(content_unit):
    """Remap fields in place in a pymongo object using a mongoengine serializer

    :param content_unit: Content unit to modify
    :type content_unit: dict

    This is a small workaround to help in cases where REST views are returning the older objects
    coming out of pymongo, but still need to have their fields remapped according to the rules of
    the pymongo serializer. As a workaround, this is a "best effort" function, so serialization
    failures will be written to the debug log and not raise exeptions.

    Usage of pymongo objects is deprecated. Since this function is only concerned with serializing
    pymongo objects, its usage is also deprecated. Furthermore, this function is only intended to
    be used in the final serialization of objects before presentation in the REST API.

    """
    try:
        content_type_id = content_unit['_content_type_id']
    except KeyError:
        # content unit didn't have a content type id, usually means we're testing...
        _logger.debug('No _content_type_id found in content unit when remapping fields: '
                      '{0!r}'.format(content_unit))
        return

    serializer = units.get_model_serializer_for_type(content_type_id)
    if serializer is None:
        # No serializer, nothing to do
        return

    # build the list of fields that need to be remapped
    field_map = {}
    for field in content_unit:
        remapped_field = serializer.translate_field_reverse(field)
        if remapped_field != field:
            field_map[field] = remapped_field

    # do the remapping
    for original_field, remapped_field in field_map.items():
        content_unit[remapped_field] = content_unit.pop(original_field)


def content_unit_obj(content_unit):
    """
    Serialize a content unit.
    """
    serial = db.scrub_mongo_fields(content_unit)
    remap_fields_with_serializer(content_unit)
    last_updated = content_unit.get('_last_updated')
    if last_updated:
        content_unit['_last_updated'] = dateutils.format_iso8601_utc_timestamp(last_updated)
    return serial


def content_unit_child_link_objs(unit):
    """
    Generate child link objects for the associated child content units.
    NOTE: this removes the _<child type>_children fields from the content unit.
    """
    links = {}
    child_keys = []
    for key, child_list in unit.items():
        # look for children fields
        if not key.endswith('children'):
            continue
        child_keys.append(key)
        # child field key format: _<child type>_children
        child_type = key.rsplit('_', 1)[0][1:]
        child_type_links = []
        # generate links
        for child_id in child_list:
            href = '/'.join((CONTENT_URI_PATH, child_type, 'units', child_id))
            link = {'child_id': child_id,
                    '_href': http.ensure_ending_slash(href)}
            child_type_links.append(link)
        links[child_type] = child_type_links
    # side effect: remove the child keys
    for key in child_keys:
        unit.pop(key)
    return links
