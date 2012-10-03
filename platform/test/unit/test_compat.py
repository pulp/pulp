# Copyright (c) 2012 Red Hat, Inc.
#
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import unittest

import mock

from pulp.common import compat


class TestAny(unittest.TestCase):
    def test_empty(self):
        ret = compat.any([])
        self.assertFalse(ret)

    def test_false(self):
        ret = compat.any([0, False, None])
        self.assertFalse(ret)

    def test_true(self):
        ret = compat.any([0, False, True])
        self.assertTrue(ret)

    def test_not_iterable(self):
        self.assertRaises(TypeError, compat.any, 3)


class TestCheckBuiltin(unittest.TestCase):
    def test_found(self):
        m = mock.MagicMock()
        m.__name__ = 'map'
        ret = compat.check_builtin(m)
        self.assertEqual(ret, map)

    def test_not_found(self):
        m = mock.MagicMock()
        m.__name__ = 'foo'
        ret = compat.check_builtin(m)
        self.assertEqual(ret, m)

