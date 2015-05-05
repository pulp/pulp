"""
Module for content serialization.
"""

from pulp.common import dateutils
from pulp.server.webservices import http
from pulp.server.webservices.views.serializers import db


CONTENT_URI_PATH = http.API_V2_HREF + '/content'


def content_unit_obj(content_unit):
    """
    Serialize a content unit.
    """
    serial = db.scrub_mongo_fields(content_unit)
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
