# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import os
from xml.etree import ElementTree


def compare_dict(source, target):
    """
    Utility method to compare dictionaries since python 2.6 doesn't support assertDictEquals

    :param source: The source dictionary to compare against the target
    :type source: dict
    :param target: The target dictionary to compare against the source
    :type target: dict
    :raise AssertionError: if the dictionaries do not match
    """
    if not isinstance(source, dict):
        raise AssertionError("Source is not a dictionary")
    if not isinstance(target, dict):
        raise AssertionError("Target is not a dictionary")

    #test keys
    source_keys = set(source.keys())
    target_keys = set(target.keys())

    if source_keys != target_keys:
        keys_info = {'source': ', '.join(map(str, source_keys)),
                     'target': ', '.join(map(str, target_keys))}
        raise AssertionError("Dictionaries do not match.  Keys are different: "
                             "[%(source)s] vs [%(target)s]" % keys_info)

    for key in source_keys:
        if source[key] != target[key]:
            raise AssertionError("Dictionaries do not match.  Value mismatch for key %(key)s.  "
                                 "%(value1)s is not equal to %(value2)s" %
                                 {'key': key, 'value1': source[key], 'value2': target[key]})


def compare_element(source, target):
    """
    Utility method to recursively compare two etree elements

    :param source: The source element to compare against the target
    :type source: xml.etree.ElementTree.Element
    :param target: The target element to compare against the source
    :type target: xml.etree.ElementTree.Element
    :raise AssertionError: if the elements do not match
    """
    if not ElementTree.iselement(source):
        raise AssertionError("Source is not an element")
    if not ElementTree.iselement(target):
        raise AssertionError("Target is not an element")

    if source.tag != target.tag:
        raise AssertionError("elements do not match.  Tags are different %s != %s" %
                             (source.tag, target.tag))

    #test keys
    source_keys = set(source.keys())
    target_keys = set(target.keys())

    if source_keys != target_keys:
        raise AssertionError("elements do not match.  Keys are different")

    for key in source_keys:
        if source.get(key) != target.get(key):
            raise AssertionError("Key values do not match.  Value mismatch for key %s: %s != %s" %
                                 (key, source.get(key), target.get(key)))

    if source.text != target.text:
        raise AssertionError("elements do not match.  Text is different\n%s\n%s" % (source.text,
                                                                                    target.text))

    #Use the deprecated getchildren method for python 2.6 support
    source_children = list(source.getchildren())
    target_children = list(target.getchildren())
    if len(source_children) != len(target_children):
        raise AssertionError("elements do not match.  Unequal number of child elements")

    for source_child, target_child in zip(source_children, target_children):
        compare_element(source_child, target_child)


def assert_body_matches_async_task(body, task):
    assert body['spawned_tasks'][0]['task_id'] == task.id


def touch(path):
    """
    Create a file at the specified path.  If the path does not exist already,
    create the parent directories for the file specified

    :param path: The canonical file path to create
    :type path: str
    """
    parent = os.path.dirname(path)

    if not os.path.exists(parent):
        os.makedirs(parent)

    file_handle = open(path, 'w')
    file_handle.close()
