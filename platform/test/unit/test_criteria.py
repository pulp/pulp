# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License
# (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied, including the
# implied warranties of MERCHANTABILITY, NON-INFRINGEMENT, or FITNESS FOR A
# PARTICULAR PURPOSE.
# You should have received a copy of GPLv2 along with this software; if not,
# see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

import unittest
from pulp.server.db.model.criteria import Criteria

FIELDS = set(('sort', 'skip', 'limit', 'filters', 'fields'))

class TestAsDict(unittest.TestCase):
    def test_empty(self):
        c = Criteria()
        ret = c.as_dict()
        self.assertTrue(isinstance(ret, dict))
        for field in FIELDS:
            self.assertTrue(ret[field] is None)

    def test_full(self):
        c = Criteria(
            filters = {'name':{'$in':['a','b']}},
            sort = (('name','ascending'),),
            limit = 10,
            skip = 10,
            fields = ('name', 'id')
        )
        ret = c.as_dict()
        self.assertTrue(isinstance(ret['filters'], dict))
        self.assertEqual(ret['limit'], 10)
        self.assertEqual(ret['skip'], 10)
        self.assertEqual(ret['fields'], c.fields)
        self.assertEqual(set(ret.keys()), FIELDS)
