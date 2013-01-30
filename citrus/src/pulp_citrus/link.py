# Copyright (c) 2012 Red Hat, Inc.
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
Provides file linking and embedding capabilities.
Used to pass file(s) through configuration values.  Basically just a standard
for passing file path and content using an encoded dictionary.  The dictionary
is keyed by a special key called the signature.  The signature is used to
identify collection values that are packed links.

A file path is packed as:

{ __file:link__ : {
    path : <path>,
    content : <file content>
}

packing   - read file and create dictionary.
unpacking - write file at destination and return the path.

The file content is base64 encoded.
"""

import os

from base64 import b64encode, b64decode


SIGNATURE = '__file:link__'


def pack(path, path_out=None):
    """
    Pack the file at the specified path as an encoded link.
    :param path: The path to a file.
    :type path: str
    :param path_out: The (optional) path used during link unpacking.
    :type path_in: str
    :return: The encoded link.
    :rtype: dict
    """
    fp = open(path, 'rb')
    try:
        content = b64encode(fp.read())
        link = {
            SIGNATURE : dict(path=(path_out or path), content=content)
        }
        return link
    finally:
        fp.close()

def unpack(link_dict, path_out=None):
    """
    Unpack an encoded link.
    The file is written to the path specified.
    :param link_dict: An encoded link.
    :type link_dict: dict
    :param path_out: The (optional) path where the file is to be unpacked.
    :type path_out: str
    :return: The path to the unpacked file.
    :rtype: str
    """
    d = link_dict[SIGNATURE]
    path = path_out or d['path']
    content = b64decode(d['content'])
    dir_path = os.path.dirname(path)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    fp = open(path, 'wb+')
    try:
        fp.write(content)
    finally:
        fp.close()
    return path

def unpack_all(value):
    """
    Unpack all encoded links in an object graph.
    Traverses data structures and unpacks encoded links.
    :param value: An object.
    :type value: object
    :return: The unpacked object.
    :rtype: object
    """
    if is_link(value):
        return unpack(value)
    if isinstance(value, dict):
        d = {}
        for k, v in value.items():
            d[k] = unpack_all(v)
        return d
    if isinstance(value, list):
        lst = []
        for item in value:
            lst.append(unpack_all(item))
        return lst
    return value

def is_link(link_dict):
    """
    Get whether the link_dict is an encoded link.
    :param link_dict: An object to test
    :type link_dict: object
    :return: True if an encoded link.
    :rtype: bool
    """
    return isinstance(link_dict, dict) and\
           len(link_dict) == 1 and SIGNATURE in link_dict