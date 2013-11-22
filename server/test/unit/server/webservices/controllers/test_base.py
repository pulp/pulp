# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import copy
import unittest

from pulp.server.webservices.controllers.base import JSONController


class JSONControllerTests(unittest.TestCase):

    def _compare_dictionary(self, source, target):
        if not isinstance(source, dict):
            self.fail("source is not a dictionary")
        if not isinstance(target, dict):
            self.fail("target is not a dictionary")

        #test keys
        source_keys = source.keys()
        target_keys = target.keys()
        for key in source_keys:
            if not key in target_keys:
                self.fail("dictionaries do not match")

        for key in source_keys:
            self.assertEquals(source[key], target[key])

    def test_process_whitelist_against_dictionary_global_keys(self):
        test_dictionary = {
            u'_href': u'foo',
            u'_id': u'bar',
            u'_ns': u'baz'
        }

        test_dictionary_before = copy.deepcopy(test_dictionary)
        JSONController.process_whitelist_against_dictionary(test_dictionary, [])

        self._compare_dictionary(test_dictionary_before,test_dictionary)

    def test_process_whitelist_against_dictionary_global_and_local_keys(self):
        test_dictionary = {
            u'_href': u'foo',
            u'_id': u'bar',
            u'_ns': u'baz',
            u'qux': u'quux'
        }

        test_dictionary_before = copy.deepcopy(test_dictionary)
        JSONController.process_whitelist_against_dictionary(test_dictionary, [u'qux'])
        self._compare_dictionary(test_dictionary_before, test_dictionary)

    def test_process_whitelist_against_dictionary_filter_key(self):
        test_dictionary = {
            u'_href': u'foo',
            u'_id': u'bar',
            u'_ns': u'baz',
            u'qux': u'quux'
        }

        target_result = copy.deepcopy(test_dictionary)
        target_result.pop(u'qux', None)

        JSONController.process_whitelist_against_dictionary(test_dictionary, [])
        self._compare_dictionary(target_result, test_dictionary)