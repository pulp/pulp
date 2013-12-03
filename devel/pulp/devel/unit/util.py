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
        raise AssertionError("Dictionaries do not match.  Keys are different")

    for key in source_keys:
        if source[key] != target[key]:
            raise AssertionError("Dictionaries do not match.  Value mismatch for key %s" % key)