# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""
Module for content serialization.
"""

from pulp.server.webservices import http

import db

# constants --------------------------------------------------------------------

CONTENT_URI_PATH = http.API_V2_HREF + '/content'

# serialization api ------------------------------------------------------------


def content_type_obj(content_type):
    """
    Serialize a content type.
    """
    serial = db.scrub_mongo_fields(content_type)
    return serial


def content_unit_obj(content_unit):
    """
    Serialize a content unit.
    """
    serial = db.scrub_mongo_fields(content_unit)
    return serial

# utility functions ------------------------------------------------------------

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
