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

import copy
import unittest

from pulp.devel.unit import util
from pulp.server.webservices.controllers.base import JSONController


class JSONControllerTests(unittest.TestCase):

    def test_process_dictionary_against_whitelist_global_keys(self):
        test_dictionary = {
            u'_href': u'foo',
            u'_id': u'bar',
            u'_ns': u'baz'
        }

        test_dictionary_before = copy.deepcopy(test_dictionary)
        JSONController.process_dictionary_against_whitelist(test_dictionary, [])

        util.compare_dict(test_dictionary_before, test_dictionary)

    def test_process_dictionary_against_whitelisty_global_and_local_keys(self):
        test_dictionary = {
            u'_href': u'foo',
            u'_id': u'bar',
            u'_ns': u'baz',
            u'qux': u'quux'
        }

        test_dictionary_before = copy.deepcopy(test_dictionary)
        JSONController.process_dictionary_against_whitelist(test_dictionary, [u'qux'])
        util.compare_dict(test_dictionary_before, test_dictionary)

    def test_process_dictionary_against_whitelist_filter_key(self):
        test_dictionary = {
            u'_href': u'foo',
            u'_id': u'bar',
            u'_ns': u'baz',
            u'qux': u'quux'
        }

        target_result = copy.deepcopy(test_dictionary)
        target_result.pop(u'qux', None)

        JSONController.process_dictionary_against_whitelist(test_dictionary, [])
        util.compare_dict(target_result, test_dictionary)