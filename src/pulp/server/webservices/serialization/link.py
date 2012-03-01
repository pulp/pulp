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
Generation of link objects for REST object serialization.
"""

import copy

from pulp.server.webservices import http


_LINK_OBJ_SKEL = {
    '_href': None,
}


def link_obj(href):
    link = copy.copy(_LINK_OBJ_SKEL)
    link['_href'] = href
    return link


def current_link_obj():
    link = copy.copy(_LINK_OBJ_SKEL)
    link['_href'] = http.uri_path()
    return link


def child_link_obj(*path_elements):
    suffix = '/'.join(path_elements)
    link = copy.copy(_LINK_OBJ_SKEL)
    link['_href'] = http.extend_uri_path(suffix)
    return link


def sibling_link_obj(*path_replacements):
    link = copy.copy(_LINK_OBJ_SKEL)
    link['_href'] = http.sub_uri_path(*path_replacements)
    return link
