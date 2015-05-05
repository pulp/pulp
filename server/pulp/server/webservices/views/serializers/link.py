"""
Generation of link objects for REST object serialization.

link object:
{
    "_href": <uri path to resource or collection>
}
"""

import os

from pulp.server.webservices import http


def link_dict():

    return {'_href': None}


def link_obj(href):
    """
    Create a link object for an arbitrary path.

    :param href: uri path
    :type href: str

    :return: link object
    :rtype: dict
    """

    link = link_dict()
    link['_href'] = href
    return link


def current_link_obj():
    """
    Create a link object for the path for the current request.

    :return: link object
    :rtype: dict
    """

    link = link_dict()
    link['_href'] = http.uri_path()
    return link


def child_link_obj(*path_elements):
    """
    Create a link object that appends the given elements to the path of the
    current request.
    Example: current request path = '/foo/bar/baz/'
             path_elements = ('fee', 'fie')
             returned_path = '/foo/bar/baz/fee/fie/'

    :param path_elements: captured positional arguments treated as path elements to append
    :type path_elements: Variable length tuple of strings
    :return: link object
    :rtype: dict
    """

    suffix = os.path.join(*path_elements)
    link = link_dict()
    link['_href'] = http.extend_uri_path(suffix)
    return link
