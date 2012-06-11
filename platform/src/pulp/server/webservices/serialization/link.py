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

link object:
{
    "_href": <uri path to resource or collection>
}
"""

import copy

from pulp.server.webservices import http


_LINK_OBJ_SKEL = {
    '_href': None,
}


def link_obj(href):
    """
    Create a link object for an arbitrary path.
    @param href: uri path
    @type  href: str
    @return: link object
    @rtype:  dict
    """
    link = copy.copy(_LINK_OBJ_SKEL)
    link['_href'] = href
    return link


def current_link_obj():
    """
    Create a link object for the path for the current request.
    @return: link object
    @rtype:  dict
    """
    link = copy.copy(_LINK_OBJ_SKEL)
    link['_href'] = http.uri_path()
    return link


def child_link_obj(*path_elements):
    """
    Create a link object that appends the given elements to the path of the
    current request.
    Example: current request path = '/foo/bar/baz/'
             path elements = ['fee', 'fie']
             returned path = '/foo/bar/baz/fee/fie/'
    @param path_elements: path elements to append
    @type  path_elements: *str
    @return: link object
    @rtype:  dict
    """
    suffix = '/'.join(path_elements)
    link = copy.copy(_LINK_OBJ_SKEL)
    link['_href'] = http.extend_uri_path(suffix)
    return link


def sibling_link_obj(*path_replacements):
    """
    Create a link object that replaces the end elements in the current request
    path with the provided replacements.
    Example: current request path = '/fee/fie/foe/foo/'
             path replacements = ['bar', 'baz']
             returned path = '/fee/fie/bar/baz/'
    @return: link object
    @rtype:  dict
    """
    link = copy.copy(_LINK_OBJ_SKEL)
    link['_href'] = http.sub_uri_path(*path_replacements)
    return link
